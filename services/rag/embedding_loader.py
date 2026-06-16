from sqlalchemy import text

from services.database.connection import engine



class EmbeddingLoader:


    def insert(

        self,

        recipe_id,

        embedding

    ):


        with engine.begin() as conn:


            conn.execute(


                text("""

                INSERT INTO recipe_embeddings

                (

                recipe_id,

                embedding

                )

                VALUES

                (

                :recipe_id,

                :embedding

                )

                """),


                {

                    "recipe_id":recipe_id,

                    "embedding":embedding

                }

            )