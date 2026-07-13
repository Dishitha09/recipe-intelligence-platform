import json
import re

from sqlalchemy import text

from services.database.connection import engine


INDIAN_CUISINE_TERMS = {
    "andhra",
    "assamese",
    "awadhi",
    "bengal",
    "bengali",
    "bihari",
    "chettinad",
    "coorg",
    "goa",
    "goan",
    "gujarat",
    "gujarati",
    "hyderabad",
    "hyderabadi",
    "india",
    "indian",
    "indo chinese",
    "karnataka",
    "kashmir",
    "kashmiri",
    "kerala",
    "konkan",
    "mangalorean",
    "maharashtra",
    "maharashtrian",
    "malabar",
    "mughlai",
    "north east india",
    "north indian",
    "odia",
    "odisha",
    "oriya",
    "parsi",
    "punjab",
    "punjabi",
    "rajasthan",
    "rajasthani",
    "sindhi",
    "south indian",
    "tamil",
    "telangana",
    "udupi",
}

INDIC_RE = re.compile(r"[\u0900-\u097F]")
HINDI_MOJIBAKE_RE = re.compile(r"à[¤¥]|à¤|à¥")
HINDI_MARKER_RE = re.compile(r"(recipe\s+in\s+hindi|in-hindi|/hindi)", re.I)
COMMENT_CONTAMINATION_RE = re.compile(
    r"\b(reply|suguna\s+vinodh|thanks\s+for\s+the\s+yummy\s+recipes)\b",
    re.I,
)
GENERATED_SIDECAR_RE = re.compile(
    r"file://data/datasets/multisource/batch/",
    re.I,
)
OFF_SCOPE_TITLE_RE = re.compile(
    r"\b(penne\s+rigate|bolognese|ricotta\s+tart|burrito|lasagna)\b",
    re.I,
)
GENERATED_TITLES = {
    "andhra gongura pappu",
    "assam fish tenga",
    "bengali lau chingri",
    "bihari sattu paratha",
    "goan prawn curry",
    "gujarati undhiyu",
    "himachali chana madra",
    "karnataka bisi bele bath",
    "kerala fish molee",
    "maharashtrian misal",
    "punjabi egg curry",
    "rajasthani laapsi",
    "tamil nadu chettinad chicken",
    "telangana sakinalu",
    "uttar pradesh vegetable tehri",
}


def is_indian_cuisine(cuisine):
    cuisine = str(cuisine or "").strip().casefold().replace("\ufeff", "")

    if not cuisine:
        return True

    return any(term in cuisine for term in INDIAN_CUISINE_TERMS)


def quality_reason(row):
    title = str(row["title"] or "")
    cuisine = str(row["cuisine"] or "")
    source_url = str(row["source_url"] or "")
    text_blob = " ".join(
        str(row[key] or "")
        for key in [
            "title",
            "description",
            "source_url",
            "ingredient_text",
            "steps_text",
        ]
    )

    if HINDI_MARKER_RE.search(f"{title} {source_url}"):
        return "non_english_hindi_marker"

    if GENERATED_SIDECAR_RE.search(source_url):
        return "generated_sidecar_artifact"

    if title.strip().casefold() in GENERATED_TITLES:
        return "generated_sidecar_artifact"

    if OFF_SCOPE_TITLE_RE.search(title):
        return "non_indian_title"

    if HINDI_MOJIBAKE_RE.search(text_blob):
        return "non_english_hindi_mojibake"

    if INDIC_RE.search(text_blob):
        return "non_english_indic_script"

    if COMMENT_CONTAMINATION_RE.search(str(row["steps_text"] or "")):
        return "comment_contaminated_steps"

    if cuisine and not is_indian_cuisine(cuisine):
        return "non_indian_cuisine"

    return None


def candidate_rows():
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT
                    r.recipe_id,
                    r.title,
                    r.description,
                    r.cuisine,
                    r.source_url,
                    r.source_type,
                    COALESCE(
                        STRING_AGG(DISTINCT ri.ingredient_name, ' '),
                        ''
                    ) AS ingredient_text,
                    COALESCE(
                        STRING_AGG(rs.instruction, ' ' ORDER BY rs.step_number),
                        ''
                    ) AS steps_text
                FROM recipes r
                LEFT JOIN recipe_ingredients ri
                    ON ri.recipe_id = r.recipe_id
                LEFT JOIN recipe_steps rs
                    ON rs.recipe_id = r.recipe_id
                GROUP BY
                    r.recipe_id,
                    r.title,
                    r.description,
                    r.cuisine,
                    r.source_url,
                    r.source_type
                """
            )
        ).mappings().all()


def delete_recipes(recipe_ids):
    if not recipe_ids:
        return {}

    params = {"recipe_ids": tuple(recipe_ids)}
    deleted = {}

    with engine.begin() as conn:
        for table in [
            "recipe_embeddings",
            "recipe_source_tracking",
            "recipe_sources",
            "recipe_steps",
            "recipe_ingredients",
            "validation_reports",
            "recipe_reviews",
            "recipe_ratings_summary",
            "trending_recipes",
            "pipeline_audit_log",
        ]:
            try:
                deleted[table] = conn.execute(
                    text(f"DELETE FROM {table} WHERE recipe_id IN :recipe_ids"),
                    params,
                ).rowcount
            except Exception as exc:
                deleted[table] = f"skipped: {exc.__class__.__name__}"

        deleted["recipes"] = conn.execute(
            text("DELETE FROM recipes WHERE recipe_id IN :recipe_ids"),
            params,
        ).rowcount

    return deleted


def cleanup():
    reasons = {}
    examples = {}
    recipe_ids = []

    for row in candidate_rows():
        reason = quality_reason(row)

        if not reason:
            continue

        recipe_ids.append(row["recipe_id"])
        reasons[reason] = reasons.get(reason, 0) + 1
        examples.setdefault(
            reason,
            {
                "recipe_id": row["recipe_id"],
                "title": row["title"],
                "cuisine": row["cuisine"],
                "source_url": row["source_url"],
            },
        )

    deleted = delete_recipes(recipe_ids)

    with engine.connect() as conn:
        source_counts = conn.execute(
            text(
                """
                SELECT source_type, count(*)
                FROM recipes
                GROUP BY source_type
                ORDER BY source_type
                """
            )
        ).fetchall()
        remaining = {
            "total": conn.execute(text("SELECT count(*) FROM recipes")).scalar(),
            "hindi_marker": conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM recipes
                    WHERE lower(coalesce(source_url, '')) LIKE '%in-hindi%'
                       OR lower(title) LIKE '%hindi%'
                    """
                )
            ).scalar(),
            "hindi_mojibake_steps": conn.execute(
                text(
                    """
                    SELECT count(DISTINCT recipe_id)
                    FROM recipe_steps
                    WHERE instruction LIKE '%à¤%'
                       OR instruction LIKE '%à¥%'
                    """
                )
            ).scalar(),
            "indic_steps": conn.execute(
                text(
                    """
                    SELECT count(DISTINCT recipe_id)
                    FROM recipe_steps
                    WHERE instruction ~ '[\\u0900-\\u097F]'
                    """
                )
            ).scalar(),
        }

    return {
        "candidates": len(recipe_ids),
        "deleted": deleted,
        "examples": examples,
        "reasons": reasons,
        "remaining": remaining,
        "source_counts": [(row[0], row[1]) for row in source_counts],
    }


def main():
    print(json.dumps(cleanup(), indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
