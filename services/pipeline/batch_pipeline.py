import pandas as pd

from services.pipeline.recipe_pipeline import RecipePipeline


class BatchPipeline:


    def __init__(self):

        self.pipeline = RecipePipeline()


    def run(

        self,

        file_path,

        chunk_size=500

    ):


        for chunk in pd.read_csv(

            file_path,

            chunksize=chunk_size

        ):


            temp_file = "temp_chunk.csv"


            chunk.to_csv(

                temp_file,

                index=False

            )


            self.pipeline.run_csv_pipeline(

                temp_file

            )


            print(

                f"Processed {len(chunk)} recipes"

            )