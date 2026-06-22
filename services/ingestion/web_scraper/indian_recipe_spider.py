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


        print("\nTOTAL URLS FOUND:", len(recipes))


        for recipe_url in recipes:

            yield response.follow(

                recipe_url,

                callback=self.parse_recipe

            )


    def parse_recipe(self, response):


        title = response.css(

            "h1::text"

        ).get()


        ingredients = response.css(

            "div.wprm-recipe-ingredient-group li ::text"

        ).getall()


        ingredients = [

            x.strip()

            for x in ingredients

            if x.strip()

        ]


        instructions = response.css(

            "div.wprm-recipe-instruction-text ::text"

        ).getall()


        instructions = [

            x.strip()

            for x in instructions

            if x.strip()

        ]


        yield {

            "title": title,

            "ingredients": " | ".join(ingredients),

            "instructions": " | ".join(instructions),

            "source_url": response.url

        }