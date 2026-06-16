import requests

from bs4 import BeautifulSoup



def collect_recipe_urls(url):

    headers = {

        "User-Agent":

        "Mozilla/5.0"

    }


    response = requests.get(

        url,

        headers=headers,

        timeout=30

    )


    soup = BeautifulSoup(

        response.text,

        "html.parser"

    )


    urls=[]


    for a in soup.select("h2.entry-title a"):


        href=a.get("href")


        if href:

            urls.append(href)


    return list(set(urls))