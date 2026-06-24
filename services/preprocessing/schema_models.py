from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class RecipeStep(BaseModel):

    step_number: int

    instruction: str


class Ingredient(BaseModel):

    ingredient_name: str

    quantity: Optional[float] = None

    unit: Optional[str] = None

    preparation: Optional[str] = None

    canonical_name: Optional[str] = None

    master_ingredient_id: Optional[int] = None

    resolution_method: Optional[str] = None

    resolution_tier: Optional[str] = None

    resolution_confidence: Optional[float] = None

    canonical_quantity: Optional[float] = None

    canonical_unit: Optional[str] = None

    conversion_method: Optional[str] = None

    conversion_factor: Optional[float] = None

    uom_confidence_score: Optional[float] = None

    enrichment_flags: List[str] = Field(default_factory=list)

    allergen_flags: List[str] = Field(default_factory=list)


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

    metadata: Optional[Dict[str, Any]] = None
