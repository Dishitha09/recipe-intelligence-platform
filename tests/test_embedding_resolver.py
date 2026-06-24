from services.enrichment.ingredient_resolution.embedding_resolver import EmbeddingResolver


class FakeModel:
    def encode(self, values):
        vectors = {
            "tomato": [1.0, 0.0],
            "onion": [0.0, 1.0],
            "tamatar": [0.99, 0.01],
            "mystery powder": [0.4, 0.6],
        }

        return [vectors[value] for value in values]


def test_embedding_resolver_returns_best_match_above_threshold():
    resolver = EmbeddingResolver(
        model=FakeModel(),
        master_ingredients=["tomato", "onion"],
        threshold=0.88,
    )

    result = resolver.resolve_match("tamatar")

    assert result["canonical_name"] == "tomato"
    assert result["method"] == "embedding"
    assert result["tier"] == "vector_similarity"
    assert result["confidence_score"] >= 0.88
    assert result["enrichment_flags"] == []


def test_embedding_resolver_flags_low_confidence_matches():
    resolver = EmbeddingResolver(
        model=FakeModel(),
        master_ingredients=["tomato", "onion"],
        threshold=0.9,
    )

    result = resolver.resolve_match("mystery powder")

    assert result["canonical_name"] is None
    assert result["method"] == "unresolved"
    assert result["tier"] == "unresolved"
    assert "unresolved_ingredient" in result["enrichment_flags"]
