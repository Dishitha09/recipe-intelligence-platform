class PromptBuilder:


    def build(self, question, recipes):


        prompt = f"""

You are an expert Indian Recipe Assistant.


User Question:

{question}



Relevant Recipes:

"""


        for r in recipes:


            prompt += f"""

Recipe:

{r['title']}


Cuisine:

{r['cuisine']}


Similarity:

{r['similarity']}


"""


        prompt += """

Provide:

1. Recommended recipes

2. Brief explanation

3. Missing ingredients if applicable

4. Cooking suggestions

"""


        return prompt