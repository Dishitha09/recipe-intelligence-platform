import scrapy


class IndianRecipeSpider(scrapy.Spider):

    name = "indian_recipes"

    start_urls = [
        "https://www.indianhealthyrecipes.com/"
    ]

    def parse(self, response):

        recipes = response.css(
            "h2.entry-title a::attr(href)"
        ).getall()

        for recipe in recipes:

            yield {
                "recipe_url": recipe
            }

        next_page = response.css(
            "a.next.page-numbers::attr(href)"
        ).get()

        if next_page:

            yield response.follow(
                next_page,
                callback=self.parse
            )