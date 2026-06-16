from scrapy.crawler import CrawlerProcess

from services.ingestion.web_scraper.indian_recipe_spider import (

IndianRecipeSpider

)



process=CrawlerProcess(

{

"LOG_LEVEL":"INFO"

}

)



process.crawl(

IndianRecipeSpider

)



process.start()