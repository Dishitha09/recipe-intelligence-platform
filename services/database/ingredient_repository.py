from sqlalchemy import text

from services.database.connection import engine
from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
)


class IngredientRepository:


    def get_ingredient_id(

        self,

        canonical_name

    ):


        with engine.begin() as conn:


            result = conn.execute(

                text("""

                SELECT ingredient_id

                FROM master_ingredients

                WHERE canonical_name=:name

                """),

                {

                    "name": canonical_name

                }

            )


            row = result.fetchone()


            if row:

                return row[0]


            return None

    def resolve_exact(

        self,

        raw_name

    ):

        normalized_name = normalize_ingredient_name(raw_name)

        if not normalized_name:

            return None

        with engine.begin() as conn:


            result = conn.execute(

                text("""

                SELECT
                    mi.ingredient_id,
                    mi.canonical_name
                FROM ingredient_aliases ia
                JOIN master_ingredients mi
                    ON mi.ingredient_id = ia.ingredient_id
                WHERE LOWER(ia.alias_name)=:name

                UNION ALL

                SELECT
                    mi.ingredient_id,
                    mi.canonical_name
                FROM master_ingredients mi
                WHERE LOWER(mi.canonical_name)=:name

                LIMIT 1

                """),

                {

                    "name": normalized_name

                }

            )


            row = result.fetchone()


            if row:

                return {
                    "ingredient_id": row[0],
                    "canonical_name": row[1],
                }


            return None

    def search_by_embedding(

        self,

        embedding,

        threshold=0.88

    ):

        vector_literal = self._vector_literal(embedding)

        with engine.begin() as conn:


            result = conn.execute(

                text("""

                SELECT
                    mi.ingredient_id,
                    mi.canonical_name,
                    1 - (ie.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM ingredient_embeddings ie
                JOIN master_ingredients mi
                    ON mi.ingredient_id = ie.ingredient_id
                WHERE 1 - (ie.embedding <=> CAST(:embedding AS vector)) >= :threshold
                ORDER BY ie.embedding <=> CAST(:embedding AS vector)
                LIMIT 1

                """),

                {

                    "embedding": vector_literal,
                    "threshold": threshold

                }

            )


            row = result.fetchone()


            if row:

                return {
                    "ingredient_id": row[0],
                    "canonical_name": row[1],
                    "confidence_score": round(float(row[2]), 4),
                }


            return None

    def upsert_master_ingredient(

        self,

        canonical_name,

        category=None,

        default_unit=None,

        density_g_per_ml=None

    ):

        with engine.begin() as conn:


            result = conn.execute(

                text("""

                INSERT INTO master_ingredients
                    (canonical_name, category, default_unit, density_g_per_ml)
                VALUES
                    (:canonical_name, :category, :default_unit, :density_g_per_ml)
                ON CONFLICT (canonical_name)
                DO UPDATE SET
                    category = COALESCE(EXCLUDED.category, master_ingredients.category),
                    default_unit = COALESCE(EXCLUDED.default_unit, master_ingredients.default_unit),
                    density_g_per_ml = COALESCE(EXCLUDED.density_g_per_ml, master_ingredients.density_g_per_ml)
                RETURNING ingredient_id

                """),

                {
                    "canonical_name": canonical_name,
                    "category": category,
                    "default_unit": default_unit,
                    "density_g_per_ml": density_g_per_ml,
                }

            )


            return result.scalar()

    def upsert_alias(

        self,

        ingredient_id,

        alias_name,

        language=None,

        source="seed"

    ):

        with engine.begin() as conn:


            conn.execute(

                text("""

                INSERT INTO ingredient_aliases
                    (ingredient_id, alias_name, language, source)
                SELECT
                    :ingredient_id, :alias_name, :language, :source
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM ingredient_aliases
                    WHERE LOWER(alias_name)=LOWER(:alias_name)
                )

                """),

                {
                    "ingredient_id": ingredient_id,
                    "alias_name": alias_name,
                    "language": language,
                    "source": source,
                }

            )

    def upsert_embedding(

        self,

        ingredient_id,

        embedding

    ):

        vector_literal = self._vector_literal(embedding)

        with engine.begin() as conn:


            conn.execute(

                text("""

                DELETE FROM ingredient_embeddings
                WHERE ingredient_id=:ingredient_id

                """),

                {
                    "ingredient_id": ingredient_id,
                }

            )


            conn.execute(

                text("""

                INSERT INTO ingredient_embeddings
                    (ingredient_id, embedding)
                VALUES
                    (:ingredient_id, CAST(:embedding AS vector))

                """),

                {
                    "ingredient_id": ingredient_id,
                    "embedding": vector_literal,
                }

            )

    def _vector_literal(self, embedding):

        values = embedding[0] if hasattr(embedding, "__len__") and len(embedding) == 1 else embedding

        if hasattr(values, "tolist"):

            values = values.tolist()

        return "[" + ",".join(str(float(value)) for value in values) + "]"
