import os

from services.ingestion.source_adapter import SourceAdapter


def _first_nonempty_line(text):
    for line in str(text or "").splitlines():
        line = line.strip()
        if line:
            return line

    return None


def _read_text(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()


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
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"{self.file_path} not found")

        text_path = self.config.get("text_path")
        inline_text = self.config.get("text")
        extraction_status = "pdfplumber"

        if inline_text:
            raw_text = str(inline_text).strip()
            page_text = []
            extraction_status = "inline_config"
        elif text_path:
            raw_text = _read_text(text_path)
            page_text = []
            extraction_status = "sidecar_file"
        else:
            import pdfplumber

            page_text = []

            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    page_text.append(page.extract_text() or "")

            raw_text = "\n".join(page_text).strip()

            if not raw_text:
                extraction_status = "pdf_ocr_required"

        title = self.config.get("title") or _first_nonempty_line(raw_text)
        source_url = self.config.get("source_url")

        self.raw_records = [
            self.build_raw_record(
                {
                    "title": title,
                    "raw_text": raw_text,
                    "source_url": source_url,
                },
                metadata={
                    "filename": os.path.basename(self.file_path),
                    "raw_path": self.file_path,
                    "page_count": len(page_text),
                    "extraction_status": extraction_status,
                    "fallback_flags": [extraction_status]
                    if extraction_status == "pdf_ocr_required"
                    else [],
                    "text_path": text_path,
                }
            )
        ]

        return self.raw_records
