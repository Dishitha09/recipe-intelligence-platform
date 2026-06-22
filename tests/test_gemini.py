from services.rag.llm_client import GeminiClient


client = GeminiClient()


response = client.generate(

    "What is Masala Dosa?"

)


print(response)