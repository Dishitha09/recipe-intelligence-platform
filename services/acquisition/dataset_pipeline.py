from configs.dataset_registry import DATASETS

from services.acquisition.dataset_ingestor import DatasetIngestor



class DatasetPipeline:


    def __init__(self):


        self.ingestor=DatasetIngestor()



    def run(self):


        for name,config in DATASETS.items():


            print(


                f"Ingesting : {name}"

            )


            data=self.ingestor.ingest_folder(


                config["folder"]

            )


            print(


                f"Loaded : {len(data)} files"

            )