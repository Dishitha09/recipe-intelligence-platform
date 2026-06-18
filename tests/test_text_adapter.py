from services.ingestion.text_adapter import TextAdapter


adapter = TextAdapter(

    "sample_recipe.txt"

)


print(

    adapter.extract()

)


print(

    adapter.transform()

)