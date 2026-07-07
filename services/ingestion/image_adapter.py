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


class ImageAdapter(SourceAdapter):
    source_type = "image"

    def __init__(self, file_path, source_id="image.default", config=None):
        self.file_path = file_path
        self.raw_records = []

        super().__init__(source_id=source_id, config=config)

    def validate_config(self):
        super().validate_config()

        if not self.file_path:
            raise ValueError("file_path is required")

    def extract(self):
        from PIL import Image

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"{self.file_path} not found")

        image = Image.open(self.file_path)
        ocr_text_path = self.config.get("ocr_text_path")
        ocr_text = self.config.get("ocr_text")
        ocr_status = "tesseract"

        if ocr_text:
            raw_text = str(ocr_text).strip()
            ocr_status = "inline_config"
        elif ocr_text_path:
            raw_text = _read_text(ocr_text_path)
            ocr_status = "sidecar_file"
        else:
            import pytesseract

            raw_text = pytesseract.image_to_string(image).strip()

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
                    "image_size": image.size,
                    "ocr_status": ocr_status,
                    "ocr_text_path": ocr_text_path,
                }
            )
        ]

        return self.raw_records
