from services.enrichment.uom.uom_normalizer import UOMNormalizer


uom=UOMNormalizer()


print(

uom.normalize(

"paneer",

"1",

"cup"

)

)


print(

uom.normalize(

"milk",

"1",

"cup"

)

)


print(

uom.normalize(

"rice",

"1/4",

"cup"

)

)


print(

uom.normalize(

"oil",

"1",

"tbsp"

)

)


print(

uom.normalize(

"salt",

"1",

"pinch"

)

)


print(

uom.normalize(

"butter",

"250",

"g"

)

)


print(

uom.normalize(

"xyz",

"1",

"cup"

)

)