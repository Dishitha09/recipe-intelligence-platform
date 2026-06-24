import os

from services.ingestion.source_adapter import SourceAdapter


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
        import pytesseract

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"{self.file_path} not found")

        image = Image.open(self.file_path)
        raw_text = pytesseract.image_to_string(image).strip()

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
                    "image_size": image.size,
                }
            )
        ]

        return self.raw_records
