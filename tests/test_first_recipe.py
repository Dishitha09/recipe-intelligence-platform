import pandas as pd

df = pd.read_csv(

    "data/datasets/indian/raw/scraped_urls.csv"

)


print(

    df.iloc[0]["recipe_url"]

)