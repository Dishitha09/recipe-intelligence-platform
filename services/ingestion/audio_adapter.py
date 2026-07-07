from services.ingestion.source_adapter import SourceAdapter

import os


def _first_nonempty_line(text):
    for line in str(text or "").splitlines():
        line = line.strip()
        if line:
            return line

    return None


def _read_text(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()


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

        transcript_path = self.config.get("transcript_path")
        transcript_text = self.config.get("transcript_text")
        transcription_status = "not_transcribed"

        if transcript_text:
            raw_text = str(transcript_text).strip()
            transcription_status = "inline_config"
        elif transcript_path:
            raw_text = _read_text(transcript_path)
            transcription_status = "sidecar_file"
        else:
            raw_text = ""

        title = self.config.get("title") or _first_nonempty_line(raw_text)
        source_url = self.config.get("source_url")

        self.raw_records = [
            self.build_raw_record(
                {
                    "title": title,
                    "raw_text": raw_text,
                    "source_url": source_url,
                },
                metadata={
                    "filename": os.path.basename(self.file_path),
                    "raw_path": self.file_path,
                    "transcription_status": transcription_status,
                    "transcript_path": transcript_path,
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
