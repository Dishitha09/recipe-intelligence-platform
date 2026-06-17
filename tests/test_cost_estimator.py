from services.grocery.cost_estimator import CostEstimator


estimator = CostEstimator()


shopping_list = [

    {

        "ingredient":"Rice",

        "quantity":1200,

        "unit":"g"

    },

    {

        "ingredient":"Paneer",

        "quantity":500,

        "unit":"g"

    },

    {

        "ingredient":"Milk",

        "quantity":1500,

        "unit":"ml"

    }

]


result = estimator.estimate(

    shopping_list

)


print(result)