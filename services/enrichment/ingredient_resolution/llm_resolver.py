import json
import os
import re
from dataclasses import dataclass
from typing import Any

from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
)
from services.reliability.retry import transient_retry


@dataclass(frozen=True)
class LLMResolution:
    raw_name: str
    normalized_name: str
    canonical_name: str | None
    confidence_score: float
    review_required: bool
    explanation: str = ""


class LLMResolver:
    def __init__(
        self,
        model=None,
        model_name="gemini-2.5-flash",
        api_key=None,
        candidate_names=None,
        input_cost_per_1k=None,
        output_cost_per_1k=None,
    ):
        self.model = model
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.candidate_names = candidate_names or []
        self.input_cost_per_1k = float(
            input_cost_per_1k
            if input_cost_per_1k is not None
            else os.getenv("GEMINI_INPUT_COST_PER_1K", "0")
        )
        self.output_cost_per_1k = float(
            output_cost_per_1k
            if output_cost_per_1k is not None
            else os.getenv("GEMINI_OUTPUT_COST_PER_1K", "0")
        )
        self.llm_calls_made = 0
        self.llm_calls_succeeded = 0
        self.llm_calls_failed = 0
        self.llm_cost_usd = 0.0

    def resolve(self, ingredient_name):
        return self.resolve_match(ingredient_name).canonical_name

    def resolve_match(self, ingredient_name):
        normalized_name = normalize_ingredient_name(ingredient_name)

        if not normalized_name:
            return LLMResolution(
                raw_name=ingredient_name,
                normalized_name=normalized_name,
                canonical_name=None,
                confidence_score=0.0,
                review_required=True,
                explanation="blank ingredient name",
            )

        prompt = self._build_prompt(ingredient_name, normalized_name)
        self.llm_calls_made += 1

        try:
            response = self._generate_content(prompt)
            self.llm_calls_succeeded += 1
            self.llm_cost_usd += self._estimate_cost(prompt, response)
        except Exception:
            self.llm_calls_failed += 1
            raise

        return self._parse_response(
            ingredient_name=ingredient_name,
            normalized_name=normalized_name,
            response=response,
        )

    def _build_prompt(self, ingredient_name, normalized_name):
        candidates = ", ".join(self.candidate_names[:200])

        return (
            "You are resolving Indian recipe ingredient names to canonical "
            "ingredient identifiers. Return JSON only with keys "
            "canonical_name, confidence_score, explanation. "
            "Use snake_case canonical names. If unsure, set canonical_name "
            "to null and confidence_score to 0. "
            f"Raw ingredient: {ingredient_name!r}. "
            f"Normalized ingredient: {normalized_name!r}. "
            f"Known canonical candidates: {candidates or 'not provided'}."
        )

    @transient_retry
    def _generate_content(self, prompt):
        model = self._get_model()
        response = model.generate_content(prompt)
        return response

    def _get_model(self):
        if self.model is not None:
            return self.model

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is required for LLM ingredient resolution"
            )

        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        return self.model

    def _parse_response(self, ingredient_name, normalized_name, response):
        text = self._response_text(response)
        payload = self._loads_json(text)

        canonical_name = payload.get("canonical_name")
        confidence_score = payload.get("confidence_score", 0.0)
        explanation = payload.get("explanation", "")

        if canonical_name:
            canonical_name = normalize_ingredient_name(canonical_name).replace(
                " ",
                "_",
            )

        try:
            confidence_score = float(confidence_score)
        except (TypeError, ValueError):
            confidence_score = 0.0

        confidence_score = max(0.0, min(confidence_score, 1.0))

        return LLMResolution(
            raw_name=ingredient_name,
            normalized_name=normalized_name,
            canonical_name=canonical_name or None,
            confidence_score=round(confidence_score, 4),
            review_required=True,
            explanation=str(explanation or ""),
        )

    def _loads_json(self, text):
        text = (text or "").strip()

        if not text:
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.S)

            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        return {
            "canonical_name": text.strip().strip('"'),
            "confidence_score": 0.6,
            "explanation": "free-text model response",
        }

    def _response_text(self, response: Any):
        if isinstance(response, str):
            return response

        text = getattr(response, "text", None)

        if text is not None:
            return text

        return str(response)

    def _estimate_cost(self, prompt, response):
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        output_tokens = getattr(usage, "candidates_token_count", None)

        if prompt_tokens is None:
            prompt_tokens = max(1, len(prompt) // 4)

        if output_tokens is None:
            output_tokens = max(1, len(self._response_text(response)) // 4)

        return round(
            (prompt_tokens / 1000 * self.input_cost_per_1k)
            + (output_tokens / 1000 * self.output_cost_per_1k),
            8,
        )
