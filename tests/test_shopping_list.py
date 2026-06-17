from services.grocery.shopping_list import ShoppingList


shopping = ShoppingList()


grocery = {

    "Rice": {

        "quantity": 1200,

        "unit": "g"

    },

    "Paneer": {

        "quantity": 500,

        "unit": "g"

    },

    "Milk": {

        "quantity": 1500,

        "unit": "ml"

    }

}


result = shopping.generate(

    grocery

)


for item in result:

    print(item)