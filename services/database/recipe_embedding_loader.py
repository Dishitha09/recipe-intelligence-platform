from sqlalchemy import text

from services.database.connection import engine
from services.enrichment.embedding_generator import EmbeddingGenerator


class RecipeEmbeddingLoader:

    def __init__(self, generator=None):

        self.generator = generator or EmbeddingGenerator()


    def load_embeddings(self):

        with engine.begin() as conn:

            recipes = conn.execute(

                text("""

                SELECT

                    recipe_id,

                    title,

                    description

                FROM recipes

                """

                )

            ).fetchall()


            for row in recipes:

                recipe_id = row[0]

                title = row[1] or ""

                description = row[2] or ""


                text_for_embedding = f"""

                {title}

                {description}

                """


                embedding = self.generator.generate_embedding(

                    text_for_embedding

                )


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

                    CAST(:embedding AS vector)

                    )

                    """

                    ),

                    {

                        "recipe_id": recipe_id,

                        "embedding": self._vector_literal(embedding)

                    }

                )


                print(

                    "Embedded:",

                    recipe_id,

                    title

                )

    def insert_embedding(self, recipe_id, embedding):

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

                CAST(:embedding AS vector)

                )

                """),

                {

                    "recipe_id": recipe_id,

                    "embedding": self._vector_literal(embedding)

                }

            )

    def _vector_literal(self, embedding):

        values = embedding[0] if hasattr(embedding, "__len__") and len(embedding) == 1 else embedding

        if hasattr(values, "tolist"):

            values = values.tolist()

        return "[" + ",".join(str(float(value)) for value in values) + "]"
