# ShopConnect Recipe Intelligence Platform

Date: 2026-07-15

This report summarizes the Recipe Intelligence Platform work completed so far, maps it against the attached ShopConnect PS-1 to PS-5 problem statement, and gives a code walkthrough of the current production-grade pipeline.

## Current Status

The project now has a working end-to-end recipe data pipeline covering ingestion, schema coercion, enrichment, UOM normalization, validation, PostgreSQL persistence, pgvector search support, v3 catalogue loading, and real multi-source recipe data.

Current confirmed PostgreSQL `recipe_catalogue_v3` counts:

```text
Total v3 recipes:        6,496
Live web-scraped rows:   1,095
```

Current v3 source counts:

```text
nileshiq/Indian-Food:              3,654
Anupam007/indian-recipe-dataset:   1,747
veg_recipes_of_india_web:            605
hebbars_kitchen_web:                 151
indianhealthyrecipes_egg_web:        110
indianhealthyrecipes_chicken_web:     83
scrapy_indianhealthyrecipes:          68
whiskaffair_web:                      54
indianhealthyrecipes_vegan_web:       24
```

Current diet distribution:

```text
vegetarian:                   2,991
unclassified:                 2,409
non_vegetarian:                 617
diabetic_friendly:              181
egg:                            134
vegan:                           89
no_onion_no_garlic_sattvic:      49
gluten_free:                     26
```

Latest full test run:

```text
117 passed, 1 warning
```

The active scraper processes were stopped on request. The interrupted extra scrape batch was not counted in the DB because the Scrapy adapter inserts only after a crawl finishes cleanly.

## Problem Statement Targets

The attached PS says the pipeline must solve five linked problems:

```text
PS-1: Data source heterogeneity
PS-2: Schema and format inconsistency
PS-3: Ingredient name ambiguity
PS-4: Unit of measure inconsistency
PS-5: Data quality and validation gap
```

It also states:

```text
Initial target: 204 validated recipes
Scale target: 5,000+ recipes
Source types: CSV, web, video, audio, PDF, plain text, images
```

Current status against volume:

```text
204 validated recipe target: exceeded
5,000+ recipe scale target: exceeded with 6,496 v3 rows
2,000 live web-scraped rows: not complete yet, currently 1,095
```

## Architecture Walkthrough

The pipeline has these major layers:

```text
Source Adapter Layer
  -> RawRecord contract
  -> Schema Coercion
  -> Enrichment
  -> UOM Normalization
  -> Validation
  -> Database Persistence
  -> Embeddings / pgvector
  -> Reports / Observability
```

## PS-1: Source Adapter Layer

Key files:

```text
services/ingestion/source_adapter.py
services/ingestion/raw_record.py
services/ingestion/source_registry.py
services/ingestion/csv_adapter.py
services/ingestion/web_adapter.py
services/ingestion/scrapy_adapter.py
services/ingestion/youtube_adapter.py
services/ingestion/pdf_adapter.py
services/ingestion/audio_adapter.py
services/ingestion/image_adapter.py
services/ingestion/text_adapter.py
configs/production_recipe_sources.json
```

`SourceAdapter` is the common abstraction. Every source adapter implements:

```python
extract()
validate_config()
build_raw_record()
```

`RawRecord` is an immutable dataclass. It stores:

```text
record_id
source_id
source_type
raw_content
metadata
ingested_at
```

The immutability is important because downstream stages should not mutate raw evidence. The implementation freezes dicts and lists through mapping proxies and tuples.

`SourceRegistry` maps source configs to adapter classes. It supports:

```text
csv
dataset
web
scrapy
youtube
pdf
audio
image
text
```

It can load JSON or YAML configs and supports hot reload through either `watchdog` or polling.

Current PS-1 status:

```text
R1.1 SourceAdapter ABC: complete
R1.2 immutable RawRecord: complete
R1.3 registry hot reload: implemented
R1.4 UUID per RawRecord: complete
R1.5 adapter error isolation: implemented in SourceRegistry.run_all
```

## PS-2: Schema Coercion

Key files:

```text
services/preprocessing/schema_coercer.py
services/preprocessing/field_mapping.py
services/preprocessing/schema_models.py
services/preprocessing/schema_registry.py
services/preprocessing/schema_validator.py
configs/source_field_mappings.json
configs/schemas/recipe/v1.json
```

`SchemaCoercer` converts heterogeneous raw records into a canonical recipe shape. It handles source-specific field names, defaults, explicit nulls, unmapped field preservation, ingredient parsing, and step parsing.

Important behavior:

```text
Raw input field "name" or "title" maps to canonical title/name.
Ingredients can be list, dict, pipe-delimited, or text section.
Steps can be list, dict, pipe-delimited, or text section.
Unmapped source fields go into metadata.unmapped.
Invalid records are routed to a dead-letter payload.
```

The canonical model includes:

```text
title/name
description
nutrition_info
tags
servings
course/cuisine/region/state
diet and diet tags
prep/cook/total time
ingredients
steps
source metadata
```

Current PS-2 status:

```text
R2.1 field mapping config: implemented
R2.2 unmapped fields preserved: implemented
R2.3 schema validation/dead-letter: implemented
R2.4 explicit null fields: implemented in canonical shape
R2.5 coercion idempotency: covered by tests
```

## Web Scraping and v3 Catalogue Loading

Key files:

```text
services/acquisition/scrape_catalogue_v3_web.py
services/ingestion/scrapy_adapter.py
services/ingestion/web_scraper/spiders/recipe_crawl_spider.py
services/ingestion/web_scraper/parsers/schema_org_recipe_parser.py
services/database/catalogue_v3_loader.py
db/catalogue_v3/01_create_recipe_catalogue_v3.sql
```

The v3 web scraper flow is:

```text
1. Load source from configs/production_recipe_sources.json.
2. Apply runtime crawl overrides such as max_items, max_pages, max_depth.
3. Build ScrapyAdapter from SourceRegistry.
4. Crawl pages with RecipeCrawlSpider.
5. Parse schema.org Recipe JSON-LD and recipe-card HTML.
6. Convert each RawRecord into recipe_catalogue_v3 payload.
7. Reject rows missing source URL, servings, ingredients, or cook steps.
8. Deduplicate by metadata.source_url and metadata.content_hash.
9. Insert accepted payloads into PostgreSQL.
```

The v3 loader stores only source-backed fields. It does not generate fake recipe text.

Important v3 fields now populated from real sources where available:

```text
name
description
nutrition_info
tags
metadata.source_url
servings
image_url
course
cuisines
meal_types
prep_time_min
cook_time_min
total_time_min
ingredients_json
cook_steps
quick_steps
source
language
```

Fields like `diet`, `difficulty_level`, `cost_tier`, `dish_family`, and `meal_role` are deterministic enrichment fields, not source text.

## PS-3: Ingredient Resolution

Key files:

```text
services/enrichment/ingredient_resolution/alias_resolver.py
services/enrichment/ingredient_resolution/embedding_resolver.py
services/enrichment/ingredient_resolution/ingredient_resolver.py
services/enrichment/ingredient_resolution/llm_resolver.py
services/database/ingredient_repository.py
services/database/seed_master_ingredients.py
db/schemas/02_master_tables.sql
db/schemas/05_embeddings.sql
```

Resolution cascade:

```text
Tier 1: database alias exact match
Tier 1 fallback: local alias resolver
Tier 2: pgvector embedding search
Tier 3: LLM escalation when enabled
Fallback: unresolved_ingredient flag
```

The resolver returns structured metadata:

```text
raw_name
normalized_name
canonical_name
master_ingredient_id
method
tier
confidence_score
enrichment_flags
llm_metadata when used
```

Current PS-3 status:

```text
R3.1 master catalogue seeded: implemented
R3.2 pgvector search: implemented and tested
R3.3 LLM escalation with counters: implemented
R3.4 unresolved ingredients do not block: implemented
R3.5 curator alias write-back: partially implemented at repository/script level, still needs review workflow integration
```

Remaining PS-3 gap:

```text
Measure ingredient resolution rate on the full latest v3 dataset.
Complete curator UI/API workflow for alias correction write-back.
Scale master ingredient catalogue quality beyond initial seed.
```

## PS-4: UOM Normalization

Key files:

```text
services/enrichment/uom/uom_normalizer.py
services/enrichment/uom/density_table.py
services/preprocessing/ingredient_parser.py
services/enrichment/catalogue_v3_enricher.py
```

The UOM normalizer handles:

```text
metric weight: g, kg, mg
imperial weight: oz, lb
volume: ml, l, tsp, tbsp, cup
Indian colloquial units: katori, glass, bowl
count units: piece, clove, slice, inch, leaf, sprig
colloquial estimates: pinch, handful
unquantified: to taste, as needed
density-based volume to mass conversion
```

Every enriched ingredient can include:

```text
raw_text
name
quantity
unit
canonical_quantity
canonical_unit
normalized_text
conversion_method
conversion_factor
uom_confidence_score
normalization_flags
```

Current PS-4 status:

```text
R4.1 canonical units normalized: implemented
R4.2 density table: implemented, but should be expanded further
R4.3 UOM conflict flagging: implemented through flags
R4.4 colloquial estimates: implemented for pinch/handful and several Indian units
R4.5 conversion factor stored: implemented
```

Remaining PS-4 gap:

```text
Expand density table to cover the true top 200 ingredients by latest production frequency.
Add more Indian household units such as bowl variants, ladle, small cup, large cup, and regional measures.
```

## Catalogue v3 Enrichment

Key files:

```text
services/enrichment/catalogue_v3_enricher.py
scripts/enrich_catalogue_v3.py
tests/test_catalogue_v3_enricher.py
```

This is the deterministic enrichment pass for the new recipe schema. It does not generate instructions or fake descriptions. It enriches only structured metadata and normalized fields.

It currently handles:

```text
ingredient parsing
canonical units
normalized ingredient text
allergen tags
diet tags
difficulty level
complexity
cost tier
budget band
dish type
dish family
meal role
health tags
efficiency tags
state/region classification when confident
```

Important fix completed today:

```text
Diet classification no longer reads the source_id.
```

Before the fix, a source id like `indianhealthyrecipes_chicken_web` could falsely influence diet classification. Now diet is inferred only from actual recipe title, description, tags, course, cuisine, meal type, and ingredients.

Regression tests added:

```text
test_catalogue_v3_enricher_does_not_infer_diet_from_source_id
test_catalogue_v3_enricher_does_not_mark_dairy_recipe_vegan
```

## PS-5: Validation Engine

Key files:

```text
services/validation/validation_engine.py
services/validation/validation_result.py
services/validation/severity.py
services/database/validation_repository.py
configs/validation_checks.json
db/schemas/04_validation_tables.sql
```

The validation engine implements 11 checks:

```text
V01 Schema Completeness
V02 Ingredient Count Bounds
V03 Step Count Minimum
V04 Quantity Sanity
V05 Allergen Consistency
V06 UOM Conflict
V07 Nutrition Plausibility
V08 Enrichment Score
V09 Duplicate Guard
V10 Language Consistency
V11 Image Availability
```

Severity routing:

```text
CRITICAL -> REJECT
HIGH -> REVIEW
MEDIUM -> FLAG
LOW -> WARN
```

Current PS-5 status:

```text
Validation checks implemented.
Dead-letter/review/accepted persistence implemented.
Duplicate guard implemented.
Validation reports can be stored in DB.
Alerting and Prometheus metrics exist.
```

Remaining PS-5 gap:

```text
Run validation reports over the latest full v3 catalogue and export the final acceptance/review/reject KPI report.
Make the human review queue easier to inspect and correct.
```

## Observability and Reliability

Key files:

```text
services/observability/metrics.py
services/observability/prometheus.py
services/observability/alerts.py
services/reliability/retry.py
services/api/main.py
```

Implemented:

```text
Prometheus metrics endpoint support
pipeline metrics calculation
Slack-style alert hook support
retry utilities with tenacity
FastAPI endpoint tests
```

Remaining:

```text
Document production deployment metrics and alert thresholds.
```

## Database Layer

Key files:

```text
services/database/catalogue_v3_connection.py
services/database/catalogue_v3_loader.py
services/database/recipe_loader.py
services/database/ingredient_repository.py
services/database/recipe_embedding_loader.py
services/database/ingestion_run_repository.py
services/database/validation_repository.py
```

Important DB features:

```text
PostgreSQL-backed catalogue
recipe_catalogue_v3 full schema
master ingredient table
alias lookup
pgvector embeddings
recipe embeddings
ingestion run tracking
validation persistence
review queue and dead-letter support
state/region views
duplicate/source URL/content hash checks
```

## Current Scraping Status

Completed and loaded live web sources:

```text
veg_recipes_of_india_web:           605
hebbars_kitchen_web:                151
indianhealthyrecipes_egg_web:       110
indianhealthyrecipes_chicken_web:    83
scrapy_indianhealthyrecipes:         68
whiskaffair_web:                     54
indianhealthyrecipes_vegan_web:      24
```

Blocked or low-yield sources observed:

```text
NDTV Food: returned 403
Times Food: configured URL returned 404
Sanjeev Kapoor: configured URL returned 404
BigBasket: configured URL returned 404
Archana's Kitchen: crawled but yielded 0 recipe items with current parser
Indian Express: crawled but yielded 0 recipe items with current parser
Tarla Dalal: yielded slowly but was stopped before clean ingest
```

Important note:

```text
Interrupted scrapes are not counted in PostgreSQL because the current ScrapyAdapter collects records in memory and loads them only after extract() returns cleanly.
```

## Tests

Current test coverage includes:

```text
source adapter contracts
schema coercion
schema registry and validation
ingredient parsing
ingredient alias resolution
embedding resolver
LLM resolver
UOM normalizer
validation engine
validation alerts
pgvector
recipe embeddings
loader/search flow
catalogue v3 loader
catalogue v3 web scrape loader
catalogue v3 enricher
schema.org parser
Prometheus metrics
API endpoints
```

Latest confirmed full suite:

```text
117 passed, 1 warning
```

## What Is Finished Against PS-1 to PS-5

PS-1 status:

```text
Mostly complete.
Adapters exist for all required source types.
RawRecord contract exists.
Registry exists.
Hot reload exists.
Multi-source support exists.
```

PS-2 status:

```text
Mostly complete.
Schema coercion exists.
Canonical model exists.
Field mappings exist.
Unmapped preservation exists.
Dead-letter routing exists.
```

PS-3 status:

```text
Strong implementation.
Alias resolver exists.
DB alias lookup exists.
Embedding resolver exists.
LLM resolver exists.
Unresolved ingredient behavior exists.
Needs stronger measured resolution KPI and curator workflow polish.
```

PS-4 status:

```text
Strong implementation.
Canonical unit normalization exists.
Density conversion exists.
Colloquial units exist.
Conversion factor is stored.
Needs expanded density/colloquial table.
```

PS-5 status:

```text
Strong implementation.
11 validation checks exist.
Severity routing exists.
DB persistence exists.
Review/dead-letter concepts exist.
Needs final full-catalogue KPI report and review workflow polish.
```

## What Remains

Highest-priority remaining work:

```text
1. Reach 2,000 live web-scraped recipes if that is now a hard requirement.
2. Add source-specific parsers for Archana's Kitchen, Tarla Dalal, Indian Express, Sanjeev Kapoor, and/or NDTV.
3. Run validation over all 6,496 v3 rows and export acceptance/review/reject KPI.
4. Run ingredient resolution KPI over all latest rows.
5. Expand density table to top 200 ingredients by latest frequency.
6. Add manual review workflow for alias corrections and validation queue.
7. Export final reviewer-facing CSV from PostgreSQL after latest stable ingest.
8. Add deployment evidence: Docker/compose verification, health check output, backup/export process.
```

Important data remaining:

```text
Total v3 recipes already exceed the PS scale target of 5,000+.
Live web-scraped recipes are at 1,095, so 905 more web rows are needed for a 2,000 web-only target.
```

## Recommended Next Step

Do not continue broad crawling blindly. The most efficient path to 2,000 web rows is:

```text
1. Build source-specific parsers for the blocked/low-yield websites.
2. Change ScrapyAdapter to stream accepted items into DB during crawl or checkpoint accepted payloads.
3. Resume large crawls only after streaming persistence is added, so stopping a crawl does not lose buffered records.
4. Prefer sources with schema.org Recipe JSON-LD and verified English recipe pages.
```

This will make the next scraping session faster, safer, and more production-grade.
