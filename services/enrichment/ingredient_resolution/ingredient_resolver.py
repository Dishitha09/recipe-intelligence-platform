from services.enrichment.ingredient_resolution.alias_resolver import resolve_alias

from services.enrichment.ingredient_resolution.embedding_resolver import EmbeddingResolver



class IngredientResolver:


    def __init__(self):

        self.embedding_resolver = EmbeddingResolver()


    def resolve(self, ingredient_name):


        alias_result = resolve_alias(ingredient_name)


        if alias_result:

            return {

                "canonical_name": alias_result,

                "method":"alias"

            }


        embedding_result = self.embedding_resolver.resolve(
            ingredient_name
        )


        return {

            "canonical_name": embedding_result,

            "method":"embedding"

        }