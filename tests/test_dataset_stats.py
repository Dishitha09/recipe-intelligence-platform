from services.acquisition.dataset_stats import DatasetStats


stats = DatasetStats()


print(

stats.count_csv_files(

"data/datasets"

)

)