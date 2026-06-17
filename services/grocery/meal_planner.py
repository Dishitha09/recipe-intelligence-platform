class MealPlanner:


    def __init__(self):

        self.plan = {}


    def add_meal(

        self,

        day,

        recipe

    ):


        self.plan[day] = recipe


    def get_plan(self):


        return self.plan