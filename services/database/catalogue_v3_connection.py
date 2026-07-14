import os
from contextlib import contextmanager
from threading import Lock

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


load_dotenv()

_engine = None
_session_factory = None
_lock = Lock()


def _catalogue_v3_database_url():
    return os.getenv("CATALOGUE_V3_DATABASE_URL")


def get_catalogue_v3_engine():
    global _engine

    if _engine is not None:
        return _engine

    with _lock:
        if _engine is None:
            database_url = _catalogue_v3_database_url()

            if not database_url:
                raise RuntimeError(
                    "CATALOGUE_V3_DATABASE_URL is not configured. Set it "
                    "before using Recipe Catalogue V3 database services."
                )

            _engine = create_engine(
                database_url,
                echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
            )

    return _engine


def get_catalogue_v3_session_factory():
    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_catalogue_v3_engine(),
        )

    return _session_factory


@contextmanager
def catalogue_v3_session_scope():
    session = get_catalogue_v3_session_factory()()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
