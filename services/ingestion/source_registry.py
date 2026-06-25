import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from services.ingestion.audio_adapter import AudioAdapter
from services.ingestion.csv_adapter import CSVAdapter
from services.ingestion.dataset_adapter import DatasetAdapter
from services.ingestion.image_adapter import ImageAdapter
from services.ingestion.pdf_adapter import PDFAdapter
from services.ingestion.scrapy_adapter import ScrapyAdapter
from services.ingestion.source_adapter import SourceAdapter
from services.ingestion.text_adapter import TextAdapter
from services.ingestion.web_adapter import WebAdapter
from services.ingestion.youtube_adapter import YouTubeAdapter


ADAPTER_CLASSES: Dict[str, Type[SourceAdapter]] = {
    "audio": AudioAdapter,
    "csv": CSVAdapter,
    "dataset": DatasetAdapter,
    "image": ImageAdapter,
    "pdf": PDFAdapter,
    "scrapy": ScrapyAdapter,
    "text": TextAdapter,
    "web": WebAdapter,
    "youtube": YouTubeAdapter,
}


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    source_type: str
    adapter: str
    location: str
    enabled: bool = True
    config: Dict[str, Any] = None


@dataclass(frozen=True)
class SourceRunResult:
    source_id: str
    status: str
    records: List[Any]
    error: Optional[str] = None


class SourceRegistry:
    def __init__(self, configs=None, config_path=None):
        self.config_path = config_path
        self._last_mtime = None
        self.configs = configs or []

        if config_path:
            self.reload()

    def reload(self):
        if not self.config_path:
            return

        with open(self.config_path, "r", encoding="utf-8") as file:
            extension = os.path.splitext(self.config_path)[1].lower()

            if extension in {".yaml", ".yml"}:
                try:
                    import yaml
                except ImportError as exc:
                    raise RuntimeError(
                        "pyyaml is required to load YAML source registry config"
                    ) from exc

                payload = yaml.safe_load(file)
            else:
                payload = json.load(file)

        self.configs = [
            SourceConfig(
                source_id=item["source_id"],
                source_type=item["source_type"],
                adapter=item["adapter"],
                location=item["location"],
                enabled=item.get("enabled", True),
                config=item.get("config", {}),
            )
            for item in payload.get("sources", [])
        ]
        self._last_mtime = os.path.getmtime(self.config_path)

    def refresh_if_changed(self):
        if not self.config_path:
            return

        current_mtime = os.path.getmtime(self.config_path)

        if self._last_mtime is None or current_mtime > self._last_mtime:
            self.reload()

    def build_adapter(self, source_config):
        adapter_class = ADAPTER_CLASSES.get(source_config.adapter)

        if adapter_class is None:
            raise ValueError(f"Unknown adapter: {source_config.adapter}")

        return adapter_class(
            source_config.location,
            source_id=source_config.source_id,
            config={
                **(source_config.config or {}),
                "source_type": source_config.source_type,
            },
        )

    def run_all(self):
        self.refresh_if_changed()
        results = []

        for source_config in self.configs:
            if not source_config.enabled:
                continue

            try:
                adapter = self.build_adapter(source_config)
                records = adapter.extract()
                results.append(
                    SourceRunResult(
                        source_id=source_config.source_id,
                        status="completed",
                        records=records,
                    )
                )
            except Exception as exc:
                results.append(
                    SourceRunResult(
                        source_id=source_config.source_id,
                        status="failed",
                        records=[],
                        error=str(exc),
                    )
                )

        return results
