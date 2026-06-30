import scrapy
from urllib.parse import urlparse

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
            if not self._should_follow(href):
                continue

            yield response.follow(href, callback=self.parse)

    def _parse_html_recipe(self, response):
        title = self._extract_text(response.css("h1::text"))

        ingredients = self._extract_list_text(
            response,
            (
                "div.wprm-recipe-ingredient-group li, "
                "ul.ingredients li, "
                "li.ingredient, "
                "[itemprop='recipeIngredient']"
            ),
        )

        instructions = self._extract_list_text(
            response,
            (
                "div.wprm-recipe-instruction-text, "
                "div.wprm-recipe-instruction-group li, "
                "div.instructions li, "
                "ol.steps li, "
                "ol.recipe-instructions li, "
                "[itemprop='recipeInstructions'] li, "
                "[itemprop='recipeInstructions']"
            ),
        )

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

    @staticmethod
    def _extract_list_text(response, selector):
        values = []

        for element in response.css(selector):
            text = " ".join(
                item.strip()
                for item in element.css("::text").getall()
                if item.strip()
            )

            if text and text not in values:
                values.append(text)

        return values

    @staticmethod
    def _should_follow(href):
        if not href:
            return False

        href = href.strip()

        if not href or href.startswith("#"):
            return False

        parsed = urlparse(href)

        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return False

        if parsed.path.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".webp",
                ".pdf",
                ".zip",
            )
        ):
            return False

        return True
