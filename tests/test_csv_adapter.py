from services.ingestion.csv_adapter import CSVAdapter


adapter = CSVAdapter(

    "sample_recipes.csv"

)


adapter.extract()


adapter.transform()


adapter.load()