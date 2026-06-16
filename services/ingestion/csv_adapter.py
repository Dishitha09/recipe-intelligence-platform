import pandas as pd

from services.ingestion.source_adapter import SourceAdapter

from services.ingestion.raw_writer import save_raw_record



class CSVAdapter(SourceAdapter):


    def __init__(self, file_path):

        self.file_path = file_path

        self.df = None



    def extract(self):

        self.df = pd.read_csv(self.file_path)

        return self.df



    def transform(self):


        records = self.df.to_dict(

            orient="records"

        )


        for row in records:


            save_raw_record(

                row,

                "csv"

            )


        return records



    def load(self):

        print("Raw CSV Saved")