import argparse
import ast
import csv
import hashlib
import html
import json
from pathlib import Path

from sqlalchemy import text

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_loader import CatalogueV3Loader
from services.ingestion.source_registry import SourceRegistry


DEFAULT_OUTPUT = Path("data/datasets/catalogue_v3/web_scrape_output.csv")


def scrape_catalogue_v3_web(
    source_id,
    config_path=Path("configs/production_recipe_sources.json"),
    output_csv=DEFAULT_OUTPUT,
    ingest=True,
    allow_disabled=True,
    max_items=None,
    max_pages=None,
    max_depth=None,
    crawl_delay_seconds=None,
    concurrent_requests=None,
):
    source = _load_source(source_id, config_path, allow_disabled)
    _apply_runtime_overrides(
        source,
        max_items=max_items,
        max_pages=max_pages,
        max_depth=max_depth,
        crawl_delay_seconds=crawl_delay_seconds,
        concurrent_requests=concurrent_requests,
        output_csv=output_csv,
    )

    adapter = SourceRegistry().build_adapter(source)
    raw_records = adapter.extract()
    payloads = [
        record_to_catalogue_v3_payload(record, source)
        for record in raw_records
    ]
    report = _load_payloads(payloads, ingest=ingest)

    if output_csv:
        write_scrape_csv(output_csv, payloads)

    return {
        "source_id": source.source_id,
        "source_url": source.location,
        "records_scraped": len(raw_records),
        **report,
        "output_csv": str(output_csv) if output_csv else None,
    }


def record_to_catalogue_v3_payload(record, source):
    content = record.raw_content
    source_url = clean(content.get("source_url"))
    ingredients = clean_list(content.get("ingredients"))
    steps = clean_list(content.get("steps"))
    title = clean(content.get("title"))
    content_hash = recipe_content_hash(title, source_url, ingredients, steps)
    servings = to_int(content.get("servings"))

    return {
        "name": title,
        "description": clean(content.get("description")) or None,
        "nutrition_info": json_object(content.get("nutrition_info")),
        "tags": clean_list(content.get("tags")),
        "metadata": {
            "source_url": source_url,
            "content_hash": content_hash,
            "scrape_source": source.location,
            "source_id": source.source_id,
            "source_group": source.config.get("source_group"),
            "parser": source.config.get("parser"),
            "instruction_source": content.get("instruction_source"),
            "servings_source": "source_recipe_yield" if servings else None,
        },
        "servings": servings,
        "difficulty_level": None,
        "youtube_url": None,
        "image_url": clean(content.get("image")) or None,
        "course": lower_list(content.get("course")),
        "region": None,
        "diet": None,
        "spice_level": None,
        "complexity": None,
        "budget_band": None,
        "diet_tags": [],
        "allergen_tags": [],
        "cuisines": clean_list(content.get("cuisines")),
        "meal_types": meal_types_from_course(content.get("course")),
        "dish_types": [],
        "texture": [],
        "prep_time_min": to_int(content.get("prep_time_min")),
        "cook_time_min": to_int(content.get("cook_time_min")),
        "total_time_min": to_int(content.get("total_time_min")),
        "passive_time_min": None,
        "ingredients_json": [
            {
                "raw_text": ingredient,
                "source_position": index,
            }
            for index, ingredient in enumerate(ingredients, start=1)
        ],
        "prep_steps": [],
        "cook_steps": [
            {
                "step_number": index,
                "instruction": step,
            }
            for index, step in enumerate(steps, start=1)
        ],
        "quick_steps": steps[:5],
        "estimated_cost_per_serving": None,
        "popularity_score": 0,
        "side_category": None,
        "meal_role": None,
        "dish_family": None,
        "health_tags": [],
        "efficiency_tags": [],
        "experience_tags": [],
        "cost_tier": None,
        "festival_tags": [],
        "owner_code": None,
        "owner_name": None,
        "source": source.source_id,
        "language": "en",
        "is_public": False,
        "created_by": "web_scraper",
        "is_active": True,
    }


def _load_payloads(payloads, ingest):
    report = {
        "inserted": 0,
        "skipped_duplicate": 0,
        "skipped_invalid": 0,
        "failed": 0,
        "errors": [],
    }

    if not ingest:
        return report

    loader = CatalogueV3Loader()

    for payload in payloads:
        invalid_reason = validation_skip_reason(payload)
        if invalid_reason:
            report["skipped_invalid"] += 1
            report["errors"].append(
                {
                    "name": payload.get("name"),
                    "source_url": payload.get("metadata", {}).get("source_url"),
                    "reason": invalid_reason,
                }
            )
            continue

        if already_loaded(payload):
            report["skipped_duplicate"] += 1
            continue

        try:
            loader.insert_recipe(payload)
            report["inserted"] += 1
        except Exception as exc:
            report["failed"] += 1
            report["errors"].append(
                {
                    "name": payload.get("name"),
                    "source_url": payload.get("metadata", {}).get("source_url"),
                    "reason": str(exc),
                }
            )

            if report["failed"] >= 10:
                break

    report["errors"] = report["errors"][:20]
    return report


def validation_skip_reason(payload):
    if not clean(payload.get("name")):
        return "missing_name"
    if not payload.get("servings"):
        return "missing_source_servings"
    if not payload.get("ingredients_json"):
        return "missing_ingredients"
    if not payload.get("cook_steps"):
        return "missing_cook_steps"
    if not payload.get("metadata", {}).get("source_url"):
        return "missing_source_url"

    return None


def already_loaded(payload):
    metadata = payload.get("metadata", {})
    source_url = metadata.get("source_url")
    content_hash = metadata.get("content_hash")

    with get_catalogue_v3_engine().connect() as conn:
        return bool(
            conn.execute(
                text(
                    """
                    SELECT 1
                    FROM recipe_catalogue_v3
                    WHERE metadata->>'source_url' = :source_url
                    OR metadata->>'content_hash' = :content_hash
                    LIMIT 1
                    """
                ),
                {
                    "source_url": source_url,
                    "content_hash": content_hash,
                },
            ).scalar()
        )


def write_scrape_csv(output_csv, payloads):
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "source",
                "source_url",
                "servings",
                "prep_time_min",
                "cook_time_min",
                "total_time_min",
                "image_url",
                "ingredients_json",
                "cook_steps",
            ],
        )
        writer.writeheader()

        for payload in payloads:
            writer.writerow(
                {
                    "name": payload.get("name"),
                    "source": payload.get("source"),
                    "source_url": payload.get("metadata", {}).get("source_url"),
                    "servings": payload.get("servings"),
                    "prep_time_min": payload.get("prep_time_min"),
                    "cook_time_min": payload.get("cook_time_min"),
                    "total_time_min": payload.get("total_time_min"),
                    "image_url": payload.get("image_url"),
                    "ingredients_json": json.dumps(
                        payload.get("ingredients_json") or [],
                        ensure_ascii=False,
                    ),
                    "cook_steps": json.dumps(
                        payload.get("cook_steps") or [],
                        ensure_ascii=False,
                    ),
                }
            )


def _load_source(source_id, config_path, allow_disabled):
    registry = SourceRegistry(config_path=str(config_path))
    source = next(
        (item for item in registry.configs if item.source_id == source_id),
        None,
    )

    if source is None:
        raise ValueError(f"Source ID {source_id} not found in {config_path}")

    if source.adapter != "scrapy":
        raise ValueError(f"Source {source_id} is not a scrapy web source")

    if not source.enabled and not allow_disabled:
        raise ValueError(f"Source {source_id} is disabled")

    return source


def _apply_runtime_overrides(
    source,
    max_items,
    max_pages,
    max_depth,
    crawl_delay_seconds,
    concurrent_requests,
    output_csv,
):
    if max_items is not None:
        source.config["max_items"] = max_items
    if max_pages is not None:
        source.config["max_pages"] = max_pages
    if max_depth is not None:
        source.config["max_depth"] = max_depth
    if crawl_delay_seconds is not None:
        source.config["crawl_delay_seconds"] = crawl_delay_seconds
    if concurrent_requests is not None:
        source.config["concurrent_requests"] = concurrent_requests
    if output_csv:
        source.config["checkpoint_csv_path"] = str(
            Path(output_csv).with_suffix(".partial.csv")
        )


def recipe_content_hash(title, source_url, ingredients, steps):
    payload = json.dumps(
        {
            "title": clean(title).casefold(),
            "source_url": clean(source_url),
            "ingredients": ingredients,
            "steps": steps,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_list(value):
    if not value:
        return []

    if isinstance(value, str):
        value = value.split("|")

    cleaned = []
    for item in value:
        text_value = clean(item)
        if text_value and text_value not in cleaned:
            cleaned.append(text_value)

    return cleaned


def lower_list(value):
    return [
        item.lower()
        for item in clean_list(value)
    ]


def clean(value):
    return " ".join(html.unescape(str(value or "")).split()).strip()


def json_object(value):
    if isinstance(value, dict):
        return value

    if not value:
        return {}

    if isinstance(value, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(value)
            except (ValueError, SyntaxError, TypeError, json.JSONDecodeError):
                continue

            if isinstance(parsed, dict):
                return parsed

    return {}


def to_int(value):
    value = clean(value)
    if not value:
        return None

    try:
        parsed = int(float(value))
    except ValueError:
        return None

    return parsed if parsed > 0 else None


def meal_types_from_course(course):
    text_value = " ".join(clean_list(course)).lower()
    return [
        token
        for token in ["breakfast", "lunch", "dinner", "snack"]
        if token in text_value
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Scrape real webpage recipes into recipe_catalogue_v3."
    )
    parser.add_argument("--source-id", required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/production_recipe_sources.json"),
    )
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-ingest", action="store_true")
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--crawl-delay-seconds", type=float, default=None)
    parser.add_argument("--concurrent-requests", type=int, default=None)
    args = parser.parse_args()

    print(
        json.dumps(
            scrape_catalogue_v3_web(
                source_id=args.source_id,
                config_path=args.config,
                output_csv=args.output_csv,
                ingest=not args.no_ingest,
                max_items=args.max_items,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                crawl_delay_seconds=args.crawl_delay_seconds,
                concurrent_requests=args.concurrent_requests,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
