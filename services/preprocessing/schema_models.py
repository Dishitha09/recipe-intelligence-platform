from pydantic import BaseModel
from typing import List, Optional


class RecipeStep(BaseModel):

    step_number: int

    instruction: str


class Ingredient(BaseModel):

    ingredient_name: str

    quantity: Optional[float] = None

    unit: Optional[str] = None

    preparation: Optional[str] = None


class Recipe(BaseModel):

    # Main Title

    title: str

    # Multilingual Support

    original_title: Optional[str] = None

    translated_title: Optional[str] = None

    # Description

    description: Optional[str] = None

    original_description: Optional[str] = None

    translated_description: Optional[str] = None

    # Recipe Classification

    cuisine: Optional[str] = None

    state: Optional[str] = None

    region: Optional[str] = None

    language: Optional[str] = None

    # Duplicate Detection

    canonical_recipe_id: Optional[int] = None

    duplicate_score: Optional[float] = None

    # Ingredients

    ingredients: List[Ingredient]

    # Recipe Steps

    steps: Optional[List[RecipeStep]] = []

    # Source Information

    source_type: str

    source_url: Optional[str] = None