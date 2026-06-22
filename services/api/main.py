from fastapi import FastAPI
from pydantic import BaseModel

from services.rag.recipe_rag import RecipeRAG

app = FastAPI(
    title="Recipe Intelligence API"
)

rag = RecipeRAG()


class QueryRequest(BaseModel):
    question: str


@app.get("/")
def home():

    return {
        "message": "Recipe Intelligence API Running"
    }


@app.post("/ask")
def ask_recipe(request: QueryRequest):

    answer = rag.answer(
        request.question
    )

    return {
        "question": request.question,
        "answer": answer
    }