import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.enrichment.ingredient_resolution.embedding_resolver import (
    EmbeddingResolver,
)


SELECT_MISSING_SQL = text(
    """
    SELECT mi.ingredient_id, mi.canonical_name
    FROM master_ingredients mi
    LEFT JOIN ingredient_embeddings ie
        ON ie.ingredient_id = mi.ingredient_id
    WHERE ie.ingredient_id IS NULL
    ORDER BY mi.ingredient_id
    LIMIT :limit
    """
)


def backfill_catalogue_v3_ingredient_embeddings(limit=100000, batch_size=256, dry_run=False):
    engine = get_catalogue_v3_engine()

    with engine.connect() as conn:
        if not conn.execute(text("SELECT to_regclass('ingredient_embeddings')")).scalar():
            return {
                "status": "skipped",
                "reason": "ingredient_embeddings table is unavailable",
            }

        rows = [
            dict(row)
            for row in conn.execute(
                SELECT_MISSING_SQL,
                {"limit": limit},
            ).mappings()
        ]

    if dry_run:
        return {
            "status": "dry_run",
            "selected_missing": len(rows),
            "inserted": 0,
        }

    resolver = EmbeddingResolver(
        master_ingredients=[
            row["canonical_name"]
            for row in rows[:1]
        ]
        or ["rice"]
    )
    model = resolver.model
    inserted = 0

    with engine.begin() as conn:
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            names = [row["canonical_name"] for row in batch]
            embeddings = model.encode(names)

            for row, embedding in zip(batch, embeddings):
                conn.execute(
                    text(
                        """
                        INSERT INTO ingredient_embeddings (
                            ingredient_id, embedding
                        )
                        VALUES (
                            :ingredient_id, CAST(:embedding AS vector)
                        )
                        ON CONFLICT (ingredient_id)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            created_at = now()
                        """
                    ),
                    {
                        "ingredient_id": row["ingredient_id"],
                        "embedding": _vector_literal(embedding),
                    },
                )
                inserted += 1

    return {
        "status": "completed",
        "selected_missing": len(rows),
        "inserted": inserted,
    }


def _vector_literal(embedding):
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()

    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def main():
    parser = argparse.ArgumentParser(
        description="Backfill missing v3 master ingredient pgvector embeddings."
    )
    parser.add_argument("--limit", type=int, default=100000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        json.dumps(
            backfill_catalogue_v3_ingredient_embeddings(
                limit=args.limit,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
