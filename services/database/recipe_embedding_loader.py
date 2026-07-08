import argparse

from sqlalchemy import text

from services.database.connection import engine
from services.database.recipe_text_builder import RecipeTextBuilder
from services.enrichment.embedding_generator import EmbeddingGenerator


class RecipeEmbeddingLoader:
    def __init__(self, generator=None, text_builder=None):
        self.generator = generator or EmbeddingGenerator()
        self.text_builder = text_builder or RecipeTextBuilder()

    def load_embeddings(self, source_type=None, limit=None, refresh=False):
        with engine.begin() as conn:
            recipes = conn.execute(
                text(
                    """
                    WITH ingredient_lines AS (
                        SELECT
                            recipe_id,
                            STRING_AGG(
                                CONCAT_WS(
                                    ' ',
                                    NULLIF(TRIM(TRAILING '.0' FROM quantity::text), ''),
                                    unit,
                                    ingredient_name
                                ),
                                ', '
                                ORDER BY recipe_ingredient_id
                            ) AS ingredients
                        FROM recipe_ingredients
                        GROUP BY recipe_id
                    )
                    SELECT
                        r.recipe_id,
                        r.title,
                        r.description,
                        r.cuisine,
                        il.ingredients,
                        v.instructions_one_line AS instructions
                    FROM recipes r
                    LEFT JOIN ingredient_lines il
                        ON il.recipe_id = r.recipe_id
                    LEFT JOIN recipe_with_instructions v
                        ON v.recipe_id = r.recipe_id
                    WHERE (:source_type IS NULL OR r.source_type = :source_type)
                      AND (
                            :refresh
                         OR NOT EXISTS (
                                SELECT 1
                                FROM recipe_embeddings re
                                WHERE re.recipe_id = r.recipe_id
                            )
                      )
                    ORDER BY r.recipe_id
                    LIMIT COALESCE(:limit, 2147483647)
                    """
                ),
                {
                    "source_type": source_type,
                    "limit": limit,
                    "refresh": refresh,
                },
            ).fetchall()

            summary = {
                "selected": len(recipes),
                "embedded": 0,
                "source_type": source_type,
                "refresh": refresh,
            }

            for row in recipes:
                recipe_id = row.recipe_id
                text_for_embedding = self.text_builder.build(dict(row._mapping))
                embedding = self.generator.generate_embedding(text_for_embedding)

                conn.execute(
                    text(
                        """
                        DELETE FROM recipe_embeddings
                        WHERE recipe_id = :recipe_id
                        """
                    ),
                    {"recipe_id": recipe_id},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO recipe_embeddings
                            (recipe_id, embedding)
                        VALUES
                            (:recipe_id, CAST(:embedding AS vector))
                        """
                    ),
                    {
                        "recipe_id": recipe_id,
                        "embedding": self._vector_literal(embedding),
                    },
                )

                summary["embedded"] += 1
                if summary["embedded"] % 100 == 0:
                    print(
                        "Embedded:",
                        summary["embedded"],
                        "of",
                        summary["selected"],
                    )

            return summary

    def insert_embedding(self, recipe_id, embedding):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM recipe_embeddings
                    WHERE recipe_id = :recipe_id
                    """
                ),
                {"recipe_id": recipe_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO recipe_embeddings
                        (recipe_id, embedding)
                    VALUES
                        (:recipe_id, CAST(:embedding AS vector))
                    """
                ),
                {
                    "recipe_id": recipe_id,
                    "embedding": self._vector_literal(embedding),
                },
            )

    def _vector_literal(self, embedding):
        values = (
            embedding[0]
            if hasattr(embedding, "__len__") and len(embedding) == 1
            else embedding
        )

        if hasattr(values, "tolist"):
            values = values.tolist()

        return "[" + ",".join(str(float(value)) for value in values) + "]"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backfill pgvector recipe embeddings from loaded recipes."
    )
    parser.add_argument("--source-type")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    summary = RecipeEmbeddingLoader().load_embeddings(
        source_type=args.source_type,
        limit=args.limit,
        refresh=args.refresh,
    )
    print(summary)


if __name__ == "__main__":
    main()
