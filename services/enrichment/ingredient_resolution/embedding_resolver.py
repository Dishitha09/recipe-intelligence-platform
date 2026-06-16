from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class EmbeddingResolver:

    def __init__(self):

        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        self.master_ingredients = [

            "whole_wheat_flour",
            "chickpea",
            "gram_flour",
            "paneer",
            "rice",
            "tomato",
            "onion"

        ]

        self.master_embeddings = self.model.encode(
            self.master_ingredients
        )


    def resolve(self, ingredient):

        query_embedding = self.model.encode([ingredient])

        similarity = cosine_similarity(
            query_embedding,
            self.master_embeddings
        )

        idx = np.argmax(similarity)

        return self.master_ingredients[idx]