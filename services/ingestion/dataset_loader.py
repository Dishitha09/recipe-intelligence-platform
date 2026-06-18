import pandas as pd


class DatasetLoader:


    def __init__(self,file_path):

        self.file_path=file_path


    def load(self):


        return pd.read_csv(

            self.file_path

        )