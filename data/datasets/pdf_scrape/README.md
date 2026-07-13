# PDF Recipe Scrape Export

This folder contains the reviewer-facing output from public/open PDF cookbook
OCR sources.

- `normalized_pdf_recipes.csv`: 1,000 parsed PDF-derived Indian/Anglo-Indian
  recipe records loaded into PostgreSQL as `source_type = pdf`.
- `pdf_sources.json`: source provenance, including Internet Archive identifiers,
  PDF URLs, local OCR cache paths, and parsed counts.

The local OCR cache lives in `data/datasets/pdf_scrape/raw_text/` and is ignored
to avoid committing large intermediate text files. Rebuild the CSV with:

```bash
python -m services.acquisition.pdf_recipe_scraper --collect-local --max-recipes 1000
```

Load it with:

```bash
python -m services.acquisition.pdf_recipe_scraper --ingest --ingest-path data/datasets/pdf_scrape/normalized_pdf_recipes.csv
```
