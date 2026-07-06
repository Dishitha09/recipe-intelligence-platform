import argparse
import json

from sqlalchemy import text

from services.database.connection import engine


def build_report(limit=25):
    with engine.connect() as conn:
        total = _scalar(
            conn,
            "SELECT count(*) FROM recipe_ingredients",
        )
        resolved = _scalar(
            conn,
            """
            SELECT count(*)
            FROM recipe_ingredients
            WHERE ingredient_id IS NOT NULL
               OR canonical_name IS NOT NULL
            """,
        )
        llm_resolved = _scalar(
            conn,
            """
            SELECT count(*)
            FROM recipe_ingredients
            WHERE resolution_method = 'llm'
            """,
        )
        raw_name_rows = _scalar(
            conn,
            """
            SELECT count(*)
            FROM recipe_ingredients
            WHERE ingredient_name IS NOT NULL
              AND trim(ingredient_name) <> ''
            """,
        )
        hnsw_indexes = _scalar(
            conn,
            """
            SELECT count(*)
            FROM pg_indexes
            WHERE indexname IN (
                'idx_ingredient_embeddings_hnsw',
                'idx_recipe_embeddings_hnsw'
            )
            """,
        )
        unresolved = [
            dict(row._mapping)
            for row in conn.execute(
                text(
                    """
                    SELECT
                        ingredient_name,
                        unit,
                        count(*) AS row_count
                    FROM recipe_ingredients
                    WHERE ingredient_id IS NULL
                      AND canonical_name IS NULL
                    GROUP BY ingredient_name, unit
                    ORDER BY row_count DESC, ingredient_name NULLS LAST
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ]

    return {
        "ingredient_rows": total,
        "resolved_rows": resolved,
        "unresolved_rows": total - resolved,
        "resolution_rate": _rate(resolved, total),
        "llm_resolved_rows": llm_resolved,
        "llm_escalation_rate": _rate(llm_resolved, total),
        "rows_with_raw_ingredient_name": raw_name_rows,
        "hnsw_indexes": hnsw_indexes,
        "top_unresolved": unresolved,
    }


def _scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar() or 0


def _rate(numerator, denominator):
    if not denominator:
        return 0.0

    return round(float(numerator) / float(denominator), 4)


def _safe_print(value):
    print(str(value).encode("ascii", errors="replace").decode("ascii"))


def main():
    parser = argparse.ArgumentParser(
        description="Print PS-3 ingredient resolution evidence."
    )
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(limit=args.limit)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return

    print("ShopConnect PS-3 ingredient resolution report")
    print("=" * 48)
    for key in [
        "ingredient_rows",
        "resolved_rows",
        "unresolved_rows",
        "resolution_rate",
        "llm_resolved_rows",
        "llm_escalation_rate",
        "rows_with_raw_ingredient_name",
        "hnsw_indexes",
    ]:
        print(f"{key}: {report[key]}")

    print("top_unresolved:")
    for row in report["top_unresolved"]:
        _safe_print(
            "  "
            f"{row.get('ingredient_name') or '<missing raw name>'}"
            f" | unit={row.get('unit') or '<none>'}"
            f" | rows={row['row_count']}"
        )


if __name__ == "__main__":
    main()
