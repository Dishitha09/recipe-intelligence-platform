from services.rag.recipe_retriever import RecipeRetriever


class RecipeChat:


    def __init__(self):

        self.retriever = RecipeRetriever()


    def ask(

        self,

        question

    ):


        recipes = self.retriever.retrieve(

            question,

            top_k=3

        )


        response = []


        for r in recipes:


            response.append(

                {

                    "recipe_id": r[0],

                    "title": r[1],

                    "cuisine": r[2],

                    "similarity": round(float(r[3]),3)

                }

            )


        return response