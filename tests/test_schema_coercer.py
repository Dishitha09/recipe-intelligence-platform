from services.ingestion.csv_adapter import CSVAdapter
from services.ingestion.raw_record import RawRecord
from services.ingestion.text_adapter import TextAdapter
from services.preprocessing.field_mapping import FieldMappingRegistry
from services.preprocessing.schema_coercer import CANONICAL_FIELDS, SchemaCoercer


MAPPING_FILE = "configs/source_field_mappings.json"


def test_schema_coercer_outputs_all_canonical_fields_with_unmapped_metadata():
    raw_record = CSVAdapter(
        "sample_recipes.csv",
        source_id="csv.default",
    ).extract()[0]
    coercer = SchemaCoercer.from_mapping_file(MAPPING_FILE)

    recipe_data = coercer.coerce_to_dict(raw_record)

    assert recipe_data["title"] == "Masala Dosa"
    assert recipe_data["description"] is None
    assert recipe_data["language"] == "english"
    assert recipe_data["source_type"] == "csv"
    assert recipe_data["source_url"] is None
    assert recipe_data["ingredients"][0]["ingredient_name"] == "Rice"
    assert recipe_data["steps"] == []
    assert recipe_data["metadata"]["source_id"] == "csv.default"
    assert set(recipe_data.keys()) == set(CANONICAL_FIELDS)
    assert recipe_data["servings"] is None
    assert recipe_data["tags"] == []
    assert recipe_data["nutrition_info"] == {}


def test_field_mapping_config_covers_all_source_types():
    registry = FieldMappingRegistry.from_json(MAPPING_FILE)
    source_types = {
        mapping.source_type
        for mapping in registry.mappings.values()
    }

    assert {
        "audio",
        "csv",
        "dataset",
        "image",
        "pdf",
        "text",
        "web",
        "youtube",
    }.issubset(source_types)


def test_schema_coercer_preserves_unmapped_fields_without_data_loss():
    raw_record = RawRecord(
        source_id="csv.default",
        source_type="csv",
        _raw_content={
            "title": "Idli",
            "ingredient": "Rice",
            "legacy_score": 42,
        },
    )
    coercer = SchemaCoercer.from_mapping_file(MAPPING_FILE)

    recipe_data = coercer.coerce_to_dict(raw_record)

    assert recipe_data["metadata"]["unmapped"] == {
        "legacy_score": 42,
    }


def test_schema_coercer_promotes_image_to_metadata_images():
    raw_record = RawRecord(
        source_id="csv.default",
        source_type="csv",
        _raw_content={
            "title": "Tomato Rice",
            "ingredient": "1 cup rice",
            "image": "https://example.com/tomato-rice.jpg",
        },
    )
    coercer = SchemaCoercer.from_mapping_file(MAPPING_FILE)

    recipe_data = coercer.coerce_to_dict(raw_record)

    assert recipe_data["metadata"]["images"] == [
        "https://example.com/tomato-rice.jpg"
    ]


def test_schema_coercer_is_idempotent_for_same_raw_record():
    raw_record = CSVAdapter(
        "sample_recipes.csv",
        source_id="csv.default",
    ).extract()[0]
    coercer = SchemaCoercer.from_mapping_file(MAPPING_FILE)

    outputs = [
        coercer.to_canonical_json(raw_record)
        for _ in range(3)
    ]

    assert outputs[0] == outputs[1] == outputs[2]


def test_schema_coercer_parses_text_recipe_sections():
    raw_record = TextAdapter(
        "sample_recipe.txt",
        source_id="text.default",
    ).extract()[0]
    coercer = SchemaCoercer.from_mapping_file(MAPPING_FILE)

    recipe_data = coercer.coerce_to_dict(raw_record)

    assert recipe_data["source_type"] == "text"
    assert recipe_data["ingredients"][0]["ingredient_name"] == "Rice"
    assert recipe_data["ingredients"][0]["quantity"] == 2
    assert recipe_data["steps"][0]["instruction"] == "Soak rice overnight."


def test_schema_coercer_preserves_commas_inside_step_text():
    raw_record = RawRecord(
        source_id="scrapy_indianhealthyrecipes",
        source_type="web",
        _raw_content={
            "title": "Coconut Oats",
            "ingredients": "1 cup oats | 1 tsp mustard",
            "steps": (
                "Heat oil. | Add mustard, cumin, urad dal and peanuts. | "
                "Fry until golden."
            ),
            "source_url": "https://example.com/coconut-oats",
        },
    )
    coercer = SchemaCoercer.from_mapping_file(MAPPING_FILE)

    recipe_data = coercer.coerce_to_dict(raw_record)

    assert [
        step["instruction"]
        for step in recipe_data["steps"]
    ] == [
        "Heat oil.",
        "Add mustard, cumin, urad dal and peanuts.",
        "Fry until golden.",
    ]


def test_schema_coercer_routes_invalid_records_to_dead_letter():
    raw_record = RawRecord(
        source_id="csv.default",
        source_type="csv",
        _raw_content={
            "title": None,
            "ingredient": "Rice",
        },
    )
    coercer = SchemaCoercer.from_mapping_file(MAPPING_FILE)

    result = coercer.coerce(raw_record)

    assert result.status == "dead_letter"
    assert result.dead_letter["record_id"] == raw_record.record_id
    assert result.dead_letter["record_snapshot"]["record_id"] == raw_record.record_id
