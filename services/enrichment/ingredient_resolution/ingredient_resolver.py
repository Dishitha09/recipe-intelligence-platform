from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
    resolve_alias_match,
)

from services.enrichment.ingredient_resolution.embedding_resolver import EmbeddingResolver



class IngredientResolver:


    def __init__(
        self,
        embedding_resolver=None,
        llm_resolver=None,
        enable_llm=False,
        enable_embedding=True,
        ingredient_repository=None,
        use_database=True,
    ):

        self.embedding_resolver = embedding_resolver
        self.llm_resolver = llm_resolver
        self.enable_llm = enable_llm
        self.enable_embedding = enable_embedding
        self.ingredient_repository = ingredient_repository
        self.use_database = use_database
        self.embedding_unavailable_error = None


    def resolve(self, ingredient_name):

        normalized_name = normalize_ingredient_name(ingredient_name)

        if not normalized_name:
            return self._unresolved_result(
                ingredient_name,
                normalized_name
            )

        database_alias_result = self._resolve_database_exact(
            ingredient_name,
            normalized_name
        )

        if database_alias_result:
            return database_alias_result

        alias_result = resolve_alias_match(ingredient_name)

        if alias_result:

            return alias_result


        if self.enable_embedding:
            try:
                embedding_result = self._resolve_database_vector(
                    ingredient_name,
                    normalized_name,
                ) or self._resolve_embedding(
                    ingredient_name
                )
            except Exception as exc:
                embedding_result = self._unresolved_result(
                    ingredient_name,
                    normalized_name,
                )
                embedding_result["enrichment_flags"].append(
                    "embedding_resolver_unavailable"
                )
                embedding_result["error"] = str(exc)
        else:
            embedding_result = self._unresolved_result(
                ingredient_name,
                normalized_name,
            )
            embedding_result["enrichment_flags"].append(
                "embedding_disabled"
            )

        if embedding_result["canonical_name"]:
            return embedding_result

        if self.enable_llm:
            llm_result = self._resolve_llm(
                ingredient_name,
                normalized_name
            )

            if llm_result["canonical_name"]:
                return llm_result

        return embedding_result

    def _resolve_embedding(self, ingredient_name):
        embedding_resolver = self._get_embedding_resolver()

        if hasattr(embedding_resolver, "resolve_match"):
            return embedding_resolver.resolve_match(ingredient_name)

        canonical_name = embedding_resolver.resolve(ingredient_name)

        if canonical_name is None:
            return self._unresolved_result(ingredient_name)

        return {
            "raw_name": ingredient_name,
            "normalized_name": normalize_ingredient_name(ingredient_name),
            "canonical_name": canonical_name,
            "method": "embedding",
            "tier": "vector_similarity",
            "confidence_score": 1.0,
            "enrichment_flags": [],
        }

    def _resolve_database_exact(self, ingredient_name, normalized_name):
        if not self.use_database:
            return None

        try:
            match = self._get_repository().resolve_exact(ingredient_name)
        except Exception:
            return None

        if match is None:
            return None

        return {
            "raw_name": ingredient_name,
            "normalized_name": normalized_name,
            "canonical_name": match["canonical_name"],
            "master_ingredient_id": match["ingredient_id"],
            "method": "database_alias",
            "tier": "exact_alias",
            "confidence_score": 1.0,
            "enrichment_flags": [],
        }

    def _resolve_database_vector(self, ingredient_name, normalized_name):
        if not self.use_database:
            return None

        embedding_resolver = self._get_embedding_resolver()

        if not hasattr(embedding_resolver, "embed_text"):
            return None

        query_embedding = embedding_resolver.embed_text(ingredient_name)

        try:
            match = self._get_repository().search_by_embedding(
                query_embedding,
                threshold=embedding_resolver.threshold,
            )
        except Exception:
            return None

        if match is None:
            return None

        return {
            "raw_name": ingredient_name,
            "normalized_name": normalized_name,
            "canonical_name": match["canonical_name"],
            "master_ingredient_id": match["ingredient_id"],
            "method": "database_embedding",
            "tier": "vector_similarity",
            "confidence_score": match["confidence_score"],
            "enrichment_flags": [],
        }

    def _resolve_llm(self, ingredient_name, normalized_name):
        llm_resolver = self._get_llm_resolver()

        if hasattr(llm_resolver, "resolve_match"):
            match = llm_resolver.resolve_match(ingredient_name)
            canonical_name = match.canonical_name
            confidence_score = match.confidence_score
            explanation = match.explanation
        else:
            canonical_name = llm_resolver.resolve(ingredient_name)
            confidence_score = 0.6
            explanation = ""

        if not canonical_name:
            return self._unresolved_result(
                ingredient_name,
                normalized_name
            )

        return {
            "raw_name": ingredient_name,
            "normalized_name": normalized_name,
            "canonical_name": canonical_name,
            "method": "llm",
            "tier": "llm_escalation",
            "confidence_score": confidence_score,
            "enrichment_flags": ["llm_review_required"],
            "llm_metadata": {
                "explanation": explanation,
                "llm_calls_made": getattr(
                    llm_resolver,
                    "llm_calls_made",
                    None,
                ),
                "llm_calls_succeeded": getattr(
                    llm_resolver,
                    "llm_calls_succeeded",
                    None,
                ),
                "llm_cost_usd": getattr(
                    llm_resolver,
                    "llm_cost_usd",
                    None,
                ),
            },
        }

    def _unresolved_result(
        self,
        ingredient_name,
        normalized_name=None,
        confidence_score=0.0,
    ):
        if normalized_name is None:
            normalized_name = normalize_ingredient_name(ingredient_name)

        return {
            "raw_name": ingredient_name,
            "normalized_name": normalized_name,
            "canonical_name": None,
            "method": "unresolved",
            "tier": "unresolved",
            "confidence_score": round(confidence_score, 4),
            "enrichment_flags": ["unresolved_ingredient"],
        }

    def _get_repository(self):
        if self.ingredient_repository is None:
            from services.database.ingredient_repository import (
                IngredientRepository,
            )

            self.ingredient_repository = IngredientRepository()

        return self.ingredient_repository

    def _get_embedding_resolver(self):
        if self.embedding_unavailable_error is not None:
            raise RuntimeError(self.embedding_unavailable_error)

        if self.embedding_resolver is not None:
            return self.embedding_resolver

        try:
            self.embedding_resolver = EmbeddingResolver()
        except Exception as exc:
            self.embedding_unavailable_error = (
                "Embedding resolver unavailable; install/cache the model or "
                "disable embedding fallback for offline ingestion. "
                f"Original error: {exc}"
            )
            raise RuntimeError(self.embedding_unavailable_error) from exc

        return self.embedding_resolver

    def _get_llm_resolver(self):
        if self.llm_resolver is None:
            from services.enrichment.ingredient_resolution.llm_resolver import (
                LLMResolver,
            )

            candidate_names = []

            if hasattr(self.embedding_resolver, "master_ingredients"):
                candidate_names = self.embedding_resolver.master_ingredients

            self.llm_resolver = LLMResolver(candidate_names=candidate_names)

        return self.llm_resolver
