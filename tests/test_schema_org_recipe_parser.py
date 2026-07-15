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
              "recipeYield": "4 servings",
              "prepTime": "PT15M",
              "cookTime": "PT25M",
              "totalTime": "PT40M",
              "recipeCategory": "Dinner",
              "recipeCuisine": "South Indian",
              "keywords": "rice, tomato",
              "nutrition": {
                "calories": "250 kcal"
              },
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
        "servings": 4,
        "prep_time_min": 15,
        "cook_time_min": 25,
        "total_time_min": 40,
        "course": ["Dinner"],
        "cuisines": ["South Indian"],
        "tags": ["rice", "tomato"],
        "nutrition_info": {"calories": "250 kcal"},
        "instruction_source": "schema_org",
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


def test_parse_schema_org_recipe_filters_multilingual_junk_ingredients():
    response = make_response(
        """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Recipe",
              "name": "Besan Chilla",
              "recipeIngredient": [
                "1 cup besan",
                "1 tsp cumin",
                "1 टी स्पून जीरा",
                "1 ಟೀಸ್ಪೂನ್ ಜೀರಿಗೆ",
                "-",
                "250"
              ],
              "recipeInstructions": [
                {"@type": "HowToStep", "text": "Mix the batter."}
              ]
            }
            </script>
          </head>
        </html>
        """
    )

    recipe = parse_schema_org_recipe(response)

    assert recipe["ingredients"] == [
        "1 cup besan",
        "1 tsp cumin",
    ]


def test_parse_schema_org_recipe_prefers_full_article_instructions():
    response = make_response(
        """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Recipe",
              "name": "Pea Shoots",
              "recipeIngredient": ["200 g pea shoots", "1 tbsp oil"],
              "recipeInstructions": [
                {"@type": "HowToStep", "text": "Cook garlic and pea shoots."},
                {"@type": "HowToStep", "text": "Serve."}
              ]
            }
            </script>
          </head>
          <body>
            <h2>How to prepare them?</h2>
            <p>Rinse the pea shoots two to three times and drain completely.</p>
            <h2>How to stir fry pea shoots</h2>
            <p>1. Pour oil to a wok and add garlic and green chili.</p>
            <p>2. Let the garlic and chili cook on a low heat until aromatic.</p>
            <p>3. Add the pea shoots and sprinkle salt.</p>
            <p>4. Increase the flame to high and stir fry just for a minute.</p>
            <p>Remove to a serving plate immediately and serve.</p>
            <p>Here are some dishes that go well with this pea shoots stir fry.</p>
            <h2>Recipe Card</h2>
            <h3>Method</h3>
            <ol>
              <li>Cook garlic and pea shoots.</li>
              <li>Serve.</li>
            </ol>
          </body>
        </html>
        """
    )

    recipe = parse_schema_org_recipe(response)

    assert recipe["instruction_source"] == "html_article"
    assert recipe["steps"] == [
        "Rinse the pea shoots two to three times and drain completely.",
        "Pour oil to a wok and add garlic and green chili.",
        "Let the garlic and chili cook on a low heat until aromatic.",
        "Add the pea shoots and sprinkle salt.",
        "Increase the flame to high and stir fry just for a minute. "
        "Remove to a serving plate immediately and serve.",
    ]


def test_parse_schema_org_recipe_extracts_html_nutrition_fallback():
    response = make_response(
        """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Recipe",
              "name": "Nihari",
              "recipeIngredient": ["500 g mutton"],
              "recipeInstructions": [
                {"@type": "HowToStep", "text": "Cook slowly."}
              ]
            }
            </script>
          </head>
          <body>
            <h3>Nutrition</h3>
            <p>
              Calories 292 kcal Carbohydrates 26 g Protein 15 g
              Fat 16 g Sodium 975 mg
            </p>
            <h3>Comments</h3>
          </body>
        </html>
        """
    )

    recipe = parse_schema_org_recipe(response)

    assert recipe["nutrition_info"] == {
        "calories": "292 kcal",
        "carbohydrates": "26 g",
        "protein": "15 g",
        "fat": "16 g",
        "sodium": "975 mg",
    }


def test_parse_schema_org_recipe_extracts_page_text_nutrition_fallback():
    response = make_response(
        """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Recipe",
              "name": "Nihari",
              "recipeIngredient": ["500 g mutton"],
              "recipeInstructions": [
                {"@type": "HowToStep", "text": "Cook slowly."}
              ]
            }
            </script>
          </head>
          <body>
            <div>
              Nutrition Calories 292 kcal Carbohydrates 26 g
              Protein 15 g Fat 16 g Sodium 975 mg
            </div>
          </body>
        </html>
        """
    )

    recipe = parse_schema_org_recipe(response)

    assert recipe["nutrition_info"]["calories"] == "292 kcal"
    assert recipe["nutrition_info"]["protein"] == "15 g"
