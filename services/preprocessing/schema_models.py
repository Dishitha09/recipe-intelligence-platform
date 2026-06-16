from pydantic import BaseModel
from typing import List, Optional
from typing import List, Optional

from pydantic import BaseModel



class RecipeStep(BaseModel):

    step_number:int

    instruction:str

class Ingredient(BaseModel):
    steps: Optional[List[RecipeStep]] = []

    ingredient_name: str

    quantity: Optional[float] = None

    unit: Optional[str] = None

    preparation: Optional[str] = None


class Recipe(BaseModel):

    title: str

    description: Optional[str] = None

    cuisine: Optional[str] = None

    ingredients: List[Ingredient]

    source_type: str

    source_url: Optional[str] = None

    language: Optional[str] = None