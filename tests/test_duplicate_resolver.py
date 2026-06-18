from services.enrichment.duplicate_resolver import DuplicateResolver


resolver = DuplicateResolver()



print(

resolver.classify(

"Paneer Butter Masala",

"Paneer Butter Masala Recipe"

)

)



print(

resolver.classify(

"Paneer Butter Masala",

"Restaurant Style Paneer Butter Masala"

)

)



print(

resolver.classify(

"Paneer Butter Masala",

"Chicken Biryani"

)

)