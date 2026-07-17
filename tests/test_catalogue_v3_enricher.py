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
    assert updates["ingredients_json"][0]["canonical_unit"] == "g"
    assert updates["ingredients_json"][0]["canonical_quantity"] == 400
    assert updates["ingredients_json"][0]["normalized_text"] == "400 g basmati rice"
    assert updates["ingredients_json"][0]["conversion_method"] == "density_lookup"
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
    assert ingredient["canonical_unit"] == "g"
    assert ingredient["canonical_quantity"] == 120
    assert ingredient["normalized_text"] == "120 g rolled oats"


def test_catalogue_v3_enricher_reparses_existing_string_quantity_as_number():
    row = {
        "name": "Dal",
        "description": "Simple dal",
        "ingredients_json": [
            {
                "raw_text": "1/2 teaspoon turmeric powder",
                "name": "turmeric powder",
                "quantity": "1/2",
                "unit": "teaspoon",
            },
            {"raw_text": "1/3 cup red lentils"},
        ],
        "cook_steps": [{"instruction": "Cook."}],
        "tags": [],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 20,
        "total_time_min": 25,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    ingredients = CatalogueV3Enricher().enrich_row(row).updates["ingredients_json"]

    assert ingredients[0]["quantity"] == 0.5
    assert ingredients[0]["canonical_unit"] == "ml"
    assert ingredients[0]["canonical_quantity"] == 2.5
    assert ingredients[0]["normalized_text"] == "2.5 ml turmeric powder"
    assert ingredients[1]["quantity"] == 0.33
    assert ingredients[1]["canonical_unit"] == "g"
    assert ingredients[1]["canonical_quantity"] == 63.33
    assert ingredients[1]["normalized_text"] == "63.33 g red lentils"


def test_catalogue_v3_enricher_repairs_unit_prefixed_legacy_names():
    row = {
        "name": "Mushroom Curry",
        "description": "Mushrooms in masala",
        "ingredients_json": [
            {
                "raw_text": "6 to 8 oz sliced white mushrooms",
                "name": "oz sliced white mushrooms",
                "quantity": 7,
                "unit": "oz",
            }
        ],
        "cook_steps": [{"instruction": "Cook."}],
        "tags": [],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 20,
        "total_time_min": 25,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    ingredient = CatalogueV3Enricher().enrich_row(row).updates["ingredients_json"][0]

    assert ingredient["name"] == "white mushrooms"
    assert ingredient["quantity"] == 7
    assert ingredient["canonical_unit"] == "g"
    assert ingredient["canonical_quantity"] == 198.45
    assert ingredient["normalized_text"] == "198.45 g white mushrooms"


def test_catalogue_v3_enricher_repairs_quantity_prefixed_legacy_names():
    row = {
        "name": "Besan Curry",
        "description": "Gram flour curry",
        "ingredients_json": [
            {
                "raw_text": "1/2 cup Gram flour (besan)",
                "name": "1/2 cup Gram flour (besan)",
                "quantity": 0.5,
                "unit": "cup",
            }
        ],
        "cook_steps": [{"instruction": "Cook."}],
        "tags": [],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 20,
        "total_time_min": 25,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    ingredient = CatalogueV3Enricher().enrich_row(row).updates["ingredients_json"][0]

    assert ingredient["name"] == "Gram flour"
    assert ingredient["quantity"] == 0.5
    assert ingredient["canonical_unit"] == "g"
    assert ingredient["canonical_quantity"] == 46
    assert ingredient["normalized_text"] == "46 g Gram flour"


def test_catalogue_v3_enricher_prefers_embedded_metric_measure():
    row = {
        "name": "Cake",
        "description": "Cake batter",
        "ingredients_json": [
            {
                "raw_text": "1 cup 180gm maida / plain flour / refined flour",
                "name": "180gm maida plain flour refined flour",
                "quantity": 1,
                "unit": "cup",
            }
        ],
        "cook_steps": [{"instruction": "Mix."}],
        "tags": [],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 20,
        "total_time_min": 25,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    ingredient = CatalogueV3Enricher().enrich_row(row).updates["ingredients_json"][0]

    assert ingredient["name"] == "maida plain flour refined flour"
    assert ingredient["quantity"] == 180
    assert ingredient["unit"] == "gm"
    assert ingredient["canonical_unit"] == "g"
    assert ingredient["canonical_quantity"] == 180
    assert ingredient["normalized_text"] == "180 g maida plain flour refined flour"


def test_catalogue_v3_enricher_strips_compound_leading_measure_from_name():
    row = {
        "name": "Roomali Roti",
        "description": "Soft roti",
        "ingredients_json": [
            {
                "raw_text": "1/2 cup + 3 tablespoons all purpose flour",
                "name": "3 tablespoons all purpose flour",
                "quantity": 0.5,
                "unit": "cup",
            },
            {
                "raw_text": "500 grams 2 blocks cream cheese, softened",
                "name": "2 blocks cream cheese softened",
                "quantity": 500,
                "unit": "grams",
            },
        ],
        "cook_steps": [{"instruction": "Mix."}],
        "tags": [],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 20,
        "total_time_min": 25,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    ingredients = CatalogueV3Enricher().enrich_row(row).updates["ingredients_json"]

    assert ingredients[0]["name"] == "all purpose flour"
    assert ingredients[0]["normalized_text"] == "60 g all purpose flour"
    assert ingredients[1]["name"] == "cream cheese"
    assert ingredients[1]["normalized_text"] == "500 g cream cheese"


def test_catalogue_v3_enricher_cleans_count_prefixed_names_and_prep():
    row = {
        "name": "Poriyal",
        "description": "Vegetable stir fry",
        "ingredients_json": [
            {"raw_text": "5 Drumstick - cut into 3 inch pieces"},
            {"raw_text": "2 Green Chillies - slit"},
        ],
        "cook_steps": [{"instruction": "Cook."}],
        "tags": [],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 20,
        "total_time_min": 25,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    ingredients = CatalogueV3Enricher().enrich_row(row).updates["ingredients_json"]

    assert ingredients[0]["name"] == "Drumstick"
    assert ingredients[0]["quantity"] == 5
    assert ingredients[0]["canonical_unit"] == "count"
    assert ingredients[0]["normalized_text"] == "5 count Drumstick"
    assert ingredients[0]["prep"] == "cut into 3 inch pieces"
    assert ingredients[1]["name"] == "Green Chillies"
    assert ingredients[1]["quantity"] == 2
    assert ingredients[1]["normalized_text"] == "2 count Green Chillies"
    assert ingredients[1]["prep"] == "slit"


def test_catalogue_v3_enricher_does_not_infer_diet_from_source_id():
    row = {
        "name": "Curd Rice Recipe",
        "description": "A cooling rice dish with yogurt.",
        "source": "indianhealthyrecipes_chicken_web",
        "ingredients_json": [
            {"raw_text": "1 cup cooked rice"},
            {"raw_text": "1 cup curd"},
        ],
        "cook_steps": [{"instruction": "Mix rice and curd."}],
        "tags": [],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 2,
        "prep_time_min": 5,
        "cook_time_min": 0,
        "total_time_min": 5,
        "difficulty_level": None,
        "diet": None,
        "meal_role": None,
        "dish_family": None,
        "cost_tier": None,
        "budget_band": None,
        "region": None,
    }

    updates = CatalogueV3Enricher().enrich_row(row).updates

    assert updates.get("diet") is None
    assert "NON_VEGETARIAN" not in updates.get("diet_tags", [])


def test_catalogue_v3_enricher_does_not_mark_dairy_recipe_vegan():
    row = {
        "name": "Category Ladoo",
        "description": "A sweet from a vegan category page.",
        "ingredients_json": [
            {"raw_text": "1 cup rava"},
            {"raw_text": "2 tbsp ghee"},
        ],
        "cook_steps": [{"instruction": "Roast and mix."}],
        "tags": ["vegan"],
        "course": [],
        "cuisines": ["Indian"],
        "meal_types": [],
        "diet_tags": [],
        "allergen_tags": [],
        "health_tags": [],
        "efficiency_tags": [],
        "dish_types": [],
        "metadata": {},
        "servings": 4,
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

    updates = CatalogueV3Enricher().enrich_row(row).updates

    assert updates.get("diet") is None
    assert "VEGAN" not in updates.get("diet_tags", [])
