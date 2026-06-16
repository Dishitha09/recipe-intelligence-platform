from services.rag.semantic_search import SemanticSearch



search=SemanticSearch()



results=search.search(

"South Indian Breakfast"

)



for row in results:

    print(row)