from services.enrichment.ingredient_resolution.embedding_resolver import EmbeddingResolver


resolver = EmbeddingResolver()


print(resolver.resolve("atta"))

print(resolver.resolve("kabuli chana"))

print(resolver.resolve("paneer"))