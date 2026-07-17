# Recipe Intelligence Platform

## 1. Project Overview

The Recipe Intelligence Platform is a production-oriented NLP and AI pipeline designed to ingest recipes from heterogeneous data sources, standardize them into a canonical schema, enrich ingredient information, store structured recipe knowledge, and provide intelligent retrieval using Vector Search, RAG (Retrieval-Augmented Generation), and Large Language Models.

The project is built to address the ShopConnect Recipe Pipeline problem statement covering:

* PS-1 : Source Heterogeneity
* PS-2 : Schema and Format Inconsistency
* PS-3 : Ingredient Name Ambiguity
* PS-4 : Unit of Measure Inconsistency
* PS-5 : Validation and Data Quality

---

## 2. Project Objectives

The platform aims to:

1. Ingest recipes from multiple source formats.
2. Normalize recipes into a common schema.
3. Resolve ingredient ambiguities using NLP and embeddings.
4. Normalize measurement units.
5. Validate recipe quality before storage.
6. Store structured recipes in PostgreSQL.
7. Generate embeddings using Sentence Transformers.
8. Perform semantic recipe search using pgvector.
9. Build a Retrieval Augmented Generation (RAG) pipeline.
10. Generate intelligent recipe answers using Gemini.

---

## 3. System Architecture

Data Sources

CSV

Web Pages

PDF Documents (Planned)

YouTube Videos (Planned)

Audio Files (Planned)

Images (Planned)

↓

Source Adapters

↓

Recipe Parsing

↓

Schema Coercion

↓

Ingredient NLP

↓

Ingredient Resolution

↓

UOM Normalization

↓

Validation Engine

↓

PostgreSQL

recipes

recipe_ingredients

recipe_steps

recipe_embeddings

↓

Sentence Transformers

↓

pgvector

↓

Vector Search

↓

RAG

↓

Gemini LLM

↓

FastAPI

↓

Recipe Intelligence API

---

## 4. Technical Stack

### Programming Language

Python 3.13

---

### Backend Framework

FastAPI

---

### Database

PostgreSQL

Extensions:

* pgvector

---

### Web Scraping

Scrapy

BeautifulSoup4

Requests

---

### NLP

Sentence Transformers

all-MiniLM-L6-v2

Scikit-Learn

NumPy

Regex

---

### Vector Database

pgvector

Embedding Size:

384 Dimensions

---

### LLM

Google Gemini

Model:

Gemini Flash

---

### Validation

Pydantic

Custom Validation Rules

---

### API

FastAPI

Uvicorn

---

### Environment

Python Virtual Environment

Windows 11

Docker

Git

GitHub

---

## 5. Recipe Data Model

Recipe

* title
* description
* cuisine
* source_url
* language

Ingredients

* ingredient_name
* quantity
* unit
* preparation

Recipe Steps

* step_number
* instruction

---

## 6. Ingredient Resolution Strategy

The project follows a three-stage ingredient resolution pipeline.

Tier 1

Alias Resolution

Examples:

atta → whole_wheat_flour

besan → gram_flour

kabuli chana → chickpea

---

Tier 2

Embedding Similarity

Sentence Transformer embeddings

Cosine Similarity

Nearest Canonical Ingredient

---

Tier 3

LLM Resolution

Gemini suggests canonical ingredient

Human curator confirms

Knowledge base updated

---

## 7. Unit Normalization

Supported Units

Weight

* mg
* g
* kg

Volume

* tsp
* tbsp
* cup
* bowl
* katori
* glass

Indian Units

* pinch
* handful

Density Based Conversion

Examples:

Rice

1 cup → grams

Flour

1 bowl → grams

Milk

1 cup → ml

---

## 8. Vector Search

Recipe text is converted into embeddings using:

SentenceTransformer

all-MiniLM-L6-v2

Embedding Dimension:

384

Embeddings are stored in:

recipe_embeddings

using:

pgvector VECTOR(384)

Similarity Search:

Cosine Distance

Top K Retrieval

---

## 9. Retrieval Augmented Generation (RAG)

User Question

↓

Sentence Embedding

↓

pgvector Similarity Search

↓

Retrieve Top Recipes

↓

Context Builder

↓

Prompt Template

↓

Gemini

↓

Generated Answer

---

## 10. API Layer

Endpoints

GET /

Health Check

GET /recipes

Paginated recipe listing with search, state, region, source, and language filters.

GET /recipes/{recipe_id}

Recipe detail with ingredients, instructions, ratings, and source transparency.

POST /search

Advanced recipe search with optional rating filter.

GET /regions

State-wise and region-wise recipe coverage for the 10,000 recipe target.

GET /recipes/{recipe_id}/reviews

Ratings and reviews for one recipe.

POST /recipes/{recipe_id}/reviews

Idempotent review creation/update with automatic rating summary refresh.

GET /trending

Trending recipe list using stored or computed scores.

GET /metrics

Prometheus scrape endpoint with ingestion, validation, resolution,
dead-letter, latency, and LLM call metrics.

POST /ingredients/aliases

Curator write-back endpoint for corrected ingredient aliases.

POST /ask

Recipe Question Answering

Future:

POST /recommend

GET /similar/{id}

POST /ingredient-search

POST /image-recipe

---

## 11. Current Project Status

Implemented

✓ CSV Ingestion

✓ Web Scraping

✓ Recipe Parser

✓ Ingredient Parser

✓ Alias Resolver

✓ Embedding Resolver

✓ UOM Normalization

✓ PostgreSQL

✓ pgvector

✓ Sentence Embeddings

✓ Vector Search

✓ RAG

✓ Gemini Integration

✓ FastAPI recipe listing/search/detail/review API

Planned

* PDF Adapter

* YouTube Adapter

* Image Adapter

* Audio Adapter

* Advanced Validation

* Monitoring

* Image to Recipe

---

## 12. Design Philosophy

The project follows:

Modular Architecture

Adapter Pattern

Repository Pattern

Pipeline Architecture

RAG Architecture

Production-first Design

Every stage is independent and extensible, allowing new data sources, new LLMs, and new retrieval strategies to be integrated with minimal changes.

---

## 13. Final Goal

Build a production-grade Recipe Intelligence Platform capable of:

* Multi-source recipe ingestion
* NLP based ingredient understanding
* Semantic recipe retrieval
* Vector search
* RAG
* LLM powered recipe assistant
* API based deployment
* Future multimodal recipe intelligence

---

## 14. Production Bootstrap

Create a local environment file:

```bash
cp .env.example .env
```

For Docker Postgres with pgvector:

```bash
docker compose up -d postgres
python -m services.database.init_db
python -m services.database.seed_master_ingredients
```

If you are using a local pgAdmin/PostgreSQL database on port `5432`, update
`DATABASE_URL` in `.env` to match that database before running `init_db`.

Generate and ingest a deterministic 100-recipe fixture:

```bash
python -m services.acquisition.scaled_recipe_ingestion --count 100 --ingest
```

Run a controlled live scrape into PostgreSQL:

```bash
python -m services.acquisition.scrapy_recipe_ingestion --source-id scrapy_indianhealthyrecipes --allow-disabled --max-items 100 --max-pages 250 --ingest
```

Run the automated catalogue v3 scrape -> load -> enrich -> nutrition pipeline:

```bash
python -m scripts.run_catalogue_v3_pipeline --source-group structured_html --allow-disabled --max-items 250 --max-pages 500 --max-depth 3
```

See `docs/catalogue_v3_pipeline_automation.md` for scheduling and idempotency
details.

Refresh fuller instructions from real source pages when a site exposes short
recipe-card steps and longer article/photo-guide steps:

```bash
python -m services.acquisition.backfill_full_instructions --source-domain indianhealthyrecipes.com
```

Verify ingestion counts in PostgreSQL:

```sql
SELECT count(*) FROM recipes;
SELECT count(*) FROM recipe_ingredients;
SELECT count(*) FROM recipe_steps;
SELECT count(*) FROM recipe_instructions;
SELECT status, count(*) FROM validation_reports GROUP BY status;
SELECT run_id, source_id, status, records_found, records_loaded
FROM ingestion_runs
ORDER BY run_id DESC
LIMIT 10;
```

Verify vector indexes:

```sql
SELECT indexname
FROM pg_indexes
WHERE indexname IN (
  'idx_ingredient_embeddings_hnsw',
  'idx_recipe_embeddings_hnsw'
);
```

Scrape operational metrics:

```bash
curl http://localhost:8000/metrics
```

Curator alias write-back:

```bash
curl -X POST http://localhost:8000/ingredients/aliases \
  -H "Content-Type: application/json" \
  -d '{"canonical_name":"dry_mango_powder","alias_name":"amchoor","source":"curator"}'
```

Inspect recipe instructions with recipe context in pgAdmin:

```sql
SELECT recipe_id, title, source_url, step_number, instruction
FROM recipe_instruction_details
ORDER BY recipe_id, step_number
LIMIT 100;
```

Inspect one row per recipe with instructions in one cell:

```sql
SELECT recipe_id, title, step_count, instructions
FROM recipe_instruction_summary
ORDER BY recipe_id
LIMIT 100;
```

The loader is idempotent: rerunning the same source updates existing recipes
by `source_url_hash` or `content_hash` instead of creating duplicates.

Check state-wise coverage:

```bash
python -m services.acquisition.backfill_state_classification
python -m services.acquisition.statewise_catalog_report --target-total 10000
python -m services.acquisition.statewise_collection_plan
```

```sql
SELECT state, region, recipe_count, avg_state_confidence
FROM recipe_state_coverage
ORDER BY recipe_count DESC;
```

---

## 15. Production Readiness Checklist

Completed foundations:

* Source abstraction for CSV, web, Scrapy, dataset, PDF, image, audio, text, and YouTube adapters.
* Canonical schema coercion.
* Ingredient enrichment and UOM normalization.
* PostgreSQL persistence for recipes, ingredients, steps, validation reports, review queue, dead-letter queue, source tracking, and ingestion runs.
* pgvector recipe embeddings and vector-search integration tests.
* Idempotent recipe loading using source URL and content fingerprints.
* Gemini-backed Tier 3 ingredient resolution with LLM counters and cost tracking.
* Prometheus `/metrics` endpoint and Slack webhook hook for critical validation failures.
* HNSW vector indexes where supported by the installed pgvector extension.
* Curator alias write-back to improve future Tier 1 resolution.
* Retry/backoff wrapper for Gemini, embedding, recipe loading, validation persistence, and ingredient write paths.

Remaining scale work:

* Enable more live sources one by one after robots/access checks.
* Add domain-specific parsers for Times Food, NDTV, Sanjeev Kapoor, Indian Express, and regional blogs.
* Run controlled batches to 500, then 1000-5000 accepted recipes.
* Add Grafana dashboard panels on top of the Prometheus metrics endpoint.
* Build a curator UI on top of alias/UOM correction APIs.
