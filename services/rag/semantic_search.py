from sqlalchemy import text

from services.database.connection import engine

from services.rag.embedding_service import EmbeddingService



class SemanticSearch:


    def __init__(self):

        self.embedder=EmbeddingService()



    def search(

        self,

        query,

        top_k=5

    ):


        embedding=self.embedder.generate_embedding(

            query

        )



        with engine.begin() as conn:



            result=conn.execute(


                text("""

                SELECT

                r.recipe_id,

                r.title,

                r.cuisine,

                1-(

                    e.embedding <=> CAST(:embedding AS vector)

                ) AS similarity



                FROM recipe_embeddings e


                JOIN recipes r


                ON r.recipe_id=e.recipe_id



                ORDER BY


                e.embedding <=> CAST(:embedding AS vector)



                LIMIT :top_k

                """),


                {

                    "embedding":embedding,

                    "top_k":top_k

                }

            )



            return result.fetchall()