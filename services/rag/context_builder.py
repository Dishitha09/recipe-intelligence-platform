from sqlalchemy import text

from services.database.connection import engine

from services.retrieval.recipe_vector_search import (

    RecipeVectorSearch

)


class ContextBuilder:


    def __init__(self):

        self.searcher = RecipeVectorSearch()


    def build_context(

        self,

        question

    ):


        similar = self.searcher.search(

            question,

            top_k=5

        )


        context = ""


        with engine.begin() as conn:


            for row in similar:


                recipe_id = row[0]


                recipe = conn.execute(

                    text("""

                    SELECT

                    title,

                    cuisine,

                    description,

                    source_url

                    FROM recipes

                    WHERE recipe_id=:id

                    """),

                    {

                        "id": recipe_id

                    }

                ).fetchone()


                context += f"""

TITLE:

{recipe[0]}


CUISINE:

{recipe[1]}


DESCRIPTION:

{recipe[2]}


SOURCE:

{recipe[3]}

------------------

"""


        return context