import argparse
from pathlib import Path

from services.ingestion.source_registry import SourceRegistry
from services.pipeline.recipe_pipeline import RecipePipeline


def main():
    parser = argparse.ArgumentParser(
        description="Run a Scrapy-based recipe crawl source and ingest results."
    )
    parser.add_argument(
        "--source-id",
        type=str,
        required=True,
        help="Source ID to enable from configs/production_recipe_sources.json",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/production_recipe_sources.json"),
        help="Path to the source registry configuration file.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/datasets/generated/scrapy_crawl_output.csv"),
        help="Optional path to persist scraped records before ingestion.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=25,
        help="Chunk size for ingestion pipeline.",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Run ingestion after scraping.",
    )
    parser.add_argument(
        "--allow-disabled",
        action="store_true",
        help="Allow a disabled source to run for a one-off controlled crawl.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Stop the crawl after this many scraped recipe items.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Stop the crawl after this many downloaded pages.",
    )
    args = parser.parse_args()

    registry = SourceRegistry(config_path=str(args.config))
    source = next(
        (item for item in registry.configs if item.source_id == args.source_id),
        None,
    )

    if source is None:
        raise ValueError(f"Source ID {args.source_id} not found in config")

    if not source.enabled and not args.allow_disabled:
        raise ValueError(f"Source {args.source_id} is disabled in config")

    if args.max_items is not None:
        source.config["max_items"] = args.max_items

    if args.max_pages is not None:
        source.config["max_pages"] = args.max_pages

    adapter = registry.build_adapter(source)
    raw_records = adapter.extract()

    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
            import csv

            fieldnames = ["title", "description", "source_url", "ingredients", "steps"]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()

            for record in raw_records:
                content = record.raw_content
                writer.writerow(
                    {
                        "title": content.get("title", ""),
                        "description": content.get("description", ""),
                        "source_url": content.get("source_url", ""),
                        "ingredients": " | ".join(content.get("ingredients", [])),
                        "steps": " | ".join(content.get("steps", [])),
                    }
                )

        print(f"Wrote {len(raw_records)} scraped records to {args.output_csv}")

    if args.ingest:
        pipeline = RecipePipeline()
        totals = {"accepted": 0, "loaded": 0, "rejected": 0, "coerced": 0}

        for start in range(0, len(raw_records), args.chunk_size):
            chunk = raw_records[start : start + args.chunk_size]
            chunk_path = args.output_csv.with_name(
                f"{args.output_csv.stem}_chunk_{start // args.chunk_size + 1:03d}.csv"
            )
            chunk_path.parent.mkdir(parents=True, exist_ok=True)

            with chunk_path.open("w", encoding="utf-8", newline="") as handle:
                import csv

                fieldnames = ["title", "description", "source_url", "ingredients", "steps"]
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()

                for record in chunk:
                    content = record.raw_content
                    writer.writerow(
                        {
                            "title": content.get("title", ""),
                            "description": content.get("description", ""),
                            "source_url": content.get("source_url", ""),
                            "ingredients": " | ".join(content.get("ingredients", [])),
                            "steps": " | ".join(content.get("steps", [])),
                        }
                    )

            summary = pipeline.run_csv_pipeline(str(chunk_path))
            for key in totals:
                totals[key] += summary.get(key, 0)

        print("Ingestion summary:", totals)


if __name__ == "__main__":
    main()
