import importlib

import pytest


def test_database_connection_import_does_not_require_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")

    connection = importlib.reload(
        importlib.import_module("services.database.connection")
    )

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        connection.get_engine()


def test_api_import_does_not_initialize_rag(monkeypatch):
    module = importlib.import_module("services.api.main")

    assert module.home() == {
        "message": "Recipe Intelligence API Running"
    }
    assert module.rag is None
