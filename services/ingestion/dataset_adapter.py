from services.ingestion.source_adapter import SourceAdapter

import pandas as pd

import os



class DatasetAdapter(SourceAdapter):


    def __init__(self,file_path):

        self.file_path=file_path



    def extract(self):


        if not os.path.exists(self.file_path):

            raise FileNotFoundError(


                f"{self.file_path} not found"

            )


        return pd.read_csv(

            self.file_path

        )



    def transform(self):


        df=self.extract()


        records=[]


        for _,row in df.iterrows():


            records.append(

                {

                    "source_type":"dataset",

                    "source_url":None,

                    "raw_text":str(row.to_dict()),

                    "metadata":{},

                    "raw_path":self.file_path

                }

            )


        return records



    def load(self):


        return self.transform()