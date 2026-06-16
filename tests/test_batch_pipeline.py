from services.pipeline.batch_pipeline import BatchPipeline


pipeline = BatchPipeline()


pipeline.run(

    "sample_recipes.csv",

    chunk_size=2

)