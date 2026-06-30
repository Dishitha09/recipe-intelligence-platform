import os
from threading import Lock

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


load_dotenv()

_engine = None
_session_local = None
_lock = Lock()


def _database_url():
    return os.getenv("DATABASE_URL")


def get_engine():
    global _engine

    if _engine is not None:
        return _engine

    with _lock:
        if _engine is None:
            database_url = _database_url()

            if not database_url:
                raise RuntimeError(
                    "DATABASE_URL is not configured. Set it before using "
                    "database-backed services."
                )

            _engine = create_engine(
                database_url,
                echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
            )

    return _engine


def get_session_local():
    global _session_local

    if _session_local is None:
        _session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )

    return _session_local


class LazyEngine:
    def __getattr__(self, name):
        return getattr(get_engine(), name)

    def begin(self, *args, **kwargs):
        return get_engine().begin(*args, **kwargs)

    def connect(self, *args, **kwargs):
        return get_engine().connect(*args, **kwargs)


engine = LazyEngine()


class LazySessionLocal:
    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)


SessionLocal = LazySessionLocal()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
