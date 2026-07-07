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
    get_adapter_class,
)
from services.ingestion.text_adapter import TextAdapter
from services.ingestion.web_adapter import WebAdapter
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

    for adapter_name in expected - {"scrapy"}:
        adapter_class = get_adapter_class(adapter_name)
        assert issubclass(adapter_class, SourceAdapter)

    assert ADAPTER_CLASSES["scrapy"] == (
        "services.ingestion.scrapy_adapter:ScrapyAdapter"
    )


def test_all_file_and_url_adapters_validate_required_config():
    adapter_inputs = [
        (AudioAdapter, ""),
        (CSVAdapter, ""),
        (DatasetAdapter, ""),
        (ImageAdapter, ""),
        (PDFAdapter, ""),
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


def test_youtube_adapter_uses_transcript_sidecar(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text(
        "Dosa Transcript\nIngredients:\n1 cup rice\nInstructions:\nCook dosa.",
        encoding="utf-8",
    )

    adapter = YouTubeAdapter(
        "local-video",
        config={
            "transcript_path": str(transcript_path),
            "source_url": "file://transcript.txt",
        },
    )
    records = adapter.extract()

    assert records[0].raw_content["title"] == "Dosa Transcript"
    assert "1 cup rice" in records[0].raw_content["raw_text"]
    assert records[0].raw_content["source_url"] == "file://transcript.txt"
    assert records[0].metadata["transcript_status"] == "sidecar_file"


def test_image_adapter_uses_ocr_text_sidecar(tmp_path):
    image_path = tmp_path / "recipe.png"
    ocr_path = tmp_path / "recipe.txt"

    from PIL import Image

    Image.new("RGB", (10, 10), "white").save(image_path)
    ocr_path.write_text(
        "Poha Card\nIngredients:\n2 cups poha\nInstructions:\nSteam poha.",
        encoding="utf-8",
    )

    adapter = ImageAdapter(
        str(image_path),
        config={
            "ocr_text_path": str(ocr_path),
            "source_url": "file://recipe.png",
        },
    )
    records = adapter.extract()

    assert records[0].raw_content["title"] == "Poha Card"
    assert "2 cups poha" in records[0].raw_content["raw_text"]
    assert records[0].raw_content["source_url"] == "file://recipe.png"
    assert records[0].metadata["ocr_status"] == "sidecar_file"


def test_pdf_adapter_uses_text_sidecar(tmp_path):
    pdf_path = tmp_path / "cookbook.pdf"
    text_path = tmp_path / "cookbook.txt"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    text_path.write_text(
        "Coconut Rice Page\nIngredients:\n1 cup rice\nInstructions:\nMix rice.",
        encoding="utf-8",
    )

    adapter = PDFAdapter(
        str(pdf_path),
        config={
            "text_path": str(text_path),
            "source_url": "file://cookbook.pdf",
        },
    )
    records = adapter.extract()

    assert records[0].raw_content["title"] == "Coconut Rice Page"
    assert "1 cup rice" in records[0].raw_content["raw_text"]
    assert records[0].raw_content["source_url"] == "file://cookbook.pdf"
    assert records[0].metadata["extraction_status"] == "sidecar_file"


def test_source_registry_lazy_loads_adapter_classes():
    adapter_class = get_adapter_class("csv")

    assert adapter_class is CSVAdapter


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


def test_source_registry_loads_yaml_config_and_polling_watcher():
    payload = """
sources:
  - source_id: csv.yaml
    source_type: csv
    adapter: csv
    location: sample_recipes.csv
"""

    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as file:
        file.write(payload)
        config_path = file.name

    try:
        registry = SourceRegistry(config_path=config_path)

        assert len(registry.configs) == 1
        assert registry.configs[0].source_id == "csv.yaml"

        watcher = registry._start_polling_watcher(interval_seconds=0.01)
        watcher.stop_event.set()
        watcher.join(timeout=1)

        assert not watcher.is_alive()
    finally:
        os.remove(config_path)
