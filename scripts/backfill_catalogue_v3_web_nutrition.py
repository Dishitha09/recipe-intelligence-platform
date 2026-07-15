import argparse
import json
from typing import Any

import requests
from scrapy.http import HtmlResponse
from sqlalchemy import text

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.ingestion.web_scraper.parsers.schema_org_recipe_parser import (
    parse_schema_org_recipe,
)


DEFAULT_USER_AGENT = "RecipeIntelligencePlatform/1.0 (+https://example.com)"


def backfill_web_nutrition(
    source: str | None = None,
    limit: int | None = None,
    timeout_seconds: int = 30,
    dry_run: bool = False,
) -> dict[str, Any]:
    rows = _select_rows(source=source, limit=limit)
    report = {
        "selected": len(rows),
        "updated": 0,
        "without_nutrition": 0,
        "failed": 0,
        "dry_run": dry_run,
        "samples": [],
    }

    for row in rows:
        try:
            nutrition_info = _fetch_nutrition(
                row["source_url"],
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            report["failed"] += 1
            if len(report["samples"]) < 5:
                report["samples"].append(
                    {
                        "name": row["name"],
                        "source_url": row["source_url"],
                        "error": str(exc),
                    }
                )
            continue

        if not nutrition_info:
            report["without_nutrition"] += 1
            continue

        report["updated"] += 1
        if len(report["samples"]) < 5:
            report["samples"].append(
                {
                    "name": row["name"],
                    "source_url": row["source_url"],
                    "nutrition_keys": sorted(nutrition_info.keys()),
                }
            )

        if not dry_run:
            _update_nutrition(row["recipe_id"], nutrition_info)

    return report


def _select_rows(source: str | None, limit: int | None) -> list[dict[str, Any]]:
    limit_clause = "LIMIT :limit_value" if limit else ""
    source_clause = "AND source = :source" if source else ""
    query = text(
        f"""
        SELECT
            recipe_id,
            name,
            metadata->>'source_url' AS source_url
        FROM recipe_catalogue_v3
        WHERE metadata->>'source_url' IS NOT NULL
        AND (nutrition_info IS NULL OR nutrition_info = '{{}}'::jsonb)
        {source_clause}
        ORDER BY recipe_id
        {limit_clause}
        """
    )
    params: dict[str, Any] = {}
    if source:
        params["source"] = source
    if limit:
        params["limit_value"] = limit

    with get_catalogue_v3_engine().connect() as conn:
        return [dict(row) for row in conn.execute(query, params).mappings()]


def _fetch_nutrition(source_url: str, timeout_seconds: int) -> dict[str, Any]:
    response = requests.get(
        source_url,
        timeout=timeout_seconds,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    scrapy_response = HtmlResponse(
        url=source_url,
        body=response.content,
        encoding=response.encoding or "utf-8",
    )
    recipe = parse_schema_org_recipe(scrapy_response) or {}
    nutrition = recipe.get("nutrition_info") or {}

    return nutrition if isinstance(nutrition, dict) else {}


def _update_nutrition(recipe_id: int, nutrition_info: dict[str, Any]) -> None:
    with get_catalogue_v3_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE recipe_catalogue_v3
                SET
                    nutrition_info = CAST(:nutrition_info AS jsonb),
                    updated_at = now()
                WHERE recipe_id = :recipe_id
                """
            ),
            {
                "recipe_id": recipe_id,
                "nutrition_info": json.dumps(nutrition_info),
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill real nutrition_info for recipe_catalogue_v3 rows by "
            "re-parsing each stored source_url."
        )
    )
    parser.add_argument("--source", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        json.dumps(
            backfill_web_nutrition(
                source=args.source,
                limit=args.limit,
                timeout_seconds=args.timeout_seconds,
                dry_run=args.dry_run,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
