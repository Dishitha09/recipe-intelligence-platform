from services.ingestion.web_scraper.collectors.url_collector import (

collect_recipe_urls

)



urls=collect_recipe_urls(

"https://www.indianhealthyrecipes.com/"

)



print(

len(urls)

)



for url in urls[:10]:

    print(url)