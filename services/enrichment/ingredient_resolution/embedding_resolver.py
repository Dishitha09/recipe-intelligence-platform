import numpy as np

from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
)
from services.reliability.retry import transient_retry


class EmbeddingResolver:

    DEFAULT_MASTER_INGREDIENTS = [
        "whole_wheat_flour",
        "chickpea",
        "gram_flour",
        "paneer",
        "rice",
        "tomato",
        "onion",
        "potato",
        "cauliflower_florets",
        "oil",
        "clarified_butter",
    ]

    def __init__(
        self,
        model=None,
        master_ingredients=None,
        threshold=0.88,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.model = model or self._load_model(model_name)
        self.threshold = threshold
        self.master_ingredients = master_ingredients or list(
            self.DEFAULT_MASTER_INGREDIENTS
        )
        self.master_embeddings = self.model.encode(self.master_ingredients)

    @transient_retry
    def _load_model(self, model_name):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for embedding resolution. "
                "Inject a model in tests or install project dependencies."
            ) from exc

        return SentenceTransformer(model_name)

    def _cosine_similarity(self, query_embedding):
        query = np.asarray(query_embedding, dtype=float)
        candidates = np.asarray(self.master_embeddings, dtype=float)

        if query.ndim == 1:
            query = query.reshape(1, -1)

        query_norm = np.linalg.norm(query, axis=1, keepdims=True)
        candidate_norm = np.linalg.norm(candidates, axis=1, keepdims=True)
        denominator = query_norm * candidate_norm.T

        with np.errstate(divide="ignore", invalid="ignore"):
            scores = np.divide(
                query @ candidates.T,
                denominator,
                out=np.zeros((query.shape[0], candidates.shape[0])),
                where=denominator != 0,
            )

        return scores

    def resolve_match(self, ingredient):
        normalized_name = normalize_ingredient_name(ingredient)

        if not normalized_name:
            return {
                "raw_name": ingredient,
                "normalized_name": normalized_name,
                "canonical_name": None,
                "method": "unresolved",
                "tier": "unresolved",
                "confidence_score": 0.0,
                "enrichment_flags": ["unresolved_ingredient"],
            }

        query_embedding = self.embed_text(normalized_name)
        similarity = self._cosine_similarity(query_embedding)
        idx = int(np.argmax(similarity))
        score = float(similarity[0][idx])

        if score < self.threshold:
            return {
                "raw_name": ingredient,
                "normalized_name": normalized_name,
                "canonical_name": None,
                "method": "unresolved",
                "tier": "unresolved",
                "confidence_score": round(score, 4),
                "enrichment_flags": ["unresolved_ingredient"],
            }

        return {
            "raw_name": ingredient,
            "normalized_name": normalized_name,
            "canonical_name": self.master_ingredients[idx],
            "method": "embedding",
            "tier": "vector_similarity",
            "confidence_score": round(score, 4),
            "enrichment_flags": [],
        }

    def resolve(self, ingredient):
        return self.resolve_match(ingredient)["canonical_name"]

    @transient_retry
    def embed_text(self, ingredient):
        normalized_name = normalize_ingredient_name(ingredient)
        return self.model.encode([normalized_name])
