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

✓ FastAPI Skeleton

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
