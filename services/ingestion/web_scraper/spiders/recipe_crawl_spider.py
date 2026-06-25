import scrapy

from services.ingestion.web_scraper.parsers.schema_org_recipe_parser import (
    parse_schema_org_recipe,
)


class RecipeCrawlSpider(scrapy.Spider):
    name = "recipe_crawl_spider"

    def __init__(self, start_urls=None, allowed_domains=None, parser="default", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.allowed_domains = allowed_domains or []
        self.parser = parser

    def parse(self, response):
        recipe = None

        if self.parser.startswith("schema_org_recipe_json_ld"):
            recipe = parse_schema_org_recipe(response)
        else:
            recipe = self._parse_html_recipe(response)

        if recipe:
            yield recipe

        for href in response.css("a::attr(href)").getall():
            yield response.follow(href, callback=self.parse)

    def _parse_html_recipe(self, response):
        title = self._extract_text(response.css("h1::text"))

        ingredients = [
            text.strip()
            for text in response.css(
                "div.wprm-recipe-ingredient-group li ::text, ul.ingredients li ::text, li.ingredient ::text"
            ).getall()
            if text.strip()
        ]

        instructions = [
            text.strip()
            for text in response.css(
                "div.wprm-recipe-instruction-text ::text, div.instructions li ::text, ol.steps li ::text"
            ).getall()
            if text.strip()
        ]

        if not title or (not ingredients and not instructions):
            return None

        return {
            "title": title,
            "description": self._extract_text(response.css("meta[name='description']::attr(content)")) or "",
            "source_url": response.url,
            "ingredients": ingredients,
            "steps": instructions,
        }

    @staticmethod
    def _extract_text(selector):
        if not selector:
            return None
        return selector.get().strip()
