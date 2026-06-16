ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS canonical_quantity FLOAT;


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS canonical_unit VARCHAR(50);