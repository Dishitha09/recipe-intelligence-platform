import pandas as pd


class DatasetLoader:


    def __init__(self, file_path):

        self.file_path = file_path



    def load(self):


        if self.file_path.endswith(".csv"):


            return pd.read_csv(

                self.file_path

            )



        raise Exception(

            "Unsupported Dataset Format"

        )