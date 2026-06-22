import requests

from parsel import Selector

from services.ingestion.web_scraper.parsers.recipe_parser import RecipeParser


url = "https://www.indianhealthyrecipes.com/aloo-gobi-recipe/"


html = requests.get(

    url

).text


response = Selector(

    text=html

)


parser = RecipeParser()


print(

    parser.parse_title(

        response

    )

)