# IndianFoodDatasetGeneration Import

Source: `kanishk307/IndianFoodDatasetGeneration`

Repository: https://github.com/kanishk307/IndianFoodDatasetGeneration

Downloaded file:

- `IndianFoodDatasetCSV.csv`

Normalized file:

- `archanas_kitchen_recipes_normalized.csv`

The source repository describes this as a 6000+ Indian recipe dataset created
from Archana's Kitchen. The normalizer keeps only rows with title, ingredients,
instructions, and source URL, then converts ingredients and instructions into
the pipe-delimited format used by the ShopConnect ingestion pipeline.

Regenerate normalized data:

```bash
python -m services.acquisition.normalize_archanas_dataset
```
