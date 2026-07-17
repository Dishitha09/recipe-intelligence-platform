# Catalogue V3 Pipeline Automation

This project can now run the real webpage recipe pipeline as one repeatable
command:

1. Select approved sources from `configs/production_recipe_sources.json`.
2. Scrape source recipe pages.
3. Load new rows into `recipe_catalogue_v3`.
4. Skip duplicates by `metadata.source_url` and `metadata.content_hash`.
5. Run deterministic enrichment and normalization.
6. Backfill source-provided nutrition where recipe pages expose it.
7. Write an automation summary JSON file.
8. Track the ingestion run when the `ingestion_runs` table is available.

## Manual Run

Run one approved source:

```bash
python -m scripts.run_catalogue_v3_pipeline \
  --source-id indianhealthyrecipes_chicken_web \
  --max-items 100 \
  --max-pages 300 \
  --max-depth 3 \
  --allow-disabled
```

Run all enabled web sources in the registry:

```bash
python -m scripts.run_catalogue_v3_pipeline
```

Run a controlled source group:

```bash
python -m scripts.run_catalogue_v3_pipeline \
  --source-group structured_html \
  --allow-disabled \
  --max-items 250 \
  --max-pages 500 \
  --max-depth 3
```

Dry run without DB inserts/updates:

```bash
python -m scripts.run_catalogue_v3_pipeline \
  --source-id hebbars_kitchen_web \
  --allow-disabled \
  --max-items 25 \
  --dry-run
```

## Daily Automation

On Windows Task Scheduler, create a task that runs:

```text
Program: powershell.exe
Arguments: -NoProfile -ExecutionPolicy Bypass -Command "cd C:\Projects\recipe-intelligence-platform; .\.venv\Scripts\python.exe -m scripts.run_catalogue_v3_pipeline --source-group structured_html --allow-disabled --max-items 250 --max-pages 500 --max-depth 3"
```

For a production scheduler, prefer smaller frequent runs over one huge crawl.
Example: run every 6 hours with `--max-items 100` to reduce failed/partial
crawl risk and keep source traffic polite.

## Outputs

Automation artifacts are written to:

```text
data/datasets/catalogue_v3/automated_runs/
```

Each run creates:

- one CSV per source with scraped payloads
- one `.partial.csv` checkpoint per active crawl
- one `catalogue_v3_pipeline_<timestamp>.json` run summary

## Idempotency

The loader checks:

- `metadata->>'source_url'`
- `metadata->>'content_hash'`

If the recipe already exists, the pipeline skips it by default. Add
`--update-existing` only when the source is trusted and you want to refresh
existing source-provided fields such as image, ingredients, steps, and timing.

## What Still Needs Hardening

The current Scrapy adapter returns rows after a clean crawl finish. For very
large unattended crawls, the next improvement should be streaming ingestion
from checkpoints so an interrupted crawl can still load the rows already seen.
