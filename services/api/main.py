import hashlib
import hmac
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.connection import engine
from services.observability.prometheus import build_prometheus_metrics


app = FastAPI(
    title="Recipe Intelligence API",
    version="1.0.0",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = None


def require_admin_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    expected_token = os.getenv("API_ADMIN_TOKEN")

    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="Admin API token is not configured.",
        )

    if not x_admin_token or not hmac.compare_digest(
        x_admin_token,
        expected_token,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing admin API token.",
        )

    return True


def get_rag():
    global rag

    if rag is None:
        from services.rag.recipe_rag import RecipeRAG

        rag = RecipeRAG()

    return rag


class QueryRequest(BaseModel):
    question: str


class AdvancedSearchRequest(BaseModel):
    query: str | None = None
    region: str | None = None
    state: str | None = None
    source_type: str | None = None
    language: str | None = None
    min_rating: float | None = Field(default=None, ge=0, le=5)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)


class ReviewCreateRequest(BaseModel):
    user_name: str = Field(default="anonymous", min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=2000)
    source: str = Field(default="web", max_length=100)


class AliasWriteBackRequest(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=255)
    alias_name: str = Field(min_length=1, max_length=255)
    language: str | None = Field(default=None, max_length=50)
    source: str = Field(default="curator", max_length=100)


def _jsonable(value: Any):
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def _row_to_dict(row):
    return {
        key: _jsonable(value)
        for key, value in row._mapping.items()
    }


def _rows_to_dicts(rows):
    return [_row_to_dict(row) for row in rows]


def _normalize_page(page: int, limit: int):
    return max(page, 1), min(max(limit, 1), 100)


def _recipe_filters(
    search: str | None = None,
    region: str | None = None,
    state: str | None = None,
    source_type: str | None = None,
    language: str | None = None,
    min_rating: float | None = None,
):
    clauses = []
    params: dict[str, Any] = {}

    if search:
        clauses.append(
            """
            (
                r.title ILIKE :search
                OR COALESCE(r.description, '') ILIKE :search
                OR COALESCE(r.instructions, '') ILIKE :search
            )
            """
        )
        params["search"] = f"%{search.strip()}%"

    if region:
        clauses.append("LOWER(COALESCE(r.region, '')) = LOWER(:region)")
        params["region"] = region.strip()

    if state:
        clauses.append("LOWER(COALESCE(r.state, '')) = LOWER(:state)")
        params["state"] = state.strip()

    if source_type:
        clauses.append("LOWER(COALESCE(r.source_type, '')) = LOWER(:source_type)")
        params["source_type"] = source_type.strip()

    if language:
        clauses.append("LOWER(COALESCE(r.language, '')) = LOWER(:language)")
        params["language"] = language.strip()

    if min_rating is not None:
        clauses.append("COALESCE(s.average_rating, 0) >= :min_rating")
        params["min_rating"] = min_rating

    return " AND ".join(clauses) if clauses else "TRUE", params


def list_recipes_from_db(
    search: str | None = None,
    region: str | None = None,
    state: str | None = None,
    source_type: str | None = None,
    language: str | None = None,
    min_rating: float | None = None,
    page: int = 1,
    limit: int = 25,
):
    page, limit = _normalize_page(page, limit)
    where_sql, params = _recipe_filters(
        search=search,
        region=region,
        state=state,
        source_type=source_type,
        language=language,
        min_rating=min_rating,
    )
    query_params = {
        **params,
        "limit": limit,
        "offset": (page - 1) * limit,
    }

    with engine.connect() as conn:
        total = conn.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM recipe_with_instructions r
                LEFT JOIN recipe_ratings_summary s
                    ON s.recipe_id = r.recipe_id
                WHERE {where_sql}
                """
            ),
            params,
        ).scalar()

        rows = conn.execute(
            text(
                f"""
                SELECT
                    r.recipe_id,
                    r.title,
                    r.description,
                    r.cuisine,
                    r.state,
                    r.region,
                    r.source_type,
                    r.source_url,
                    r.language,
                    r.step_count,
                    LEFT(COALESCE(r.instructions, ''), 700)
                        AS instructions_preview,
                    COALESCE(ingredient_counts.ingredient_count, 0)
                        AS ingredient_count,
                    COALESCE(s.review_count, 0) AS review_count,
                    COALESCE(s.average_rating, 0) AS average_rating,
                    r.created_at,
                    r.updated_at
                FROM recipe_with_instructions r
                LEFT JOIN recipe_ratings_summary s
                    ON s.recipe_id = r.recipe_id
                LEFT JOIN (
                    SELECT recipe_id, COUNT(*) AS ingredient_count
                    FROM recipe_ingredients
                    GROUP BY recipe_id
                ) ingredient_counts
                    ON ingredient_counts.recipe_id = r.recipe_id
                WHERE {where_sql}
                ORDER BY
                    r.updated_at DESC NULLS LAST,
                    r.recipe_id DESC
                LIMIT :limit
                OFFSET :offset
                """
            ),
            query_params,
        ).fetchall()

    return {
        "items": _rows_to_dicts(rows),
        "page": page,
        "limit": limit,
        "total": int(total or 0),
    }


def get_recipe_detail_from_db(recipe_id: int):
    with engine.connect() as conn:
        recipe_row = conn.execute(
            text(
                """
                SELECT
                    r.*,
                    COALESCE(s.review_count, 0) AS review_count,
                    COALESCE(s.average_rating, 0) AS average_rating,
                    COALESCE(s.five_star_count, 0) AS five_star_count,
                    COALESCE(s.four_star_count, 0) AS four_star_count,
                    COALESCE(s.three_star_count, 0) AS three_star_count,
                    COALESCE(s.two_star_count, 0) AS two_star_count,
                    COALESCE(s.one_star_count, 0) AS one_star_count
                FROM recipe_with_instructions r
                LEFT JOIN recipe_ratings_summary s
                    ON s.recipe_id = r.recipe_id
                WHERE r.recipe_id = :recipe_id
                """
            ),
            {"recipe_id": recipe_id},
        ).fetchone()

        if recipe_row is None:
            return None

        ingredient_rows = conn.execute(
            text(
                """
                SELECT
                    ri.recipe_ingredient_id,
                    ri.ingredient_id,
                    COALESCE(ri.canonical_name, mi.canonical_name)
                        AS canonical_name,
                    mi.category,
                    ri.quantity,
                    ri.unit,
                    ri.canonical_quantity,
                    ri.canonical_unit,
                    ri.preparation,
                    ri.resolution_method,
                    ri.resolution_tier,
                    ri.resolution_confidence,
                    ri.conversion_method,
                    ri.uom_confidence_score,
                    ri.enrichment_flags
                FROM recipe_ingredients ri
                LEFT JOIN master_ingredients mi
                    ON mi.ingredient_id = ri.ingredient_id
                WHERE ri.recipe_id = :recipe_id
                ORDER BY ri.recipe_ingredient_id
                """
            ),
            {"recipe_id": recipe_id},
        ).fetchall()

        step_rows = conn.execute(
            text(
                """
                SELECT step_number, instruction
                FROM recipe_steps
                WHERE recipe_id = :recipe_id
                ORDER BY step_number
                """
            ),
            {"recipe_id": recipe_id},
        ).fetchall()

        source_rows = conn.execute(
            text(
                """
                SELECT
                    run_id,
                    source_name,
                    source_type,
                    source_url,
                    ingested_at
                FROM recipe_source_tracking
                WHERE recipe_id = :recipe_id
                ORDER BY ingested_at DESC
                """
            ),
            {"recipe_id": recipe_id},
        ).fetchall()

    recipe = _row_to_dict(recipe_row)
    recipe["ingredients"] = _rows_to_dicts(ingredient_rows)
    recipe["steps"] = _rows_to_dicts(step_rows)
    recipe["source_transparency"] = {
        "source_type": recipe.get("source_type"),
        "source_url": recipe.get("source_url"),
        "tracking": _rows_to_dicts(source_rows),
    }
    return recipe


def get_regions_from_db():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    state,
                    region,
                    place_type,
                    recipe_count,
                    avg_state_confidence,
                    distinct_source_urls,
                    target_for_10000,
                    remaining_for_10000
                FROM recipe_state_target_coverage
                ORDER BY region, state
                """
            )
        ).fetchall()

    return {"items": _rows_to_dicts(rows)}


def get_rating_summary_from_db(recipe_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    recipe_id,
                    review_count,
                    average_rating,
                    five_star_count,
                    four_star_count,
                    three_star_count,
                    two_star_count,
                    one_star_count,
                    updated_at
                FROM recipe_ratings_summary
                WHERE recipe_id = :recipe_id
                """
            ),
            {"recipe_id": recipe_id},
        ).fetchone()

    if row is None:
        return {
            "recipe_id": recipe_id,
            "review_count": 0,
            "average_rating": 0,
            "five_star_count": 0,
            "four_star_count": 0,
            "three_star_count": 0,
            "two_star_count": 0,
            "one_star_count": 0,
            "updated_at": None,
        }

    return _row_to_dict(row)


def get_reviews_from_db(recipe_id: int):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    review_id,
                    recipe_id,
                    user_name,
                    rating,
                    review_text,
                    source,
                    created_at,
                    updated_at
                FROM recipe_reviews
                WHERE recipe_id = :recipe_id
                ORDER BY created_at DESC, review_id DESC
                """
            ),
            {"recipe_id": recipe_id},
        ).fetchall()

    return _rows_to_dicts(rows)


def create_review_in_db(recipe_id: int, payload: ReviewCreateRequest):
    user_name = payload.user_name.strip() or "anonymous"
    review_text = (payload.review_text or "").strip()
    review_hash = hashlib.sha256(
        f"{recipe_id}|{user_name.lower()}|{payload.rating}|{review_text}".encode(
            "utf-8"
        )
    ).hexdigest()

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM recipes WHERE recipe_id = :recipe_id"),
            {"recipe_id": recipe_id},
        ).scalar()

        if not exists:
            raise HTTPException(status_code=404, detail="Recipe not found")

        row = conn.execute(
            text(
                """
                INSERT INTO recipe_reviews
                    (
                        recipe_id,
                        user_name,
                        rating,
                        review_text,
                        source,
                        review_hash
                    )
                VALUES
                    (
                        :recipe_id,
                        :user_name,
                        :rating,
                        :review_text,
                        :source,
                        :review_hash
                    )
                ON CONFLICT (review_hash)
                DO UPDATE SET
                    user_name = EXCLUDED.user_name,
                    rating = EXCLUDED.rating,
                    review_text = EXCLUDED.review_text,
                    source = EXCLUDED.source,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING
                    review_id,
                    recipe_id,
                    user_name,
                    rating,
                    review_text,
                    source,
                    created_at,
                    updated_at
                """
            ),
            {
                "recipe_id": recipe_id,
                "user_name": user_name,
                "rating": payload.rating,
                "review_text": review_text,
                "source": payload.source.strip() or "web",
                "review_hash": review_hash,
            },
        ).fetchone()

    return _row_to_dict(row)


def get_trending_from_db(limit: int = 25):
    limit = min(max(limit, 1), 100)

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    r.recipe_id,
                    r.title,
                    r.state,
                    r.region,
                    r.source_type,
                    r.source_url,
                    r.step_count,
                    COALESCE(s.review_count, 0) AS review_count,
                    COALESCE(s.average_rating, 0) AS average_rating,
                    COALESCE(
                        t.trending_score,
                        (
                            COALESCE(s.average_rating, 0) * 10
                            + LEAST(COALESCE(s.review_count, 0), 50)
                            + CASE
                                WHEN r.created_at >= CURRENT_TIMESTAMP
                                     - INTERVAL '30 days'
                                THEN 5
                                ELSE 0
                              END
                        )
                    ) AS trending_score,
                    COALESCE(
                        t.reason,
                        'computed from rating, review volume, and recency'
                    ) AS reason
                FROM recipe_with_instructions r
                LEFT JOIN recipe_ratings_summary s
                    ON s.recipe_id = r.recipe_id
                LEFT JOIN trending_recipes t
                    ON t.recipe_id = r.recipe_id
                ORDER BY
                    trending_score DESC,
                    r.updated_at DESC NULLS LAST,
                    r.recipe_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).fetchall()

    return {"items": _rows_to_dicts(rows), "limit": limit}


@app.get("/")
def home():
    return {
        "message": "Recipe Intelligence API Running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "recipe-intelligence-api",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    checks = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["operational_db"] = "ok"
    except Exception:
        checks["operational_db"] = "failed"

    try:
        with get_catalogue_v3_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["catalogue_v3_db"] = "ok"
    except Exception:
        checks["catalogue_v3_db"] = "failed"

    if all(value == "ok" for value in checks.values()):
        return {
            "status": "ready",
            "checks": checks,
        }

    raise HTTPException(
        status_code=503,
        detail={
            "status": "not_ready",
            "checks": checks,
        },
    )


@app.get("/metrics")
def metrics():
    return Response(
        content=build_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.post(
    "/ingredients/aliases",
    dependencies=[Depends(require_admin_token)],
)
def write_back_alias(request: AliasWriteBackRequest):
    from services.database.ingredient_repository import IngredientRepository

    return IngredientRepository().write_back_alias(
        canonical_name=request.canonical_name,
        alias_name=request.alias_name,
        language=request.language,
        source=request.source,
    )


@app.post(
    "/catalogue-v3/ingredients/aliases",
    dependencies=[Depends(require_admin_token)],
)
def write_back_catalogue_v3_alias(request: AliasWriteBackRequest):
    from services.database.catalogue_v3_curator_repository import (
        CatalogueV3CuratorRepository,
    )

    return CatalogueV3CuratorRepository().write_back_alias(
        canonical_name=request.canonical_name,
        alias_name=request.alias_name,
        language=request.language,
        source=request.source,
    )


@app.get("/recipes")
def list_recipes(
    q: str | None = Query(default=None),
    region: str | None = Query(default=None),
    state: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
):
    return list_recipes_from_db(
        search=q,
        region=region,
        state=state,
        source_type=source_type,
        language=language,
        page=page,
        limit=limit,
    )


@app.post("/search")
def search_recipes(request: AdvancedSearchRequest):
    return list_recipes_from_db(
        search=request.query,
        region=request.region,
        state=request.state,
        source_type=request.source_type,
        language=request.language,
        min_rating=request.min_rating,
        page=request.page,
        limit=request.limit,
    )


@app.get("/regions")
def regions():
    return get_regions_from_db()


@app.get("/recipes/{recipe_id}/reviews")
def recipe_reviews(recipe_id: int):
    return {
        "summary": get_rating_summary_from_db(recipe_id),
        "items": get_reviews_from_db(recipe_id),
    }


@app.post(
    "/recipes/{recipe_id}/reviews",
    dependencies=[Depends(require_admin_token)],
)
def add_recipe_review(recipe_id: int, request: ReviewCreateRequest):
    review = create_review_in_db(recipe_id, request)

    return {
        "review": review,
        "summary": get_rating_summary_from_db(recipe_id),
    }


@app.get("/recipes/{recipe_id}")
def recipe_detail(recipe_id: int):
    recipe = get_recipe_detail_from_db(recipe_id)

    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return recipe


@app.get("/trending")
def trending(limit: int = Query(default=25, ge=1, le=100)):
    return get_trending_from_db(limit=limit)


@app.post("/ask", dependencies=[Depends(require_admin_token)])
def ask_recipe(request: QueryRequest):
    answer = get_rag().answer(
        request.question
    )

    return {
        "question": request.question,
        "answer": answer
    }
