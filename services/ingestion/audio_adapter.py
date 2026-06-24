from services.ingestion.source_adapter import SourceAdapter

import os


class AudioAdapter(SourceAdapter):
    source_type = "audio"


    def __init__(self, file_path, source_id="audio.default", config=None):

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


        self.raw_records = [
            self.build_raw_record(
                {
                    "title": None,
                    "raw_text": "",
                    "source_url": None,
                },
                metadata={
                    "filename": os.path.basename(self.file_path),
                    "raw_path": self.file_path,
                    "transcription_status": "not_transcribed",
                }
            )
        ]

        return self.raw_records



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


        return self.raw_records or self.extract()
