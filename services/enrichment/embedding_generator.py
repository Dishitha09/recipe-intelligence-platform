from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:

    def __init__(self):

        self.model = SentenceTransformer(

            "sentence-transformers/all-MiniLM-L6-v2"

        )


    def generate_embedding(

        self,

        text

    ):

        embedding = self.model.encode(

            text

        )

        return embedding.tolist()