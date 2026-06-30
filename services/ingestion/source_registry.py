import importlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


ADAPTER_CLASSES = {
    "audio": "services.ingestion.audio_adapter:AudioAdapter",
    "csv": "services.ingestion.csv_adapter:CSVAdapter",
    "dataset": "services.ingestion.dataset_adapter:DatasetAdapter",
    "image": "services.ingestion.image_adapter:ImageAdapter",
    "pdf": "services.ingestion.pdf_adapter:PDFAdapter",
    "scrapy": "services.ingestion.scrapy_adapter:ScrapyAdapter",
    "text": "services.ingestion.text_adapter:TextAdapter",
    "web": "services.ingestion.web_adapter:WebAdapter",
    "youtube": "services.ingestion.youtube_adapter:YouTubeAdapter",
}


def get_adapter_class(adapter_name):
    adapter_path = ADAPTER_CLASSES.get(adapter_name)

    if adapter_path is None:
        raise ValueError(f"Unknown adapter: {adapter_name}")

    module_name, class_name = adapter_path.split(":", 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(
            f"Adapter '{adapter_name}' requires optional dependency or module "
            f"'{module_name}' that is not available."
        ) from exc

    return getattr(module, class_name)


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
        adapter_class = get_adapter_class(source_config.adapter)

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
