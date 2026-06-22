class RecipeTextBuilder:


    def build(

        self,

        recipe

    ):


        text = f"""

        Title:

        {recipe['title']}


        Cuisine:

        {recipe.get('cuisine','')}


        Description:

        {recipe.get('description','')}


        Ingredients:

        {recipe.get('ingredients','')}


        Instructions:

        {recipe.get('instructions','')}

        """


        return text