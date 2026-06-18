from services.ingestion.dataset_scanner import DatasetScanner


scanner = DatasetScanner()


files = scanner.scan(

    "data/datasets"

)


print(files)