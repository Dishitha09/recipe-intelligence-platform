from services.ingestion.dataset_loader import DatasetLoader


loader=DatasetLoader(

    "data/datasets/sample_dataset.csv"

)


df=loader.load()


print(df.head())

print(

    len(df)

)