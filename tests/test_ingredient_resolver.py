from services.enrichment.ingredient_resolution.ingredient_resolver import IngredientResolver


resolver = IngredientResolver()


print(

resolver.resolve("atta")

)


print(

resolver.resolve("kadala")

)


print(

resolver.resolve("paneer")

)


print(

resolver.resolve("rice")

)