from sqlalchemy import text

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
)
from services.reliability.retry import transient_retry


class CatalogueV3CuratorRepository:
    def __init__(self, engine=None):
        self.engine = engine or get_catalogue_v3_engine()

    @transient_retry
    def write_back_alias(
        self,
        canonical_name,
        alias_name,
        language=None,
        source="curator",
        corrected_by=None,
    ):
        if not canonical_name or not alias_name:
            raise ValueError("canonical_name and alias_name are required")

        canonical_name = normalize_ingredient_name(canonical_name).replace(
            " ",
            "_",
        )
        alias_name = normalize_ingredient_name(alias_name)

        with self.engine.begin() as conn:
            ingredient_id = conn.execute(
                text(
                    """
                    INSERT INTO master_ingredients (canonical_name)
                    VALUES (:canonical_name)
                    ON CONFLICT (canonical_name)
                    DO UPDATE SET canonical_name = EXCLUDED.canonical_name
                    RETURNING ingredient_id
                    """
                ),
                {"canonical_name": canonical_name},
            ).scalar()

            conn.execute(
                text(
                    """
                    INSERT INTO ingredient_aliases (
                        ingredient_id, alias_name, language, source
                    )
                    VALUES (
                        :ingredient_id, :alias_name, :language, :source
                    )
                    ON CONFLICT (LOWER(alias_name)) DO UPDATE SET
                        ingredient_id = EXCLUDED.ingredient_id,
                        language = COALESCE(
                            EXCLUDED.language,
                            ingredient_aliases.language
                        ),
                        source = EXCLUDED.source
                    """
                ),
                {
                    "ingredient_id": ingredient_id,
                    "alias_name": alias_name,
                    "language": language,
                    "source": source,
                },
            )

            resolved = conn.execute(
                text(
                    """
                    SELECT
                        ia.alias_name,
                        mi.ingredient_id,
                        mi.canonical_name
                    FROM ingredient_aliases ia
                    JOIN master_ingredients mi
                        ON mi.ingredient_id = ia.ingredient_id
                    WHERE LOWER(ia.alias_name) = LOWER(:alias_name)
                    """
                ),
                {"alias_name": alias_name},
            ).mappings().first()

        return {
            "ingredient_id": resolved["ingredient_id"],
            "canonical_name": resolved["canonical_name"],
            "alias_name": resolved["alias_name"],
            "language": language,
            "source": source,
            "corrected_by": corrected_by,
            "next_run_resolution_tier": "exact_alias",
            "next_run_resolution_method": "database_alias",
        }

    def resolve_alias(self, alias_name):
        normalized_alias = normalize_ingredient_name(alias_name)

        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        ia.alias_name,
                        mi.ingredient_id,
                        mi.canonical_name
                    FROM ingredient_aliases ia
                    JOIN master_ingredients mi
                        ON mi.ingredient_id = ia.ingredient_id
                    WHERE LOWER(ia.alias_name) = LOWER(:alias_name)
                    """
                ),
                {"alias_name": normalized_alias},
            ).mappings().first()

        if row is None:
            return None

        return {
            "ingredient_id": row["ingredient_id"],
            "canonical_name": row["canonical_name"],
            "alias_name": row["alias_name"],
            "resolution_tier": "exact_alias",
            "resolution_method": "database_alias",
        }
