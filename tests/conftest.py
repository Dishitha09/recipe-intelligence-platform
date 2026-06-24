collect_ignore = [
    # Database integration smoke scripts. Run after Postgres is available.
    "test_bulk_recipe_loader.py",
    "test_embedding_loader.py",
    "test_dataset_ingestor.py",
    "test_dataset_pipeline.py",
    "test_embedding_generator.py",
    "test_recipe_ingredients_schema.py",
    "test_recipe_lookup.py",
    "test_single_recipe_ingredient_ingestion.py",
    "test_first_recipe.py",

    # External network, scraper, and parser smoke scripts.
    "test_recipe_parser.py",
    "test_scrapy_spider.py",
    "test_url_collector.py",

    # LLM/RAG/model integration smoke scripts.
    "test_embedding_service.py",
    "test_gemini.py",
    "test_llm_service.py",
    "test_recipe_assistant.py",
    "test_recipe_chat.py",
    "test_recipe_rag.py",
    "test_recipe_retriever.py",
    "test_recipe_vector_search.py",
    "test_semantic_search.py",
]
