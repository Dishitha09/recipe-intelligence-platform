from services.ingestion.source_adapter import SourceAdapter

import os


class TextAdapter(SourceAdapter):


    def __init__(self, file_path):

        self.file_path = file_path



    def extract(self):


        if not os.path.exists(self.file_path):

            raise FileNotFoundError(

                f"{self.file_path} not found"

            )


        with open(

            self.file_path,

            "r",

            encoding="utf-8"

        ) as f:


            return f.read()



    def transform(self):


        text = self.extract()


        return {

            "source_type": "text",

            "source_url": None,

            "raw_text": text,

            "metadata": {

                "filename":

                os.path.basename(

                    self.file_path

                )

            },

            "raw_path":

            self.file_path

        }



    def load(self):


        return self.transform()