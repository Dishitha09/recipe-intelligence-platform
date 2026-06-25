from urllib.parse import urlparse

from scrapy import signals
from scrapy.crawler import CrawlerProcess

from services.ingestion.source_adapter import SourceAdapter
from services.ingestion.web_scraper.spiders.recipe_crawl_spider import (
    RecipeCrawlSpider,
)


DEFAULT_USER_AGENT = "RecipeIntelligencePlatform/1.0 (+https://example.com)"


class ScrapyAdapter(SourceAdapter):
    source_type = "web"

    def __init__(self, url, source_id="web.scrapy", config=None):
        self.url = url
        self.raw_records = []
        super().__init__(source_id=source_id, config=config)

    def validate_config(self):
        super().validate_config()

        if not self.url:
            raise ValueError("url is required")

    def extract(self):
        settings = {
            "LOG_LEVEL": self.config.get("log_level", "INFO"),
            "USER_AGENT": self.config.get(
                "user_agent",
                self.config.get("default_user_agent", DEFAULT_USER_AGENT),
            ),
            "ROBOTSTXT_OBEY": bool(self.config.get("requires_robots_check", True)),
            "DOWNLOAD_DELAY": float(self.config.get("crawl_delay_seconds", 1)),
            "DEPTH_LIMIT": int(self.config.get("max_depth", 2)),
            "CONCURRENT_REQUESTS": int(self.config.get("concurrent_requests", 8)),
            "COOKIES_ENABLED": False,
            "TELNETCONSOLE_ENABLED": False,
        }

        start_urls = [self.url]
        parsed = urlparse(self.url)
        allowed_domains = self.config.get(
            "allowed_domains",
            [parsed.netloc] if parsed.netloc else [],
        )

        items = []

        def collect_item(item, response, spider):
            items.append(dict(item))

        process = CrawlerProcess(settings=settings)
        crawler = process.create_crawler(RecipeCrawlSpider)
        crawler.signals.connect(collect_item, signals.item_scraped)

        process.crawl(
            crawler,
            start_urls=start_urls,
            allowed_domains=allowed_domains,
            parser=self.config.get("parser", "default"),
        )
        process.start()

        self.raw_records = [
            self.build_raw_record(
                record,
                metadata={
                    "source_url": record.get("source_url"),
                    "scrape_source": self.url,
                    "parser": self.config.get("parser", "default"),
                },
            )
            for record in items
            if isinstance(record, dict)
        ]

        return self.raw_records
