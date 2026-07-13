from services.preprocessing.schema_registry import SchemaRegistry


def test_schema_registry_validates_recipe_v1_contract():
    registry = SchemaRegistry()
    payload = {
        "schema_version": "v1",
        "title": "Masala Dosa",
        "ingredients": [{"ingredient_name": "rice"}],
        "steps": [{"step_number": 1, "instruction": "Cook on a tawa."}],
        "source_type": "web",
    }

    result = registry.validate(payload)

    assert result["valid"] is True
    assert result["schema_version"] == "v1"


def test_schema_registry_reports_missing_required_fields():
    result = SchemaRegistry().validate({"schema_version": "v1"})

    assert result["valid"] is False
    assert "title is required" in result["errors"]
