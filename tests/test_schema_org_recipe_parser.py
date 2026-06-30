from scrapy.http import HtmlResponse

from services.ingestion.web_scraper.parsers.schema_org_recipe_parser import (
    parse_schema_org_recipe,
)


def make_response(html, url="https://example.com/recipe"):
    return HtmlResponse(
        url=url,
        body=html.encode("utf-8"),
        encoding="utf-8",
    )


def test_parse_schema_org_recipe_extracts_json_ld_recipe():
    response = make_response(
        """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Recipe",
              "name": "Tomato Rice",
              "description": "A quick South Indian rice dish.",
              "url": "https://example.com/tomato-rice",
              "image": "https://example.com/tomato-rice.jpg",
              "recipeIngredient": [
                "200 g rice",
                "150 g tomato",
                "10 ml oil"
              ],
              "recipeInstructions": [
                {"@type": "HowToStep", "text": "Cook rice."},
                {"@type": "HowToStep", "text": "Add tomato masala."}
              ]
            }
            </script>
          </head>
          <body></body>
        </html>
        """
    )

    recipe = parse_schema_org_recipe(response)

    assert recipe == {
        "title": "Tomato Rice",
        "description": "A quick South Indian rice dish.",
        "source_url": "https://example.com/tomato-rice",
        "ingredients": [
            "200 g rice",
            "150 g tomato",
            "10 ml oil",
        ],
        "steps": [
            "Cook rice.",
            "Add tomato masala.",
        ],
        "image": "https://example.com/tomato-rice.jpg",
    }


def test_parse_schema_org_recipe_returns_none_without_recipe_schema():
    response = make_response(
        """
        <html>
          <head>
            <script type="application/ld+json">
            {"@context": "https://schema.org", "@type": "Article"}
            </script>
          </head>
        </html>
        """
    )

    assert parse_schema_org_recipe(response) is None


def test_parse_schema_org_recipe_flattens_howto_sections():
    response = make_response(
        """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Recipe",
              "name": "Sectioned Dosa",
              "recipeIngredient": ["200 g rice", "50 g urad dal"],
              "recipeInstructions": [
                {
                  "@type": "HowToSection",
                  "name": "Batter",
                  "itemListElement": [
                    {"@type": "HowToStep", "text": "Soak rice and dal."},
                    {"@type": "HowToStep", "text": "Grind into batter."}
                  ]
                },
                {
                  "@type": "HowToSection",
                  "name": "Cook",
                  "itemListElement": [
                    {"@type": "HowToStep", "text": "Spread on hot tawa."}
                  ]
                }
              ]
            }
            </script>
          </head>
        </html>
        """
    )

    recipe = parse_schema_org_recipe(response)

    assert recipe["steps"] == [
        "Soak rice and dal.",
        "Grind into batter.",
        "Spread on hot tawa.",
    ]
