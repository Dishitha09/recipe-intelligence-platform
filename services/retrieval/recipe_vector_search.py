from sqlalchemy import text

from services.database.connection import engine

from services.enrichment.embedding_generator import (

    EmbeddingGenerator

)


class RecipeVectorSearch:


    def __init__(self):

        self.embedder = EmbeddingGenerator()


    def search(

        self,

        query,

        top_k=5

    ):


        query_embedding = self.embedder.generate_embedding(

            query

        )


        with engine.begin() as conn:


            result = conn.execute(

                text("""

                SELECT

                    r.recipe_id,

                    r.title,

                    re.embedding <=> CAST(:embedding AS vector)

                    AS distance

                FROM recipe_embeddings re

                JOIN recipes r

                ON r.recipe_id=re.recipe_id

                ORDER BY distance

                LIMIT :top_k

                """),

                {

                    "embedding": str(query_embedding),

                    "top_k": top_k

                }

            )


            return result.fetchall()