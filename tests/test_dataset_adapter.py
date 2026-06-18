from services.ingestion.dataset_adapter import DatasetAdapter


adapter=DatasetAdapter(

    "data/datasets/sample_dataset.csv"

)


records=adapter.load()


print(

    len(records)

)


print(

    records[0]

)