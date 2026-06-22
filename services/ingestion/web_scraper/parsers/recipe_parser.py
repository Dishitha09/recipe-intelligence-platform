class RecipeParser:


    def parse_title(self, response):

        title = response.css(

            "h1::text"

        ).get()


        return title