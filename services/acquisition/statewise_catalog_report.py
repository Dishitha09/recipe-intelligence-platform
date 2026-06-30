import argparse
import json
import math

from sqlalchemy import text

from configs.india_states import INDIA_STATES, UNION_TERRITORIES
from services.database.connection import engine


def build_report(target_total=10000, include_union_territories=True):
    places = list(INDIA_STATES)
    if include_union_territories:
        places.extend(UNION_TERRITORIES)

    target_per_place = math.ceil(target_total / len(places))

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT state, region, recipe_count, avg_state_confidence,
                       distinct_source_urls
                FROM recipe_state_coverage
                ORDER BY recipe_count DESC, state ASC
                """
            )
        ).mappings().all()

        total_recipes = conn.execute(text("SELECT count(*) FROM recipes")).scalar() or 0
        real_distinct_urls = conn.execute(
            text(
                """
                SELECT count(DISTINCT source_url)
                FROM recipes
                WHERE source_url IS NOT NULL
                  AND source_url NOT LIKE 'https://example.com/%'
                """
            )
        ).scalar() or 0

    by_state = {row["state"]: dict(row) for row in rows}
    coverage = []
    for place in places:
        count = int(by_state.get(place, {}).get("recipe_count", 0))
        coverage.append(
            {
                "state": place,
                "current_count": count,
                "target_count": target_per_place,
                "remaining": max(target_per_place - count, 0),
            }
        )

    return {
        "target_total": target_total,
        "target_per_state_or_ut": target_per_place,
        "current_total_recipes": total_recipes,
        "current_real_distinct_source_urls": real_distinct_urls,
        "current_state_coverage": [dict(row) for row in rows],
        "coverage_gap": coverage,
        "remaining_real_recipes_to_target": max(target_total - real_distinct_urls, 0),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Report state-wise recipe coverage against a real-data target."
    )
    parser.add_argument("--target-total", type=int, default=10000)
    parser.add_argument("--states-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(
        target_total=args.target_total,
        include_union_territories=not args.states_only,
    )

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return

    print(f"Target real recipes: {report['target_total']}")
    print(f"Current real distinct URLs: {report['current_real_distinct_source_urls']}")
    print(f"Remaining to target: {report['remaining_real_recipes_to_target']}")
    print(f"Target per state/UT: {report['target_per_state_or_ut']}")
    print("\nState coverage gaps:")
    for item in report["coverage_gap"]:
        if item["remaining"] > 0:
            print(
                f"- {item['state']}: {item['current_count']} / "
                f"{item['target_count']} "
                f"(remaining {item['remaining']})"
            )


if __name__ == "__main__":
    main()
