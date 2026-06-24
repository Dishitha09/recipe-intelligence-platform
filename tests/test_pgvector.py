import pytest
from sqlalchemy import text

from services.database.connection import engine


def require_pgvector():
    try:
        with engine.connect() as conn:
            version = conn.execute(
                text(
                    """
                    SELECT extversion
                    FROM pg_extension
                    WHERE extname='vector'
                    """
                )
            ).scalar()
    except Exception as exc:
        pytest.skip(f"database unavailable: {exc}")

    if version is None:
        pytest.skip("pgvector extension is not installed")

    return version


def test_pgvector_extension_is_enabled():
    version = require_pgvector()

    assert version


def test_pgvector_cosine_distance_works():
    require_pgvector()

    with engine.connect() as conn:
        distance = conn.execute(
            text(
                """
                SELECT
                    CAST('[1,0,0]' AS vector)
                    <=> CAST('[1,0,0]' AS vector)
                """
            )
        ).scalar()

    assert distance == 0
