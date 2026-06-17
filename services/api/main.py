from fastapi import FastAPI

from pydantic import BaseModel

from services.rag.recipe_chat import RecipeChat

from services.rag.prompt_builder import PromptBuilder

from services.rag.llm_service import LLMService


app = FastAPI(

    title="Recipe Intelligence Platform",

    version="1.0"

)


chat = RecipeChat()

builder = PromptBuilder()

llm = LLMService()



class ChatRequest(BaseModel):

    question:str



@app.get("/")

def home():

    return {

        "message":"Recipe Intelligence Platform API"

    }



@app.post("/chat")

def ask_chat(data:ChatRequest):


    recipes = chat.ask(

        data.question

    )


    prompt = builder.build(

        data.question,

        recipes

    )


    answer = llm.generate(

        prompt

    )


    return {

        "question":data.question,

        "recipes":recipes,

        "answer":answer

    }