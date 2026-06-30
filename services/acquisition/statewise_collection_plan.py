import argparse
import json
from pathlib import Path

from services.acquisition.statewise_catalog_report import build_report


DEFAULT_PLAN = Path("configs/statewise_10k_collection_plan.json")


def load_plan(path=DEFAULT_PLAN):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_collection_status(plan_path=DEFAULT_PLAN):
    plan = load_plan(plan_path)
    target_total = plan["target"]["minimum_real_recipes"]
    report = build_report(target_total=target_total)

    remaining_by_source = []
    for source in plan["source_targets"]:
        remaining_by_source.append(
            {
                "source_id": source["source_id"],
                "source_type": source["source_type"],
                "target_records": source["target_records"],
                "state_coverage": source["state_coverage"],
                "status": source["status"],
            }
        )

    return {
        "target": plan["target"],
        "quality_gates": plan["quality_gates"],
        "current": {
            "real_distinct_source_urls": report["current_real_distinct_source_urls"],
            "remaining_real_recipes_to_target": report[
                "remaining_real_recipes_to_target"
            ],
            "target_per_state_or_union_territory": report[
                "target_per_state_or_ut"
            ],
        },
        "source_targets": remaining_by_source,
        "largest_state_gaps": [
            item
            for item in report["coverage_gap"]
            if item["remaining"] > 0
        ][:12],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Show the real-data collection plan for 10k state-wise recipes."
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    status = build_collection_status(args.plan)

    if args.json:
        print(json.dumps(status, indent=2, default=str))
        return

    current = status["current"]
    print(f"Target real recipes: {status['target']['minimum_real_recipes']}")
    print(f"Current real distinct URLs: {current['real_distinct_source_urls']}")
    print(f"Remaining: {current['remaining_real_recipes_to_target']}")
    print(
        "Target per state/UT: "
        f"{current['target_per_state_or_union_territory']}"
    )
    print("\nSource targets:")
    for source in status["source_targets"]:
        print(
            f"- {source['source_id']}: {source['target_records']} "
            f"({source['status']})"
        )


if __name__ == "__main__":
    main()
