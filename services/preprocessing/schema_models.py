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

    nutrition_info: Optional[Dict[str, Any]] = None

    tags: List[str] = Field(default_factory=list)

    servings: Optional[int] = None

    difficulty_level: Optional[str] = None

    youtube_url: Optional[str] = None

    image_url: Optional[str] = None

    course: List[str] = Field(default_factory=list)

    # Recipe Classification

    cuisine: Optional[str] = None

    state: Optional[str] = None

    region: Optional[str] = None

    state_confidence: Optional[float] = None

    state_method: Optional[str] = None

    language: Optional[str] = None

    diet: Optional[str] = None

    spice_level: Optional[str] = None

    complexity: Optional[str] = None

    budget_band: Optional[str] = None

    diet_tags: List[str] = Field(default_factory=list)

    allergen_tags: List[str] = Field(default_factory=list)

    cuisines: List[str] = Field(default_factory=list)

    meal_types: List[str] = Field(default_factory=list)

    dish_types: List[str] = Field(default_factory=list)

    texture: List[str] = Field(default_factory=list)

    prep_time_min: Optional[int] = None

    cook_time_min: Optional[int] = None

    total_time_min: Optional[int] = None

    passive_time_min: Optional[int] = None

    # Duplicate Detection

    canonical_recipe_id: Optional[int] = None

    duplicate_score: Optional[float] = None

    estimated_cost_per_serving: Optional[float] = None

    popularity_score: Optional[float] = None

    side_category: Optional[str] = None

    meal_role: Optional[str] = None

    dish_family: Optional[str] = None

    health_tags: List[str] = Field(default_factory=list)

    efficiency_tags: List[str] = Field(default_factory=list)

    experience_tags: List[str] = Field(default_factory=list)

    cost_tier: Optional[str] = None

    festival_tags: List[str] = Field(default_factory=list)

    # Ingredients

    ingredients: List[Ingredient]

    # Recipe Steps

    steps: Optional[List[RecipeStep]] = []

    # Source Information

    source_type: str

    source_url: Optional[str] = None

    source: Optional[str] = None

    owner_code: Optional[str] = None

    owner_name: Optional[str] = None

    created_by: Optional[str] = None

    is_public: bool = False

    is_active: bool = True

    metadata: Optional[Dict[str, Any]] = None
