from types import SimpleNamespace

from services.acquisition.scrape_catalogue_v3_web import (
    clean,
    json_object,
    record_to_catalogue_v3_payload,
    validation_skip_reason,
)


def test_record_to_catalogue_v3_payload_uses_only_scraped_fields():
    record = SimpleNamespace(
        raw_content={
            "title": "Real Scraped Dosa",
            "description": "Source description",
            "source_url": "https://example.com/dosa",
            "ingredients": ["1 cup rice", "1/4 cup urad dal"],
            "steps": ["Soak rice.", "Grind batter."],
            "image": "https://example.com/dosa.jpg",
            "servings": 4,
            "prep_time_min": 20,
            "cook_time_min": 10,
            "course": ["Breakfast"],
            "cuisines": ["South Indian"],
            "tags": ["dosa", "breakfast"],
        }
    )
    source = SimpleNamespace(
        source_id="example_web",
        location="https://example.com/",
        config={"source_group": "structured_html", "parser": "schema_org"},
    )

    payload = record_to_catalogue_v3_payload(record, source)

    assert payload["name"] == "Real Scraped Dosa"
    assert payload["servings"] == 4
    assert payload["ingredients_json"] == [
        {"raw_text": "1 cup rice", "source_position": 1},
        {"raw_text": "1/4 cup urad dal", "source_position": 2},
    ]
    assert payload["cook_steps"] == [
        {"step_number": 1, "instruction": "Soak rice."},
        {"step_number": 2, "instruction": "Grind batter."},
    ]
    assert payload["metadata"]["servings_source"] == "source_recipe_yield"
    assert payload["metadata"]["content_hash"]


def test_validation_skip_reason_requires_source_servings():
    payload = {
        "name": "Recipe",
        "servings": None,
        "ingredients_json": [{"raw_text": "rice"}],
        "cook_steps": [{"instruction": "Cook."}],
        "metadata": {"source_url": "https://example.com/recipe"},
    }

    assert validation_skip_reason(payload) == "missing_source_servings"


def test_json_object_handles_nested_stringified_dict():
    value = "\"{'calories': '250 kcal', 'proteinContent': '9 g'}\""

    assert json_object(value) == {
        "calories": "250 kcal",
        "proteinContent": "9 g",
    }


def test_clean_repairs_common_fraction_mojibake():
    assert clean("1\u00c2\u00bd cups rice") == "1 1/2 cups rice"
