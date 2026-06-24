import json
import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class FieldMapping:
    source_id: str
    source_type: str
    fields: Dict[str, List[str]]
    defaults: Dict[str, object] = field(default_factory=dict)


class FieldMappingRegistry:
    def __init__(self, mappings=None):
        self.mappings = mappings or {}

    @classmethod
    def from_json(cls, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        return cls.from_payload(payload)

    @classmethod
    def from_file(cls, file_path):
        extension = os.path.splitext(file_path)[1].lower()

        with open(file_path, "r", encoding="utf-8") as file:
            if extension in {".yaml", ".yml"}:
                try:
                    import yaml
                except ImportError as exc:
                    raise RuntimeError(
                        "pyyaml is required to load YAML field mappings"
                    ) from exc

                payload = yaml.safe_load(file)
            else:
                payload = json.load(file)

        return cls.from_payload(payload)

    @classmethod
    def from_payload(cls, payload):
        mappings = {}

        for item in payload.get("mappings", []):
            mapping = FieldMapping(
                source_id=item["source_id"],
                source_type=item["source_type"],
                fields=item.get("fields", {}),
                defaults=item.get("defaults", {}),
            )
            mappings[mapping.source_id] = mapping

        return cls(mappings)

    def get(self, source_id, source_type=None):
        mapping = self.mappings.get(source_id)

        if mapping:
            return mapping

        for candidate in self.mappings.values():
            if candidate.source_type == source_type:
                return candidate

        raise ValueError(
            f"No field mapping found for source_id={source_id}"
        )
