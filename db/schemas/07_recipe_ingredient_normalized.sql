ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS canonical_quantity FLOAT;


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS canonical_unit VARCHAR(50);


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS canonical_name VARCHAR(255);


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS resolution_method VARCHAR(50);


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS resolution_tier VARCHAR(50);


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS resolution_confidence FLOAT;


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS conversion_method VARCHAR(100);


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS conversion_factor FLOAT;


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS uom_confidence_score FLOAT;


ALTER TABLE recipe_ingredients

ADD COLUMN IF NOT EXISTS enrichment_flags JSONB DEFAULT '[]'::jsonb;
