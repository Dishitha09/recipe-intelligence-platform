from services.rag.embedding_service import EmbeddingService

from services.rag.embedding_loader import EmbeddingLoader



service=EmbeddingService()

loader=EmbeddingLoader()



embedding=service.generate_embedding(

"Masala Dosa South Indian Rice"

)



loader.insert(

1,

embedding

)



print(

"Embedding Inserted"

)