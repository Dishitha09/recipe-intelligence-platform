import argparse
import os
import time

import requests
from scrapy.http import HtmlResponse
from sqlalchemy import text

from services.database.connection import engine
from services.ingestion.web_scraper.parsers.schema_org_recipe_parser import (
    parse_schema_org_recipe,
)


DEFAULT_DOMAIN = "indianhealthyrecipes.com"
DEFAULT_USER_AGENT = (
    "RecipeIntelligencePlatform/1.0 "
    "(+mailto:your-email@example.com)"
)


def fetch_recipe_rows(domain=None, url=None, limit=None):
    clauses = ["r.source_url IS NOT NULL"]
    params = {}

    if domain:
        clauses.append("r.source_url ILIKE :domain_pattern")
        params["domain_pattern"] = f"%{domain}%"

    if url:
        clauses.append("r.source_url = :url")
        params["url"] = url

    limit_sql = ""

    if limit is not None:
        limit_sql = "LIMIT :limit"
        params["limit"] = limit

    with engine.connect() as conn:
        return conn.execute(
            text(
                f"""
                SELECT
                    r.recipe_id,
                    r.title,
                    r.source_url,
                    COUNT(rs.recipe_step_id) AS old_step_count,
                    COALESCE(SUM(length(rs.instruction)), 0) AS old_chars
                FROM recipes r
                LEFT JOIN recipe_steps rs
                    ON rs.recipe_id = r.recipe_id
                WHERE {" AND ".join(clauses)}
                GROUP BY r.recipe_id, r.title, r.source_url
                ORDER BY r.recipe_id
                {limit_sql}
                """
            ),
            params,
        ).fetchall()


def fetch_html(url, timeout_seconds):
    user_agent = os.getenv(
        "RECIPE_PIPELINE_USER_AGENT",
        DEFAULT_USER_AGENT,
    )
    response = requests.get(
        url,
        headers={"User-Agent": user_agent},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response


def parse_steps_from_html(url, html_response):
    response = HtmlResponse(
        url=url,
        body=html_response.content,
        encoding=html_response.encoding or "utf-8",
    )
    recipe = parse_schema_org_recipe(response)

    if not recipe:
        return [], "not_found"

    return recipe.get("steps", []), recipe.get("instruction_source")


def should_update(row, steps, min_char_gain, force):
    if force:
        return bool(steps)

    new_chars = sum(len(step) for step in steps)
    old_chars = int(row.old_chars or 0)
    old_count = int(row.old_step_count or 0)

    if not steps:
        return False

    if len(steps) > old_count and new_chars >= old_chars:
        return True

    return new_chars >= old_chars + min_char_gain


def replace_steps(recipe_id, steps):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM recipe_steps
                WHERE recipe_id = :recipe_id
                """
            ),
            {"recipe_id": recipe_id},
        )

        for index, step in enumerate(steps, start=1):
            conn.execute(
                text(
                    """
                    INSERT INTO recipe_steps
                        (recipe_id, step_number, instruction)
                    VALUES
                        (:recipe_id, :step_number, :instruction)
                    """
                ),
                {
                    "recipe_id": recipe_id,
                    "step_number": index,
                    "instruction": step,
                },
            )

        conn.execute(
            text(
                """
                UPDATE recipes
                SET updated_at = CURRENT_TIMESTAMP
                WHERE recipe_id = :recipe_id
                """
            ),
            {"recipe_id": recipe_id},
        )


def backfill(args):
    rows = fetch_recipe_rows(
        domain=args.source_domain,
        url=args.url,
        limit=args.limit,
    )
    summary = {
        "checked": 0,
        "updated": 0,
        "skipped_not_better": 0,
        "failed": 0,
    }

    for row in rows:
        summary["checked"] += 1

        try:
            html_response = fetch_html(row.source_url, args.timeout_seconds)
            steps, instruction_source = parse_steps_from_html(
                row.source_url,
                html_response,
            )
            new_chars = sum(len(step) for step in steps)
            update = should_update(
                row,
                steps,
                min_char_gain=args.min_char_gain,
                force=args.force,
            )

            if update and not args.dry_run:
                replace_steps(row.recipe_id, steps)

            if update:
                summary["updated"] += 1
                action = "would_update" if args.dry_run else "updated"
            else:
                summary["skipped_not_better"] += 1
                action = "skipped"

            print(
                {
                    "recipe_id": row.recipe_id,
                    "title": row.title,
                    "action": action,
                    "instruction_source": instruction_source,
                    "old_steps": int(row.old_step_count or 0),
                    "new_steps": len(steps),
                    "old_chars": int(row.old_chars or 0),
                    "new_chars": new_chars,
                }
            )
        except Exception as exc:
            summary["failed"] += 1
            print(
                {
                    "recipe_id": row.recipe_id,
                    "title": row.title,
                    "action": "failed",
                    "error": str(exc),
                }
            )

        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    print("Backfill summary:", summary)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill fuller source-derived recipe instructions."
    )
    parser.add_argument("--source-domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--url", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--min-char-gain", type=int, default=180)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    backfill(args)


if __name__ == "__main__":
    main()
