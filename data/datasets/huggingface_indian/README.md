# Hugging Face Indian Recipe Datasets

This folder contains source-truth normalized dataset exports used by the
production ingestion pipeline.

- `processed/anupam007_indian_recipe_dataset_normalized.csv`: normalized from
  `Anupam007/indian-recipe-dataset`.
- `processed/nileshiq_indian_food_normalized.csv`: normalized from
  `nileshiq/Indian-Food`, preserving source-provided prep time, cook time,
  total time, servings, cuisine, course, diet, ingredients, steps, and URL.

Raw downloaded files are intentionally kept out of git by `.gitignore` because
they are larger source mirrors. Regenerate processed files with:

```bash
python -m services.acquisition.normalize_huggingface_indian_dataset
```
