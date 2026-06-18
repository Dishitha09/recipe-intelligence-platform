import os


class DatasetScanner:


    def scan(self, path):


        files = []


        for root, dirs, names in os.walk(path):


            for file in names:


                files.append(

                    os.path.join(

                        root,

                        file

                    )

                )


        return files