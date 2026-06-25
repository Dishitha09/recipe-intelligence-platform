from services.ingestion.web_scraper.spiders.recipe_crawl_spider import (
    RecipeCrawlSpider,
)


def test_recipe_crawl_spider_filters_non_page_links():
    assert RecipeCrawlSpider._should_follow("/paneer-recipes/") is True
    assert RecipeCrawlSpider._should_follow(
        "https://example.com/paneer-recipes/"
    ) is True

    assert RecipeCrawlSpider._should_follow("#comments") is False
    assert RecipeCrawlSpider._should_follow("mailto:test@example.com") is False
    assert RecipeCrawlSpider._should_follow("javascript:void(0)") is False
    assert RecipeCrawlSpider._should_follow("/recipe-card.jpg") is False
    assert RecipeCrawlSpider._should_follow("/cookbook.pdf") is False
