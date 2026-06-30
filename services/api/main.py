from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Recipe Intelligence API"
)

rag = None


def get_rag():
    global rag

    if rag is None:
        from services.rag.recipe_rag import RecipeRAG

        rag = RecipeRAG()

    return rag


class QueryRequest(BaseModel):
    question: str


@app.get("/")
def home():

    return {
        "message": "Recipe Intelligence API Running"
    }


@app.post("/ask")
def ask_recipe(request: QueryRequest):

    answer = get_rag().answer(
        request.question
    )

    return {
        "question": request.question,
        "answer": answer
    }
