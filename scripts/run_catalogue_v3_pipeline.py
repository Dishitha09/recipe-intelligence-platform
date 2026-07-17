import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from scripts.backfill_catalogue_v3_web_nutrition import backfill_web_nutrition
from scripts.enrich_catalogue_v3 import enrich_catalogue_v3
from services.acquisition.scrape_catalogue_v3_web import scrape_catalogue_v3_web
from services.database.ingestion_run_repository import IngestionRunRepository
from services.ingestion.source_registry import SourceConfig, SourceRegistry


DEFAULT_CONFIG = Path("configs/production_recipe_sources.json")
DEFAULT_OUTPUT_DIR = Path("data/datasets/catalogue_v3/automated_runs")


@dataclass(frozen=True)
class PipelineOptions:
    config_path: Path = DEFAULT_CONFIG
    output_dir: Path = DEFAULT_OUTPUT_DIR
    source_ids: tuple[str, ...] = ()
    source_group: str | None = None
    all_configured_sources: bool = False
    allow_disabled: bool = False
    max_items: int | None = None
    max_pages: int | None = None
    max_depth: int | None = None
    crawl_delay_seconds: float | None = None
    concurrent_requests: int | None = None
    enrich_limit: int | None = None
    nutrition_limit: int | None = None
    nutrition_timeout_seconds: int = 30
    source_timeout_seconds: int = 420
    update_existing: bool = False
    skip_scrape: bool = False
    skip_enrichment: bool = False
    skip_nutrition: bool = False
    no_ingest: bool = False
    dry_run: bool = False
    track_runs: bool = True


def select_sources(
    sources: Iterable[SourceConfig],
    source_ids: Iterable[str] = (),
    source_group: str | None = None,
    all_configured_sources: bool = False,
    allow_disabled: bool = False,
) -> list[SourceConfig]:
    requested_ids = set(source_ids)
    selected = []

    for source in sources:
        if source.adapter != "scrapy":
            continue

        if requested_ids:
            should_include = source.source_id in requested_ids
        elif source_group:
            should_include = source.config.get("source_group") == source_group
        else:
            should_include = all_configured_sources or source.enabled

        if not should_include:
            continue

        if not source.enabled and not allow_disabled and source.source_id not in requested_ids:
            continue

        selected.append(source)

    missing_ids = requested_ids - {source.source_id for source in selected}
    if missing_ids:
        raise ValueError(
            "Requested source IDs were not found or are not scrapy sources: "
            + ", ".join(sorted(missing_ids))
        )

    return sorted(
        selected,
        key=lambda source: (
            source.config.get("priority", 999),
            source.source_id,
        ),
    )


def run_catalogue_v3_pipeline(
    options: PipelineOptions,
    scrape_func: Callable[..., dict[str, Any]] = scrape_catalogue_v3_web,
    enrich_func: Callable[..., dict[str, Any]] = enrich_catalogue_v3,
    nutrition_func: Callable[..., dict[str, Any]] = backfill_web_nutrition,
    run_repository: IngestionRunRepository | None = None,
) -> dict[str, Any]:
    registry = SourceRegistry(config_path=str(options.config_path))
    sources = select_sources(
        registry.configs,
        source_ids=options.source_ids,
        source_group=options.source_group,
        all_configured_sources=options.all_configured_sources,
        allow_disabled=options.allow_disabled,
    )

    if not sources:
        raise ValueError(
            "No web scrapy sources selected. Enable approved sources in the "
            "registry, pass --source-id, or pass --source-group with "
            "--allow-disabled for a controlled run."
        )

    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_started_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_repository = run_repository or IngestionRunRepository()
    source_results = []

    for source in sources:
        run_id = _start_tracked_run(options, run_repository, source)
        source_report: dict[str, Any] = {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "source_group": source.config.get("source_group"),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            if options.skip_scrape:
                scrape_report = {
                    "source_id": source.source_id,
                    "records_scraped": 0,
                    "inserted": 0,
                    "skipped_duplicate": 0,
                    "updated_existing": 0,
                    "skipped_invalid": 0,
                    "failed": 0,
                    "errors": [],
                    "skipped": True,
                }
            else:
                output_csv = _source_output_csv(
                    output_dir,
                    source.source_id,
                    run_started_at,
                )
                if scrape_func is scrape_catalogue_v3_web:
                    scrape_report = _scrape_source_subprocess(
                        source=source,
                        options=options,
                        output_csv=output_csv,
                        run_started_at=run_started_at,
                    )
                else:
                    scrape_report = scrape_func(
                        source_id=source.source_id,
                        config_path=options.config_path,
                        output_csv=output_csv,
                        ingest=not options.no_ingest and not options.dry_run,
                        allow_disabled=True,
                        max_items=options.max_items,
                        max_pages=options.max_pages,
                        max_depth=options.max_depth,
                        crawl_delay_seconds=options.crawl_delay_seconds,
                        concurrent_requests=options.concurrent_requests,
                        update_existing=options.update_existing,
                    )

            source_report["scrape"] = scrape_report

            if options.skip_enrichment:
                enrichment_report = {"skipped": True}
            else:
                enrichment_report = enrich_func(
                    source=source.source_id,
                    limit=options.enrich_limit or options.max_items or 100000,
                    dry_run=options.dry_run,
                )

            source_report["enrichment"] = enrichment_report

            if options.skip_nutrition:
                nutrition_report = {"skipped": True}
            else:
                nutrition_report = nutrition_func(
                    source=source.source_id,
                    limit=options.nutrition_limit or options.max_items,
                    timeout_seconds=options.nutrition_timeout_seconds,
                    dry_run=options.dry_run,
                )

            source_report["nutrition"] = nutrition_report
            source_report["status"] = "completed"
            source_report["ended_at"] = datetime.now(timezone.utc).isoformat()
            _complete_tracked_run(
                options,
                run_repository,
                run_id,
                source_report,
            )
        except Exception as exc:
            source_report["status"] = "failed"
            source_report["error"] = str(exc)
            source_report["ended_at"] = datetime.now(timezone.utc).isoformat()
            _fail_tracked_run(
                options,
                run_repository,
                run_id,
                exc,
                source_report,
            )

        source_results.append(source_report)

    summary = {
        "run_started_at": run_started_at,
        "dry_run": options.dry_run,
        "selected_sources": [source.source_id for source in sources],
        "totals": _totals(source_results),
        "sources": source_results,
    }
    summary_path = output_dir / f"catalogue_v3_pipeline_{run_started_at}.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    summary["summary_path"] = str(summary_path)

    return summary


def _source_output_csv(output_dir: Path, source_id: str, run_started_at: str) -> Path:
    return output_dir / f"{source_id}_{run_started_at}.csv"


def _scrape_source_subprocess(
    source: SourceConfig,
    options: PipelineOptions,
    output_csv: Path,
    run_started_at: str,
) -> dict[str, Any]:
    summary_json = output_csv.with_suffix(".summary.json")
    log_path = output_csv.with_suffix(".log")
    command = [
        sys.executable,
        "-m",
        "scripts.scrape_catalogue_v3_source_job",
        "--source-id",
        source.source_id,
        "--config",
        str(options.config_path),
        "--output-csv",
        str(output_csv),
        "--summary-json",
        str(summary_json),
        "--allow-disabled",
    ]

    if options.no_ingest or options.dry_run:
        command.append("--no-ingest")
    if options.max_items is not None:
        command.extend(["--max-items", str(options.max_items)])
    if options.max_pages is not None:
        command.extend(["--max-pages", str(options.max_pages)])
    if options.max_depth is not None:
        command.extend(["--max-depth", str(options.max_depth)])
    if options.crawl_delay_seconds is not None:
        command.extend(
            ["--crawl-delay-seconds", str(options.crawl_delay_seconds)]
        )
    if options.concurrent_requests is not None:
        command.extend(
            ["--concurrent-requests", str(options.concurrent_requests)]
        )
    if options.update_existing:
        command.append("--update-existing")

    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=options.source_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(
            "\n".join(
                [
                    "COMMAND:",
                    " ".join(command),
                    "",
                    f"TIMEOUT: {options.source_timeout_seconds} seconds",
                    "",
                    "STDOUT:",
                    exc.stdout or "",
                    "",
                    "STDERR:",
                    exc.stderr or "",
                ]
            ),
            encoding="utf-8",
        )
        raise RuntimeError(
            f"Scrape job timed out for {source.source_id} after "
            f"{options.source_timeout_seconds} seconds. See {log_path}."
        ) from exc
    log_path.write_text(
        "\n".join(
            [
                "COMMAND:",
                " ".join(command),
                "",
                "STDOUT:",
                completed.stdout,
                "",
                "STDERR:",
                completed.stderr,
            ]
        ),
        encoding="utf-8",
    )

    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout)[-2000:].strip()
        raise RuntimeError(
            f"Scrape job failed for {source.source_id}. "
            f"See {log_path}. {tail}"
        )

    if not summary_json.exists():
        raise RuntimeError(
            f"Scrape job did not write summary for {source.source_id}. "
            f"See {log_path}."
        )

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    summary["job_log"] = str(log_path)
    summary["job_started_at"] = run_started_at
    return summary


def _start_tracked_run(
    options: PipelineOptions,
    repository: IngestionRunRepository,
    source: SourceConfig,
) -> int | None:
    if options.dry_run or not options.track_runs:
        return None

    try:
        return repository.start_run(
            source_id=source.source_id,
            source_name=source.source_id,
            source_type=source.source_type,
        )
    except Exception:
        return None


def _complete_tracked_run(
    options: PipelineOptions,
    repository: IngestionRunRepository,
    run_id: int | None,
    source_report: dict[str, Any],
) -> None:
    if options.dry_run or not options.track_runs or run_id is None:
        return

    try:
        repository.complete_run(run_id, _tracking_summary(source_report))
    except Exception:
        pass


def _fail_tracked_run(
    options: PipelineOptions,
    repository: IngestionRunRepository,
    run_id: int | None,
    error: Exception,
    source_report: dict[str, Any],
) -> None:
    if options.dry_run or not options.track_runs or run_id is None:
        return

    try:
        repository.fail_run(run_id, str(error), _tracking_summary(source_report))
    except Exception:
        pass


def _tracking_summary(source_report: dict[str, Any]) -> dict[str, Any]:
    scrape = source_report.get("scrape") or {}
    inserted = int(scrape.get("inserted") or 0)
    updated = int(scrape.get("updated_existing") or 0)
    duplicates = int(scrape.get("skipped_duplicate") or 0)
    invalid = int(scrape.get("skipped_invalid") or 0)
    failed = int(scrape.get("failed") or 0)

    return {
        "records_found": int(scrape.get("records_scraped") or 0),
        "coerced": inserted + updated + duplicates + invalid + failed,
        "accepted": inserted + updated + duplicates,
        "loaded": inserted + updated,
        "review": 0,
        "rejected": invalid,
        "validation_errors": failed,
        "source_report": source_report,
    }


def _totals(source_results: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "records_scraped": 0,
        "inserted": 0,
        "skipped_duplicate": 0,
        "updated_existing": 0,
        "skipped_invalid": 0,
        "failed": 0,
        "enriched": 0,
        "nutrition_updated": 0,
    }

    for result in source_results:
        scrape = result.get("scrape") or {}
        enrichment = result.get("enrichment") or {}
        nutrition = result.get("nutrition") or {}

        for key in [
            "records_scraped",
            "inserted",
            "skipped_duplicate",
            "updated_existing",
            "skipped_invalid",
            "failed",
        ]:
            totals[key] += int(scrape.get(key) or 0)

        totals["enriched"] += int(enrichment.get("updated") or 0)
        totals["nutrition_updated"] += int(nutrition.get("updated") or 0)

    return totals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the automated recipe_catalogue_v3 web pipeline: scrape new "
            "recipes, load to DB, enrich/normalize rows, and backfill "
            "source-provided nutrition where available."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument("--source-group", default=None)
    parser.add_argument("--all-configured-sources", action="store_true")
    parser.add_argument("--allow-disabled", action="store_true")
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--crawl-delay-seconds", type=float, default=None)
    parser.add_argument("--concurrent-requests", type=int, default=None)
    parser.add_argument("--enrich-limit", type=int, default=None)
    parser.add_argument("--nutrition-limit", type=int, default=None)
    parser.add_argument("--nutrition-timeout-seconds", type=int, default=30)
    parser.add_argument("--source-timeout-seconds", type=int, default=420)
    parser.add_argument("--update-existing", action="store_true")
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-enrichment", action="store_true")
    parser.add_argument("--skip-nutrition", action="store_true")
    parser.add_argument("--no-ingest", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-track-runs", action="store_true")
    return parser


def options_from_args(args: argparse.Namespace) -> PipelineOptions:
    return PipelineOptions(
        config_path=args.config,
        output_dir=args.output_dir,
        source_ids=tuple(args.source_id or ()),
        source_group=args.source_group,
        all_configured_sources=args.all_configured_sources,
        allow_disabled=args.allow_disabled,
        max_items=args.max_items,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        crawl_delay_seconds=args.crawl_delay_seconds,
        concurrent_requests=args.concurrent_requests,
        enrich_limit=args.enrich_limit,
        nutrition_limit=args.nutrition_limit,
        nutrition_timeout_seconds=args.nutrition_timeout_seconds,
        source_timeout_seconds=args.source_timeout_seconds,
        update_existing=args.update_existing,
        skip_scrape=args.skip_scrape,
        skip_enrichment=args.skip_enrichment,
        skip_nutrition=args.skip_nutrition,
        no_ingest=args.no_ingest,
        dry_run=args.dry_run,
        track_runs=not args.no_track_runs,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    summary = run_catalogue_v3_pipeline(options_from_args(args))
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
