from services.ingestion.source_adapter import SourceAdapter

import os


class TextAdapter(SourceAdapter):
    source_type = "text"


    def __init__(self, file_path, source_id="text.default", config=None):

        self.file_path = file_path
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


        with open(

            self.file_path,

            "r",

            encoding="utf-8"

        ) as f:


            text = f.read()

        title = next(
            (
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ),
            None
        )

        self.raw_records = [
            self.build_raw_record(
                {
                    "title": title,
                    "raw_text": text,
                    "source_url": None,
                },
                metadata={
                    "filename": os.path.basename(self.file_path),
                    "raw_path": self.file_path,
                }
            )
        ]

        return self.raw_records



    def transform(self):


        records = self.raw_records or self.extract()

        text = records[0].raw_content["raw_text"]


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


        return self.raw_records or self.extract()
