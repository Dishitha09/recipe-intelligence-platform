import pandas as pd

from services.ingestion.source_adapter import SourceAdapter

from services.ingestion.raw_writer import save_raw_record



class CSVAdapter(SourceAdapter):
    source_type = "csv"


    def __init__(self, file_path, source_id="csv.default", config=None):

        self.file_path = file_path

        self.df = None
        self.raw_records = []

        super().__init__(source_id=source_id, config=config)


    def validate_config(self):

        super().validate_config()

        if not self.file_path:
            raise ValueError("file_path is required")



    def extract(self):

        self.df = pd.read_csv(self.file_path).fillna("")

        self.raw_records = []

        for row_number, row in enumerate(
            self.df.to_dict(orient="records"),
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

        if self.df is None:
            self.extract()

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

        return self.raw_records or self.extract()
