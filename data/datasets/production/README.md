# Production Recipe Dataset Export

This folder contains reviewer-facing exports from the PostgreSQL production
tables.

- `real_web_recipes_3883_20260710.csv`: 3,883 real webpage recipes exported
  from PostgreSQL after adding Yummy Tummy Aarthi crawling, validation,
  ingredient-resolution backfill, and pgvector recipe embedding backfill.
- `real_dataset_recipes_6559_20260712.csv`: 6,559 structured-dataset-attributed
  Indian recipes exported from PostgreSQL after ingesting the public
  `kanishk307/IndianFoodDatasetGeneration` Archana's Kitchen dataset plus the
  earlier local structured dataset rows. Invalid localized/no-ingredient rows
  were pruned after quality cleanup. Each row has source provenance,
  ingredients, step count, and full one-line instructions.
- `real_dataset_recipes_50_20260712.csv`: 50 structured-dataset-attributed
  earlier dataset export kept for comparison before the Archana's Kitchen
  dataset batch.
- `real_web_recipes_3080_20260709.csv`: earlier 3,080 real webpage export
  from PostgreSQL after Indian Healthy Recipes, Hebbars Kitchen, and Veg
  Recipes of India crawling, validation, ingredient-resolution backfill, and
  pgvector recipe embedding backfill.
- `real_web_recipes_1629_20260708.csv`: earlier 1,629-row webpage export after
  Indian Healthy Recipes plus Hebbars Kitchen crawling, parser cleanup, and
  localized-page pruning.
- `real_web_recipes_903_20260707.csv`: earlier 903-row webpage export after
  the depth-3 and depth-5 Indian Healthy Recipes crawls.
- `real_web_recipes_501_20260706.csv`: earlier 501-row real webpage export
  kept for comparison.
- Each row includes source URL, state/region classification, ingredient
  measurements, ingredient names, step count, and full one-line instructions.
- This is different from files under `data/datasets/generated/`, which are
  local fixtures or scrape checkpoints.

Regenerate the CSV with:

```bash
python -m services.reports.export_production_web_recipes --output data/datasets/production/real_web_recipes_3883_20260710.csv
python -m services.reports.export_production_dataset_recipes --output data/datasets/production/real_dataset_recipes_6559_20260712.csv
```
