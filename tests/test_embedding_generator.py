from services.enrichment.embedding_generator import (

    EmbeddingGenerator

)


generator = EmbeddingGenerator()


text = """

Aloo Gobi Recipe

Potatoes

Cauliflower

Indian Curry

"""


embedding = generator.generate_embedding(

    text

)


print(

    len(embedding)

)

print(

    embedding[:10]

)