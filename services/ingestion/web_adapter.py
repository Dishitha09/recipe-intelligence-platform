from services.ingestion.source_adapter import SourceAdapter


class WebAdapter(SourceAdapter):
    source_type = "web"

    def __init__(self, url, source_id="web.default", config=None):
        self.url = url
        self.raw_records = []

        super().__init__(source_id=source_id, config=config)

    def validate_config(self):
        super().validate_config()

        if not self.url:
            raise ValueError("url is required")

    def extract(self):
        import requests
        from bs4 import BeautifulSoup

        timeout = self.config.get("timeout_seconds", 20)
        response = requests.get(self.url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        raw_text = soup.get_text(" ", strip=True)

        self.raw_records = [
            self.build_raw_record(
                {
                    "title": title,
                    "raw_text": raw_text,
                    "source_url": self.url,
                },
                metadata={
                    "http_status": response.status_code,
                    "content_type": response.headers.get("content-type"),
                }
            )
        ]

        return self.raw_records
