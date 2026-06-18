from services.ingestion.source_adapter import SourceAdapter

import os


class AudioAdapter(SourceAdapter):


    def __init__(self, file_path):

        self.file_path = file_path



    def extract(self):


        if not os.path.exists(self.file_path):

            raise FileNotFoundError(

                f"{self.file_path} not found"

            )


        return self.file_path



    def transform(self):


        return {

            "source_type": "audio",

            "source_url": None,

            "raw_text": "",

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