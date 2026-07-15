from services.enrichment.catalogue_v3_enricher import CatalogueV3Enricher


def test_catalogue_v3_enricher_structures_ingredients_and_tags():
    row = {
        "name": "Egg Pulao",
        "description": "One-pot rice with boiled eggs",
        "ingredients_json": [
            {"raw_text": "2 cups basmati rice"},
            {"raw_text": "4 eggs boiled"},
            {"raw_text": "1 tbsp ghee"},
        ],
        "cook_steps": [
            {"instruction": "Saute spices."},
            {"instruction": "Cook rice."},
        ],
        "tags": ["pulao"],
        "course": ["main"],
        "cuisines": ["Andhra", "South Indian"],
        "meal_types": ["lunch", "dinner"],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {"source_url": "https://example.com/egg-pulao"},
        "servings": 4,
        "prep_time_min": 20,
        "cook_time_min": 30,
        "total_time_min": 50,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    result = CatalogueV3Enricher().enrich_row(row)
    updates = result.updates

    assert updates["ingredients_json"][0]["name"] == "basmati rice"
    assert updates["ingredients_json"][0]["quantity"] == 2
    assert updates["ingredients_json"][0]["unit"] == "cups"
    assert updates["ingredients_json"][0]["canonical_unit"] == "cup"
    assert updates["ingredients_json"][0]["canonical_quantity"] == 2
    assert updates["ingredients_json"][0]["normalized_text"] == "2 cups basmati rice"
    assert updates["ingredients_json"][0]["conversion_method"] == "volume_passthrough_without_density"
    assert updates["diet"] == "egg"
    assert "EGG" in updates["diet_tags"]
    assert "HIGH_PROTEIN" in updates["health_tags"]
    assert updates["dish_family"] == "pulao"
    assert updates["meal_role"] == "complete_meal"
    assert updates["difficulty_level"] == "MEDIUM"
    assert result.metadata_patch["catalogue_v3_enrichment"]["generated_text"] is False


def test_catalogue_v3_enricher_detects_non_veg_and_premium():
    row = {
        "name": "Mutton Biryani",
        "description": "Hyderabadi lamb rice",
        "ingredients_json": [{"raw_text": "1 kg mutton"}, {"raw_text": "saffron"}],
        "cook_steps": [{"instruction": "Cook slowly."}] * 10,
        "tags": [],
        "course": ["main"],
        "cuisines": ["Hyderabadi"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 4,
        "prep_time_min": 30,
        "cook_time_min": 120,
        "total_time_min": 150,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    updates = CatalogueV3Enricher().enrich_row(row).updates

    assert updates["diet"] == "non_vegetarian"
    assert "NON_VEGETARIAN" in updates["diet_tags"]
    assert updates["dish_family"] == "biryani"
    assert updates["cost_tier"] == "PREMIUM"
    assert "MEAL_PREP" in updates["efficiency_tags"]


def test_catalogue_v3_enricher_repairs_mojibake_and_normalizes_uom():
    row = {
        "name": "Coconut Oats",
        "description": "Quick oats",
        "ingredients_json": [{"raw_text": "1\u00c2\u00bd cup rolled oats"}],
        "cook_steps": [{"instruction": "Cook."}],
        "tags": [],
        "course": ["breakfast"],
        "cuisines": ["Indian"],
        "meal_types": ["breakfast"],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 10,
        "total_time_min": 15,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    ingredient = CatalogueV3Enricher().enrich_row(row).updates["ingredients_json"][0]

    assert ingredient["raw_text"] == "1 1/2 cup rolled oats"
    assert ingredient["quantity"] == 1.5
    assert ingredient["unit"] == "cup"
    assert ingredient["canonical_unit"] == "cup"
    assert ingredient["normalized_text"] == "1.5 cup rolled oats"
