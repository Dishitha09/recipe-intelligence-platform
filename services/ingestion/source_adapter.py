from abc import ABC, abstractmethod

from services.ingestion.raw_record import RawRecord


class SourceAdapter(ABC):
    source_type = None

    def __init__(self, source_id=None, config=None):
        self.source_id = source_id or self.__class__.__name__.lower()
        self.config = config or {}
        self.validate_config()

    @abstractmethod
    def extract(self):
        """Return a list of immutable RawRecord objects."""
        pass

    def validate_config(self):
        if not self.source_id:
            raise ValueError("source_id is required")

    def transform(self):
        return [
            record.raw_content
            for record in self.extract()
        ]

    def load(self):
        return self.extract()

    def build_raw_record(self, raw_content, metadata=None):
        if not isinstance(raw_content, dict):
            raise ValueError("raw_content must be a dictionary")

        source_type = self.source_type or self.config.get("source_type")

        if not source_type:
            raise ValueError("source_type is required")

        return RawRecord(
            source_id=self.source_id,
            source_type=source_type,
            _raw_content=raw_content,
            metadata=metadata or {},
        )
