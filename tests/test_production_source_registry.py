import json

from services.ingestion.source_registry import ADAPTER_CLASSES, SourceRegistry


CONFIG_PATH = "configs/production_recipe_sources.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_production_source_registry_loads_configured_sources():
    registry = SourceRegistry(config_path=CONFIG_PATH)
    payload = load_config()

    assert len(registry.configs) == len(payload["sources"])
    assert len(registry.configs) >= 10

    for source in registry.configs:
        assert source.source_id
        assert source.source_type
        assert source.adapter in ADAPTER_CLASSES
        assert source.location
        assert source.config["expected_volume"] > 0


def test_production_source_registry_targets_large_scale_volume():
    payload = load_config()
    expected_total = sum(
        source["config"]["expected_volume"]
        for source in payload["sources"]
    )

    assert payload["pipeline"]["target_recipe_count"] == 20000
    assert expected_total >= payload["pipeline"]["target_recipe_count"]


def test_no_sources_are_enabled_by_default_for_real_only_catalogue():
    payload = load_config()
    enabled_sources = [
        source["source_id"]
        for source in payload["sources"]
        if source.get("enabled", True)
    ]

    assert enabled_sources == []


def test_local_fixture_is_marked_production_excluded():
    payload = load_config()
    fixture = next(
        source
        for source in payload["sources"]
        if source["source_id"] == "generated_indian_recipes_100"
    )

    assert fixture["enabled"] is False
    assert fixture["config"]["production_excluded"] is True
