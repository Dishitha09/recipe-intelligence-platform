import json

from scripts.export_catalogue_v3_reviewer_format import _export_row


def test_reviewer_export_uses_metric_ingredient_shape():
    row = {
        "name": "Egg Pulao",
        "course": ["main"],
        "region": "south_indian",
        "cuisines": ["Andhra", "South Indian"],
        "meal_types": ["lunch", "dinner"],
        "ingredients_json": [
            {
                "name": "2 cups Basmati rice - soaked",
                "raw_text": "2 cups basmati rice",
                "quantity": 2,
                "unit": "cups",
                "canonical_quantity": 400,
                "canonical_unit": "g",
            },
            {
                "name": "oil",
                "raw_text": "3 tbsp oil",
                "quantity": 3,
                "unit": "tbsp",
                "canonical_quantity": 45,
                "canonical_unit": "ml",
            },
        ],
        "is_public": True,
        "is_active": True,
    }

    exported = _export_row(row)
    ingredients = json.loads(exported["ingredients_json"])

    assert ingredients == [
        {
            "item": "Basmati rice",
            "quantity": 400,
            "unit": "g",
            "prep": "soaked",
        },
        {
            "item": "oil",
            "quantity": 45,
            "unit": "ml",
            "prep": None,
        },
    ]
    assert exported["course"] == '["main"]'
    assert exported["is_public"] == "TRUE"
