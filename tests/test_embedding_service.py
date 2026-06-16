from services.rag.embedding_service import EmbeddingService



service=EmbeddingService()


embedding=service.generate_embedding(

"Masala Dosa South Indian Rice"

)



print(

len(embedding)

)



print(

embedding[:10]

)