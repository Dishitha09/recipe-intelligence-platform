from services.database.catalogue_v3_curator_repository import (
    CatalogueV3CuratorRepository,
)


def test_catalogue_v3_curator_normalizes_alias_writeback(monkeypatch):
    calls = []

    class FakeResult:
        def __init__(self, scalar_value=None, mapping_value=None):
            self.scalar_value = scalar_value
            self.mapping_value = mapping_value

        def scalar(self):
            return self.scalar_value

        def mappings(self):
            return self

        def first(self):
            return self.mapping_value

    class FakeConnection:
        def execute(self, statement, params=None):
            calls.append(
                {
                    "sql": str(statement),
                    "params": params or {},
                }
            )

            if "RETURNING ingredient_id" in str(statement):
                return FakeResult(scalar_value=42)

            if "SELECT" in str(statement):
                return FakeResult(
                    mapping_value={
                        "ingredient_id": 42,
                        "canonical_name": "dry_mango_powder",
                        "alias_name": "amchoor",
                    }
                )

            return FakeResult()

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    repo = CatalogueV3CuratorRepository(engine=FakeEngine())

    result = repo.write_back_alias(
        canonical_name="Dry Mango Powder",
        alias_name="Amchoor",
        language="hi",
        corrected_by="reviewer@example.com",
    )

    assert result["ingredient_id"] == 42
    assert result["canonical_name"] == "dry_mango_powder"
    assert result["alias_name"] == "amchoor"
    assert result["next_run_resolution_tier"] == "exact_alias"
    assert calls[0]["params"]["canonical_name"] == "dry_mango_powder"
    assert calls[1]["params"]["alias_name"] == "amchoor"
