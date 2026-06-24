import os

from services.ingestion.source_adapter import SourceAdapter


class PDFAdapter(SourceAdapter):
    source_type = "pdf"

    def __init__(self, file_path, source_id="pdf.default", config=None):
        self.file_path = file_path
        self.raw_records = []

        super().__init__(source_id=source_id, config=config)

    def validate_config(self):
        super().validate_config()

        if not self.file_path:
            raise ValueError("file_path is required")

    def extract(self):
        import pdfplumber

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"{self.file_path} not found")

        page_text = []

        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:
                page_text.append(page.extract_text() or "")

        raw_text = "\n".join(page_text).strip()

        self.raw_records = [
            self.build_raw_record(
                {
                    "title": None,
                    "raw_text": raw_text,
                    "source_url": None,
                },
                metadata={
                    "filename": os.path.basename(self.file_path),
                    "raw_path": self.file_path,
                    "page_count": len(page_text),
                }
            )
        ]

        return self.raw_records
