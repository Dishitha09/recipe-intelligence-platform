from services.ingestion.source_adapter import SourceAdapter

import pandas as pd

import os



class DatasetAdapter(SourceAdapter):
    source_type = "dataset"


    def __init__(self,file_path, source_id="dataset.default", config=None):

        self.file_path=file_path
        self.raw_records = []

        super().__init__(source_id=source_id, config=config)


    def validate_config(self):

        super().validate_config()

        if not self.file_path:
            raise ValueError("file_path is required")



    def extract(self):


        if not os.path.exists(self.file_path):

            raise FileNotFoundError(


                f"{self.file_path} not found"

            )


        df = pd.read_csv(

            self.file_path

        ).fillna("")

        self.raw_records = []

        for row_number, row in enumerate(
            df.to_dict(orient="records"),
            start=1
        ):
            self.raw_records.append(
                self.build_raw_record(
                    dict(row),
                    metadata={
                        "file_path": self.file_path,
                        "row_number": row_number,
                    }
                )
            )

        return self.raw_records



    def transform(self):


        records=self.raw_records or self.extract()


        transformed=[]


        for record in records:


            transformed.append(

                {

                    "source_type":"dataset",

                    "source_url":None,

                    "raw_text":str(record.raw_content),

                    "metadata":{},

                    "raw_path":self.file_path

                }

            )


        return transformed



    def load(self):


        return self.raw_records or self.extract()
