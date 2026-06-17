class CostEstimator:


    def __init__(self):


        self.price_catalog = {


            "Rice": 70,

            "Paneer": 360,

            "Milk": 60,

            "Butter": 600,

            "Tomato": 40,

            "Chickpea": 120

        }


    def estimate(self, shopping_list):


        total = 0

        breakdown = []


        for item in shopping_list:


            ingredient = item["ingredient"]

            quantity = item["quantity"]

            unit = item["unit"]


            if unit == "g":

                cost = (

                    quantity / 1000

                ) * self.price_catalog.get(

                    ingredient,

                    0

                )


            elif unit == "ml":

                cost = (

                    quantity / 1000

                ) * self.price_catalog.get(

                    ingredient,

                    0

                )


            else:

                cost = 0


            total += cost


            breakdown.append(

                {

                    "ingredient": ingredient,

                    "cost": round(cost,2)

                }

            )


        return {

            "items": breakdown,

            "total_cost": round(total,2)

        }