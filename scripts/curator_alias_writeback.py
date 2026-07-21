import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_curator_repository import (
    CatalogueV3CuratorRepository,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Write a curator-approved alias correction into the v3 master "
            "ingredient catalogue so the next ingredient resolution run uses "
            "Tier 1 exact alias matching."
        )
    )
    parser.add_argument("--canonical-name", required=True)
    parser.add_argument("--alias-name", required=True)
    parser.add_argument("--language", default=None)
    parser.add_argument("--source", default="curator")
    parser.add_argument("--corrected-by", default=None)
    args = parser.parse_args()

    result = CatalogueV3CuratorRepository().write_back_alias(
        canonical_name=args.canonical_name,
        alias_name=args.alias_name,
        language=args.language,
        source=args.source,
        corrected_by=args.corrected_by,
    )
    result["verification"] = CatalogueV3CuratorRepository().resolve_alias(
        args.alias_name,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
