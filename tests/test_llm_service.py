from services.rag.llm_service import LLMService


llm = LLMService()


response = llm.generate(

    "I have paneer and tomatoes"

)


print(response)