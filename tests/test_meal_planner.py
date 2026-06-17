from services.grocery.meal_planner import MealPlanner


planner = MealPlanner()


planner.add_meal(

    "Monday",

    "Masala Dosa"

)


planner.add_meal(

    "Tuesday",

    "Paneer Butter Masala"

)


planner.add_meal(

    "Wednesday",

    "Chole Bhature"

)


print(

    planner.get_plan()

)