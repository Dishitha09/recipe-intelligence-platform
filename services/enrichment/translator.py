class Translator:


    def __init__(self):


        self.dictionary = {


            "पनीर बटर मसाला":

            "Paneer Butter Masala",


            "मसाला डोसा":

            "Masala Dosa",


            "छोले भटूरे":

            "Chole Bhature",


            "இட்லி":

            "Idli",


            "மசாலா தோசை":

            "Masala Dosa",


            "சாம்பார்":

            "Sambar"

        }



    def translate(

        self,

        text

    ):


        return self.dictionary.get(

            text,

            text

        )