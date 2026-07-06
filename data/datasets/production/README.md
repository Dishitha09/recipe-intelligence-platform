# Production Recipe Dataset Export

This folder contains reviewer-facing exports from the PostgreSQL production
tables.

- `real_web_recipes_501_20260706.csv`: 501 real webpage recipes exported from
  PostgreSQL after ingestion through the ShopConnect pipeline.
- Each row includes source URL, state/region classification, ingredient
  measurements, ingredient names, step count, and full one-line instructions.
- This is different from files under `data/datasets/generated/`, which are
  local fixtures or scrape checkpoints.

Regenerate the CSV with:

```bash
python -m services.reports.export_production_web_recipes --output data/datasets/production/real_web_recipes_501_20260706.csv
```
