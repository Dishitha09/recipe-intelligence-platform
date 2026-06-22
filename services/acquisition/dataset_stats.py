import os


class DatasetStats:


    def count_csv_files(self, path):


        count = 0


        for root, dirs, files in os.walk(path):


            for file in files:


                if file.endswith(".csv"):

                    count += 1


        return count