from types import SimpleNamespace

from services.enrichment.ingredient_resolution.llm_resolver import LLMResolver


class FakeGeminiModel:
    def __init__(self, text):
        self.text = text
        self.prompts = []

    def generate_content(self, prompt):
        self.prompts.append(prompt)

        return SimpleNamespace(
            text=self.text,
            usage_metadata=SimpleNamespace(
                prompt_token_count=100,
                candidates_token_count=20,
            ),
        )


def test_llm_resolver_returns_canonical_name_and_counters():
    model = FakeGeminiModel(
        '{"canonical_name": "dry mango powder", '
        '"confidence_score": 0.82, '
        '"explanation": "common Indian ingredient alias"}'
    )
    resolver = LLMResolver(
        model=model,
        candidate_names=["amchur"],
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.002,
    )

    result = resolver.resolve_match("amchoor powder")

    assert result.canonical_name == "dry_mango_powder"
    assert result.confidence_score == 0.82
    assert result.review_required is True
    assert resolver.llm_calls_made == 1
    assert resolver.llm_calls_succeeded == 1
    assert resolver.llm_cost_usd > 0
    assert "amchoor powder" in model.prompts[0]
