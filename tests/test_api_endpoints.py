from fastapi.testclient import TestClient

from services.api import main


client = TestClient(main.app)


def test_recipe_listing_endpoint_passes_filters(monkeypatch):
    captured = {}

    def fake_list_recipes_from_db(**kwargs):
        captured.update(kwargs)
        return {
            "items": [
                {
                    "recipe_id": 1,
                    "title": "Masala Dosa",
                    "state": "Tamil Nadu",
                }
            ],
            "page": kwargs["page"],
            "limit": kwargs["limit"],
            "total": 1,
        }

    monkeypatch.setattr(
        main,
        "list_recipes_from_db",
        fake_list_recipes_from_db,
    )

    response = client.get(
        "/recipes",
        params={
            "q": "dosa",
            "state": "Tamil Nadu",
            "page": 2,
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Masala Dosa"
    assert captured["search"] == "dosa"
    assert captured["state"] == "Tamil Nadu"
    assert captured["page"] == 2
    assert captured["limit"] == 5


def test_advanced_search_endpoint_supports_rating_filter(monkeypatch):
    captured = {}

    def fake_list_recipes_from_db(**kwargs):
        captured.update(kwargs)
        return {"items": [], "page": 1, "limit": 10, "total": 0}

    monkeypatch.setattr(
        main,
        "list_recipes_from_db",
        fake_list_recipes_from_db,
    )

    response = client.post(
        "/search",
        json={
            "query": "paneer",
            "region": "North",
            "min_rating": 4.0,
            "limit": 10,
        },
    )

    assert response.status_code == 200
    assert captured["search"] == "paneer"
    assert captured["region"] == "North"
    assert captured["min_rating"] == 4.0


def test_recipe_detail_endpoint_returns_404_for_missing_recipe(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_recipe_detail_from_db",
        lambda recipe_id: None,
    )

    response = client.get("/recipes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Recipe not found"


def test_recipe_detail_endpoint_returns_steps_and_source(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_recipe_detail_from_db",
        lambda recipe_id: {
            "recipe_id": recipe_id,
            "title": "Nihari",
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "Brown onions and spices.",
                }
            ],
            "source_transparency": {
                "source_type": "web",
                "source_url": "https://example.com/nihari",
                "tracking": [],
            },
        },
    )

    response = client.get("/recipes/7")

    assert response.status_code == 200
    assert response.json()["steps"][0]["instruction"] == (
        "Brown onions and spices."
    )
    assert response.json()["source_transparency"]["source_type"] == "web"


def test_add_review_endpoint_returns_updated_summary(monkeypatch):
    monkeypatch.setattr(
        main,
        "create_review_in_db",
        lambda recipe_id, payload: {
            "review_id": 3,
            "recipe_id": recipe_id,
            "user_name": payload.user_name,
            "rating": payload.rating,
            "review_text": payload.review_text,
        },
    )
    monkeypatch.setattr(
        main,
        "get_rating_summary_from_db",
        lambda recipe_id: {
            "recipe_id": recipe_id,
            "review_count": 1,
            "average_rating": 5,
        },
    )

    response = client.post(
        "/recipes/7/reviews",
        json={
            "user_name": "Dishitha",
            "rating": 5,
            "review_text": "Loved it.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["rating"] == 5
    assert body["summary"]["review_count"] == 1
