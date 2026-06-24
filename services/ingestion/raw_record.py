from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                key: _freeze(item)
                for key, item in value.items()
            }
        )

    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)

    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)

    return value


@dataclass(frozen=True)
class RawRecord:
    source_id: str
    source_type: str
    _raw_content: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    record_id: str = field(default_factory=lambda: str(uuid4()))
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        object.__setattr__(self, "_raw_content", _freeze(self._raw_content))
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @property
    def raw_content(self):
        return self._raw_content

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "raw_content": _thaw(self.raw_content),
            "metadata": _thaw(self.metadata),
            "ingested_at": self.ingested_at,
        }


def _thaw(value):
    if isinstance(value, Mapping):
        return {
            key: _thaw(item)
            for key, item in value.items()
        }

    if isinstance(value, tuple):
        return [_thaw(item) for item in value]

    return value
