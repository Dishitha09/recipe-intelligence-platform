import json
import os
import tempfile

from services.ingestion.audio_adapter import AudioAdapter
from services.ingestion.csv_adapter import CSVAdapter
from services.ingestion.dataset_adapter import DatasetAdapter
from services.ingestion.image_adapter import ImageAdapter
from services.ingestion.pdf_adapter import PDFAdapter
from services.ingestion.raw_record import RawRecord
from services.ingestion.source_adapter import SourceAdapter
from services.ingestion.source_registry import (
    ADAPTER_CLASSES,
    SourceConfig,
    SourceRegistry,
)
from services.ingestion.text_adapter import TextAdapter
from services.ingestion.web_adapter import WebAdapter
from services.ingestion.scrapy_adapter import ScrapyAdapter
from services.ingestion.youtube_adapter import YouTubeAdapter


def test_raw_record_content_is_immutable():
    record = RawRecord(
        source_id="test.source",
        source_type="csv",
        _raw_content={"title": "Dosa", "nested": {"x": 1}},
    )

    try:
        record.raw_content["title"] = "Changed"
        changed = True
    except TypeError:
        changed = False

    assert changed is False
    assert record.raw_content["title"] == "Dosa"


def test_csv_adapter_extract_returns_raw_records_with_unique_ids():
    adapter = CSVAdapter("sample_recipes.csv", source_id="csv.default")

    records = adapter.extract()
    record_ids = {record.record_id for record in records}

    assert len(records) == 3
    assert len(record_ids) == 3
    assert records[0].source_id == "csv.default"
    assert records[0].source_type == "csv"
    assert records[0].raw_content["title"] == "Masala Dosa"


def test_all_source_types_are_registered_and_implement_contract():
    expected = {
        "audio",
        "csv",
        "dataset",
        "image",
        "pdf",
        "scrapy",
        "text",
        "web",
        "youtube",
    }

    assert set(ADAPTER_CLASSES.keys()) == expected

    for adapter_class in ADAPTER_CLASSES.values():
        assert issubclass(adapter_class, SourceAdapter)


def test_all_file_and_url_adapters_validate_required_config():
    adapter_inputs = [
        (AudioAdapter, ""),
        (CSVAdapter, ""),
        (DatasetAdapter, ""),
        (ImageAdapter, ""),
        (PDFAdapter, ""),
        (ScrapyAdapter, ""),
        (TextAdapter, ""),
        (WebAdapter, ""),
        (YouTubeAdapter, ""),
    ]

    for adapter_class, location in adapter_inputs:
        try:
            adapter_class(location)
            raised = False
        except ValueError:
            raised = True

        assert raised is True


def test_source_registry_isolates_adapter_failures():
    registry = SourceRegistry(
        configs=[
            SourceConfig(
                source_id="csv.default",
                source_type="csv",
                adapter="csv",
                location="sample_recipes.csv",
            ),
            SourceConfig(
                source_id="missing.text",
                source_type="text",
                adapter="text",
                location="missing-file.txt",
            ),
        ]
    )

    results = registry.run_all()

    assert results[0].status == "completed"
    assert len(results[0].records) == 3
    assert results[1].status == "failed"
    assert "not found" in results[1].error


def test_raw_record_generates_unique_ids_at_scale():
    record_ids = {
        RawRecord(
            source_id="test.source",
            source_type="csv",
            _raw_content={"index": index},
        ).record_id
        for index in range(10000)
    }

    assert len(record_ids) == 10000


def test_source_registry_hot_reloads_json_config():
    first_payload = {
        "sources": [
            {
                "source_id": "csv.default",
                "source_type": "csv",
                "adapter": "csv",
                "location": "sample_recipes.csv",
            }
        ]
    }
    second_payload = {
        "sources": [
            *first_payload["sources"],
            {
                "source_id": "text.default",
                "source_type": "text",
                "adapter": "text",
                "location": "sample_recipe.txt",
            },
        ]
    }

    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as file:
        json.dump(first_payload, file)
        config_path = file.name

    try:
        registry = SourceRegistry(config_path=config_path)
        assert len(registry.configs) == 1

        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(second_payload, file)

        os.utime(config_path, None)
        registry._last_mtime = 0
        registry.refresh_if_changed()

        assert len(registry.configs) == 2
    finally:
        os.remove(config_path)
