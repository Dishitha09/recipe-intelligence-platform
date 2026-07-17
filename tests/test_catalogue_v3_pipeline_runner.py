from pathlib import Path

from services.ingestion.source_registry import SourceConfig
from scripts.run_catalogue_v3_pipeline import (
    PipelineOptions,
    run_catalogue_v3_pipeline,
    select_sources,
)


def source_config(
    source_id,
    enabled=True,
    source_group="structured_html",
    adapter="scrapy",
    priority=2,
):
    return SourceConfig(
        source_id=source_id,
        source_type="web",
        adapter=adapter,
        location=f"https://example.com/{source_id}",
        enabled=enabled,
        config={"source_group": source_group, "priority": priority},
    )


def test_select_sources_defaults_to_enabled_scrapy_sources():
    sources = [
        source_config("enabled_web", enabled=True),
        source_config("disabled_web", enabled=False),
        source_config("youtube_source", adapter="youtube"),
    ]

    selected = select_sources(sources)

    assert [source.source_id for source in selected] == ["enabled_web"]


def test_select_sources_can_include_disabled_group_when_allowed():
    sources = [
        source_config("one", enabled=False, priority=3),
        source_config("two", enabled=False, priority=1),
    ]

    selected = select_sources(
        sources,
        source_group="structured_html",
        allow_disabled=True,
    )

    assert [source.source_id for source in selected] == ["two", "one"]


def test_run_pipeline_chains_scrape_enrich_and_nutrition(tmp_path):
    config = tmp_path / "sources.json"
    config.write_text(
        """
        {
          "sources": [
            {
              "source_id": "example_web",
              "source_type": "web",
              "adapter": "scrapy",
              "location": "https://example.com",
              "enabled": true,
              "config": {
                "source_group": "structured_html",
                "priority": 1
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    calls = []

    def fake_scrape(**kwargs):
        calls.append(("scrape", kwargs["source_id"]))
        return {
            "source_id": kwargs["source_id"],
            "records_scraped": 3,
            "inserted": 2,
            "skipped_duplicate": 1,
            "updated_existing": 0,
            "skipped_invalid": 0,
            "failed": 0,
            "errors": [],
        }

    def fake_enrich(**kwargs):
        calls.append(("enrich", kwargs["source"]))
        return {"updated": 3}

    def fake_nutrition(**kwargs):
        calls.append(("nutrition", kwargs["source"]))
        return {"updated": 1}

    summary = run_catalogue_v3_pipeline(
        PipelineOptions(
            config_path=config,
            output_dir=tmp_path,
            track_runs=False,
        ),
        scrape_func=fake_scrape,
        enrich_func=fake_enrich,
        nutrition_func=fake_nutrition,
    )

    assert calls == [
        ("scrape", "example_web"),
        ("enrich", "example_web"),
        ("nutrition", "example_web"),
    ]
    assert summary["totals"]["records_scraped"] == 3
    assert summary["totals"]["inserted"] == 2
    assert summary["totals"]["skipped_duplicate"] == 1
    assert summary["totals"]["enriched"] == 3
    assert summary["totals"]["nutrition_updated"] == 1
    assert Path(summary["summary_path"]).exists()
