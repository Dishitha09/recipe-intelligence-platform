# Production Recipe Dataset Export

This folder contains reviewer-facing exports from the PostgreSQL production
tables.

- `real_web_recipes_903_20260707.csv`: 903 real webpage recipes exported from
  PostgreSQL after the depth-3 and depth-5 Indian Healthy Recipes crawls.
- `real_web_recipes_501_20260706.csv`: earlier 501-row real webpage export
  kept for comparison.
- Each row includes source URL, state/region classification, ingredient
  measurements, ingredient names, step count, and full one-line instructions.
- This is different from files under `data/datasets/generated/`, which are
  local fixtures or scrape checkpoints.

Regenerate the CSV with:

```bash
python -m services.reports.export_production_web_recipes --output data/datasets/production/real_web_recipes_903_20260707.csv
```
