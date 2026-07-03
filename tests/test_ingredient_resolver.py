from services.enrichment.ingredient_resolution.ingredient_resolver import IngredientResolver
import services.enrichment.ingredient_resolution.ingredient_resolver as resolver_module
from types import SimpleNamespace


class FakeEmbeddingResolver:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def resolve_match(self, ingredient_name):
        self.calls.append(ingredient_name)
        return self.result


class FakeRepository:
    def __init__(self, exact=None, vector=None):
        self.exact = exact
        self.vector = vector
        self.exact_calls = []
        self.vector_calls = []

    def resolve_exact(self, ingredient_name):
        self.exact_calls.append(ingredient_name)
        return self.exact

    def search_by_embedding(self, embedding, threshold=0.88):
        self.vector_calls.append((embedding, threshold))
        return self.vector


class FakeVectorResolver:
    threshold = 0.88

    def embed_text(self, ingredient_name):
        return [[0.1, 0.2]]


class FakeLLMResolver:
    def __init__(self, canonical_name):
        self.canonical_name = canonical_name
        self.llm_calls_made = 0
        self.llm_calls_succeeded = 0
        self.llm_cost_usd = 0.001

    def resolve_match(self, ingredient_name):
        self.llm_calls_made += 1
        self.llm_calls_succeeded += 1

        return SimpleNamespace(
            raw_name=ingredient_name,
            normalized_name=ingredient_name,
            canonical_name=self.canonical_name,
            confidence_score=0.74,
            review_required=True,
            explanation="model escalation",
        )


def test_ingredient_resolver_uses_alias_before_embedding():
    embedding_resolver = FakeEmbeddingResolver(
        {
            "canonical_name": "wrong_match",
            "method": "embedding",
            "tier": "vector_similarity",
            "confidence_score": 0.99,
            "enrichment_flags": [],
        }
    )
    resolver = IngredientResolver(
        embedding_resolver=embedding_resolver,
        use_database=False,
    )

    result = resolver.resolve("atta")

    assert result["canonical_name"] == "whole_wheat_flour"
    assert result["method"] == "alias"
    assert result["tier"] == "exact_alias"
    assert embedding_resolver.calls == []


def test_ingredient_resolver_uses_database_exact_before_local_alias():
    repository = FakeRepository(
        exact={
            "ingredient_id": 101,
            "canonical_name": "whole_wheat_flour",
        }
    )
    resolver = IngredientResolver(
        embedding_resolver=FakeEmbeddingResolver(
            {
                "canonical_name": "wrong_match",
                "method": "embedding",
                "tier": "vector_similarity",
                "confidence_score": 0.99,
                "enrichment_flags": [],
            }
        ),
        ingredient_repository=repository,
    )

    result = resolver.resolve("atta")

    assert result["canonical_name"] == "whole_wheat_flour"
    assert result["master_ingredient_id"] == 101
    assert result["method"] == "database_alias"
    assert repository.exact_calls == ["atta"]


def test_ingredient_resolver_uses_database_vector_before_local_embedding():
    repository = FakeRepository(
        exact=None,
        vector={
            "ingredient_id": 202,
            "canonical_name": "amchur",
            "confidence_score": 0.91,
        }
    )
    resolver = IngredientResolver(
        embedding_resolver=FakeVectorResolver(),
        ingredient_repository=repository,
    )

    result = resolver.resolve("dry mango powder")

    assert result["canonical_name"] == "amchur"
    assert result["master_ingredient_id"] == 202
    assert result["method"] == "database_embedding"
    assert repository.vector_calls == [([[0.1, 0.2]], 0.88)]


def test_ingredient_resolver_uses_embedding_fallback():
    embedding_result = {
        "raw_name": "tamatar",
        "normalized_name": "tamatar",
        "canonical_name": "tomato",
        "method": "embedding",
        "tier": "vector_similarity",
        "confidence_score": 0.93,
        "enrichment_flags": [],
    }
    resolver = IngredientResolver(
        embedding_resolver=FakeEmbeddingResolver(embedding_result),
        use_database=False,
    )

    result = resolver.resolve("tamatar")

    assert result == embedding_result


def test_ingredient_resolver_can_disable_embedding_fallback():
    embedding_resolver = FakeEmbeddingResolver(
        {
            "raw_name": "unknown ingredient",
            "normalized_name": "unknown ingredient",
            "canonical_name": "should_not_be_used",
            "method": "embedding",
            "tier": "vector_similarity",
            "confidence_score": 0.99,
            "enrichment_flags": [],
        }
    )
    resolver = IngredientResolver(
        embedding_resolver=embedding_resolver,
        enable_embedding=False,
        use_database=False,
    )

    result = resolver.resolve("unknown ingredient")

    assert result["canonical_name"] is None
    assert result["method"] == "unresolved"
    assert "embedding_disabled" in result["enrichment_flags"]
    assert embedding_resolver.calls == []


def test_ingredient_resolver_flags_unresolved_ingredients():
    resolver = IngredientResolver(
        embedding_resolver=FakeEmbeddingResolver(
            {
                "raw_name": "unknown ingredient",
                "normalized_name": "unknown ingredient",
                "canonical_name": None,
                "method": "unresolved",
                "tier": "unresolved",
                "confidence_score": 0.42,
                "enrichment_flags": ["unresolved_ingredient"],
            }
        ),
        use_database=False,
    )

    result = resolver.resolve("unknown ingredient")

    assert result["canonical_name"] is None
    assert result["method"] == "unresolved"
    assert result["confidence_score"] == 0.42
    assert "unresolved_ingredient" in result["enrichment_flags"]


def test_ingredient_resolver_handles_blank_input():
    resolver = IngredientResolver(
        embedding_resolver=FakeEmbeddingResolver(
            {
                "canonical_name": "should_not_be_used",
                "method": "embedding",
                "tier": "vector_similarity",
                "confidence_score": 1.0,
                "enrichment_flags": [],
            }
        ),
        use_database=False,
    )

    result = resolver.resolve("   ")

    assert result["canonical_name"] is None
    assert result["method"] == "unresolved"
    assert result["normalized_name"] == ""
    assert "unresolved_ingredient" in result["enrichment_flags"]


def test_ingredient_resolver_escalates_to_llm_after_embedding_miss():
    embedding_result = {
        "raw_name": "amchoor powder",
        "normalized_name": "amchoor powder",
        "canonical_name": None,
        "method": "unresolved",
        "tier": "unresolved",
        "confidence_score": 0.31,
        "enrichment_flags": ["unresolved_ingredient"],
    }
    resolver = IngredientResolver(
        embedding_resolver=FakeEmbeddingResolver(embedding_result),
        llm_resolver=FakeLLMResolver("dry_mango_powder"),
        enable_llm=True,
        use_database=False,
    )

    result = resolver.resolve("amchoor powder")

    assert result["canonical_name"] == "dry_mango_powder"
    assert result["method"] == "llm"
    assert result["tier"] == "llm_escalation"
    assert result["confidence_score"] == 0.74
    assert result["llm_metadata"]["llm_calls_made"] == 1


def test_ingredient_resolver_caches_embedding_unavailable(monkeypatch):
    calls = []

    class BrokenEmbeddingResolver:
        def __init__(self):
            calls.append("load")
            raise OSError("offline")

    monkeypatch.setattr(
        resolver_module,
        "EmbeddingResolver",
        BrokenEmbeddingResolver,
    )
    resolver = IngredientResolver(use_database=False)

    first = resolver.resolve("unknown ingredient one")
    second = resolver.resolve("unknown ingredient two")

    assert first["canonical_name"] is None
    assert second["canonical_name"] is None
    assert "embedding_resolver_unavailable" in first["enrichment_flags"]
    assert "embedding_resolver_unavailable" in second["enrichment_flags"]
    assert calls == ["load"]
