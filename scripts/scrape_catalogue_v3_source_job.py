import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.acquisition.scrape_catalogue_v3_web import scrape_catalogue_v3_web


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one recipe_catalogue_v3 web scrape source job."
    )
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--allow-disabled", action="store_true")
    parser.add_argument("--no-ingest", action="store_true")
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--crawl-delay-seconds", type=float, default=None)
    parser.add_argument("--concurrent-requests", type=int, default=None)
    parser.add_argument("--update-existing", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    summary = scrape_catalogue_v3_web(
        source_id=args.source_id,
        config_path=args.config,
        output_csv=args.output_csv,
        ingest=not args.no_ingest,
        allow_disabled=args.allow_disabled,
        max_items=args.max_items,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        crawl_delay_seconds=args.crawl_delay_seconds,
        concurrent_requests=args.concurrent_requests,
        update_existing=args.update_existing,
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
