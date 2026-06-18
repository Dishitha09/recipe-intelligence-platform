from services.acquisition.dataset_ingestor import DatasetIngestor


ingestor = DatasetIngestor()


data = ingestor.ingest_folder(

    "data/datasets"

)


print(

    len(data)

)