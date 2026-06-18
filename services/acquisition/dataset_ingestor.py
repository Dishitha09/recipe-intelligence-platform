from services.ingestion.dataset_scanner import DatasetScanner

from services.ingestion.dataset_loader import DatasetLoader



class DatasetIngestor:


    def ingest_folder(self, folder):


        scanner = DatasetScanner()


        files = scanner.scan(folder)


        all_data = []


        for file in files:


            if file.endswith(".csv"):


                loader = DatasetLoader(file)


                df = loader.load()


                all_data.append(df)


        return all_data