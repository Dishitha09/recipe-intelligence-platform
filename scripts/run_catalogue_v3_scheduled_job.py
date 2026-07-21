import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from scripts.catalogue_v3_production_kpi_report import (
    catalogue_v3_production_kpi_report,
)
from scripts.resolve_catalogue_v3_ingredients import resolve_catalogue_v3_ingredients
from scripts.run_catalogue_v3_pipeline import PipelineOptions, run_catalogue_v3_pipeline
from scripts.validate_catalogue_v3 import validate_catalogue_v3


def run_scheduled_job(args):
    started_at = datetime.now(timezone.utc).isoformat()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline_summary = run_catalogue_v3_pipeline(
        PipelineOptions(
            source_ids=tuple(args.source_id or ()),
            source_group=args.source_group,
            all_configured_sources=args.all_configured_sources,
            allow_disabled=args.allow_disabled,
            max_items=args.max_items,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            source_timeout_seconds=args.source_timeout_seconds,
            output_dir=Path(args.pipeline_output_dir),
            dry_run=args.dry_run,
            skip_scrape=args.skip_scrape,
            skip_nutrition=args.skip_nutrition,
            no_ingest=args.no_ingest,
            track_runs=not args.no_track_runs,
        )
    )

    resolution = resolve_catalogue_v3_ingredients(
        limit=args.validation_limit,
        dry_run=args.dry_run,
    )
    validation = validate_catalogue_v3(
        limit=args.validation_limit,
        dry_run=args.dry_run,
    )
    kpi = catalogue_v3_production_kpi_report()

    evidence = {
        "status": "completed",
        "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "pipeline": pipeline_summary,
        "ingredient_resolution": resolution,
        "validation": validation,
        "kpi": kpi,
    }
    evidence_path = output_dir / "scheduled_catalogue_v3_run_latest.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, default=str),
        encoding="utf-8",
    )
    evidence["evidence_path"] = str(evidence_path)
    return evidence


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run the scheduled v3 production pipeline proof: scrape/load, "
            "resolve ingredients, validate, and emit KPI evidence."
        )
    )
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument("--source-group", default="structured_html")
    parser.add_argument("--all-configured-sources", action="store_true")
    parser.add_argument("--allow-disabled", action="store_true")
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=250)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--source-timeout-seconds", type=int, default=420)
    parser.add_argument("--validation-limit", type=int, default=100000)
    parser.add_argument("--pipeline-output-dir", default="data/datasets/catalogue_v3/automated_runs")
    parser.add_argument("--output-dir", default="evidence")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-nutrition", action="store_true")
    parser.add_argument("--no-ingest", action="store_true")
    parser.add_argument("--no-track-runs", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    print(json.dumps(run_scheduled_job(args), indent=2, default=str))


if __name__ == "__main__":
    main()
