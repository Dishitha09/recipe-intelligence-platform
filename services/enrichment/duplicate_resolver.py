class DuplicateResolver:


    def clean(self, text):

        text = text.lower()


        remove_words = [

            "recipe",

            "style",

            "restaurant",

            "authentic",

            "easy",

            "homemade",

            "traditional"

        ]


        for word in remove_words:

            text = text.replace(word, "")


        return text.strip()



    def similarity(

        self,

        a,

        b

    ):


        a = self.clean(a)

        b = self.clean(b)


        words_a = set(a.split())

        words_b = set(b.split())


        common = words_a.intersection(words_b)


        return (

            len(common)

            /

            max(

                len(words_a),

                len(words_b)

            )

        )



    def classify(

        self,

        recipe1,

        recipe2

    ):


        score = self.similarity(

            recipe1,

            recipe2

        )


        if score >= 0.90:


            return {


                "type":"duplicate",

                "score":score

            }


        elif score >= 0.50:


            return {


                "type":"variation",

                "score":score

            }


        else:


            return {


                "type":"new",

                "score":score

            }