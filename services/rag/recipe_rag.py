from services.rag.context_builder import ContextBuilder

from services.rag.prompt_templates import SYSTEM_PROMPT

from services.rag.llm_client import GeminiClient


class RecipeRAG:


    def __init__(self):

        self.builder = ContextBuilder()

        self.llm = GeminiClient()


    def answer(

        self,

        question

    ):


        context = self.builder.build_context(

            question

        )


        prompt = f"""

{SYSTEM_PROMPT}


CONTEXT:

{context}


QUESTION:

{question}


ANSWER:

"""


        answer = self.llm.generate(

            prompt

        )


        return answer