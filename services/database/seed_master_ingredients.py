import argparse

from services.enrichment.ingredient_resolution.alias_resolver import (
    INGREDIENT_ALIAS,
)
from services.database.ingredient_repository import IngredientRepository


RICE_VARIETIES = """
ambemohar rice
arwa rice
basmati rice
black rice
boiled rice
brown rice
gobindobhog rice
hand pounded rice
idli rice
indrayani rice
jeera samba rice
kalanamak rice
kaima rice
kolam rice
matta rice
mogra rice
navara rice
ponni rice
raw rice
red rice
samba rice
seeraga samba rice
sona masuri rice
steamed rice
surti kolam rice
ukda rice
white rice
wild rice
""".strip().splitlines()

GRAINS_AND_MILLETS = """
amaranth
bajra
barley
barnyard millet
broken wheat
buckwheat
bulgur wheat
corn
foxtail millet
jowar
kodo millet
little millet
maize
oats
pearl millet
poha
proso millet
quinoa
ragi
red poha
rice flakes
rolled oats
sabudana
samai
semolina
sorghum
wheat
white poha
""".strip().splitlines()

PULSES = """
adzuki bean
black chickpea
black eyed pea
black gram
brown chickpea
brown lentil
chana dal
chickpea
cowpea
field bean
green gram
green lentil
horse gram
kala chana
kidney bean
lobia
masoor dal
matki
moth bean
moong dal
navy bean
orange lentil
peas
pigeon peas
rajma
red bean
red lentil
soybean
toor dal
urad dal
val bean
white chickpea
white pea
yellow moong dal
""".strip().splitlines()

FLOURS_AND_STARCHES = """
all purpose flour
arrowroot powder
bajra flour
besan
buckwheat flour
corn flour
corn starch
gram flour
jowar flour
maida
millet flour
oat flour
potato starch
ragi flour
rice flour
roasted gram flour
sabudana flour
semolina
singhara flour
soy flour
tapioca starch
wheat flour
whole wheat flour
""".strip().splitlines()

VEGETABLES = """
ash gourd
baby corn
banana blossom
banana stem
beetroot
bitter gourd
bottle gourd
brinjal
broad beans
broccoli
cabbage
capsicum
carrot
cauliflower
celery
chayote
cluster beans
colocasia
cucumber
drumstick
elephant foot yam
french beans
garlic
green beans
green chili
green peas
ivy gourd
jackfruit
knol khol
ladies finger
leek
lotus root
mushroom
onion
plantain
pointed gourd
potato
pumpkin
radish
raw banana
raw mango
raw papaya
ridge gourd
snake gourd
spring onion
sweet corn
sweet potato
taro root
tendli
tomato
turnip
yam
yellow cucumber
zucchini
""".strip().splitlines()

LEAFY_GREENS = """
agathi leaves
amaranth leaves
bathua
betel leaves
brahmi leaves
cabbage leaves
celery leaves
chakravarthy leaves
cheera
coriander leaves
curry leaves
dill leaves
fenugreek leaves
gongura
keerai
lettuce
malabar spinach
mint leaves
moringa leaves
mustard greens
palak
ponnaganni keerai
radish leaves
red amaranth
shepu
spinach
spring onion greens
""".strip().splitlines()

FRUITS = """
apple
apricot
banana
black grape
blueberry
cherry
chikoo
custard apple
dates
dragon fruit
fig
gooseberry
grapes
green apple
guava
jackfruit pulp
jamun
kiwi
lemon
lime
lychee
mango
melon
mosambi
mulberry
orange
papaya
peach
pear
pineapple
plum
pomegranate
raisins
raspberry
raw jackfruit
strawberry
sweet lime
watermelon
wood apple
""".strip().splitlines()

SPICES = """
ajwain
amchur
asafoetida
bay leaf
black cardamom
black cumin
black pepper
caraway seed
cardamom
cassia
chili flakes
cinnamon
clove
coriander
cumin
dagad phool
dry ginger
fennel
fenugreek seed
garam masala
green cardamom
kasuri methi
kebab chini
kokum
long pepper
mace
mango powder
mustard seed
nigella seed
nutmeg
panch phoron
paprika
poppy seed
red chili
red chili powder
saffron
sesame seed
star anise
stone flower
tamarind
turmeric
white pepper
""".strip().splitlines()

HERBS = """
basil
celery herb
chives
coriander leaves
curry leaves
dill
lemongrass
mint
oregano
parsley
rosemary
sage
thyme
""".strip().splitlines()

NUTS_AND_SEEDS = """
almond
apricot kernel
cashew
char magaz
chia seed
coconut
dry coconut
flax seed
fox nut
groundnut
hazelnut
lotus seed
melon seed
peanut
pinenut
pistachio
pumpkin seed
raisins
sesame seed
sunflower seed
walnut
watermelon seed
""".strip().splitlines()

DAIRY_AND_FATS = """
butter
buttermilk
cheese
chenna
clarified butter
cream
curd
ghee
khoya
milk
paneer
yogurt
""".strip().splitlines()

OILS = """
coconut oil
groundnut oil
mustard oil
peanut oil
rice bran oil
sesame oil
sunflower oil
vegetable oil
""".strip().splitlines()

SWEETENERS = """
brown sugar
cane sugar
castor sugar
coconut sugar
date syrup
gud
honey
jaggery
maple syrup
molasses
palm jaggery
powdered sugar
rock sugar
sugar
""".strip().splitlines()

PROTEINS_AND_SEAFOOD = """
anchovy
beef
boneless chicken
chicken
chicken breast
chicken drumstick
chicken liver
chicken thigh
crab
duck
egg
fish
fish roe
goat meat
hilsa fish
king fish
lamb
mackerel
mutton
pomfret
pork
prawn
quail
rohu fish
sardine
seer fish
shrimp
surmai
tilapia
tuna
""".strip().splitlines()

CONDIMENTS_AND_PANTRY = """
apple cider vinegar
baking powder
baking soda
black salt
chaat masala
chili garlic sauce
coconut milk
dark soy sauce
fish sauce
green chutney
idli podi
imli chutney
ketchup
mayonnaise
mustard paste
pickle masala
pink salt
rice vinegar
rock salt
salt
soy sauce
tamarind paste
tomato puree
vinegar
white salt
""".strip().splitlines()


def normalize_name(name):
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def rows_from(names, category, default_unit="g"):
    return [
        {
            "canonical_name": normalize_name(name),
            "display_name": name,
            "category": category,
            "default_unit": default_unit,
            "aliases": [name, normalize_name(name)],
        }
        for name in names
        if name.strip()
    ]


def build_master_ingredients():
    rows = []
    rows.extend(rows_from(RICE_VARIETIES, "rice_grain"))
    rows.extend(rows_from(GRAINS_AND_MILLETS, "grain"))
    rows.extend(rows_from(FLOURS_AND_STARCHES, "flour"))
    rows.extend(rows_from(VEGETABLES, "vegetable"))
    rows.extend(rows_from(LEAFY_GREENS, "leafy_green"))
    rows.extend(rows_from(FRUITS, "fruit"))
    rows.extend(rows_from(SPICES, "spice"))
    rows.extend(rows_from(HERBS, "herb"))
    rows.extend(rows_from(NUTS_AND_SEEDS, "nut_seed"))
    rows.extend(rows_from(DAIRY_AND_FATS, "dairy_fat"))
    rows.extend(rows_from(OILS, "oil"))
    rows.extend(rows_from(SWEETENERS, "sweetener"))
    rows.extend(rows_from(PROTEINS_AND_SEAFOOD, "protein"))
    rows.extend(rows_from(CONDIMENTS_AND_PANTRY, "pantry"))

    pulse_forms = ["whole", "split", "skinned", "sprouted", "flour"]

    for pulse in PULSES:
        rows.append(
            {
                "canonical_name": normalize_name(pulse),
                "display_name": pulse,
                "category": "pulse",
                "default_unit": "g",
                "aliases": [pulse, normalize_name(pulse)],
            }
        )

        for form in pulse_forms:
            display_name = f"{form} {pulse}"
            rows.append(
                {
                    "canonical_name": normalize_name(display_name),
                    "display_name": display_name,
                    "category": "pulse",
                    "default_unit": "g",
                    "aliases": [display_name, normalize_name(display_name)],
                }
            )

    by_name = {}

    for row in rows:
        by_name[row["canonical_name"]] = row

    for alias, canonical_name in INGREDIENT_ALIAS.items():
        by_name.setdefault(
            canonical_name,
            {
                "canonical_name": canonical_name,
                "display_name": canonical_name.replace("_", " "),
                "category": "seeded_alias",
                "default_unit": "g",
                "aliases": [canonical_name.replace("_", " "), canonical_name],
            },
        )
        by_name[canonical_name]["aliases"].append(alias)

    return sorted(by_name.values(), key=lambda row: row["canonical_name"])


def seed_master_ingredients(with_embeddings=False):
    repository = IngredientRepository()
    rows = build_master_ingredients()
    embedding_model = None

    if with_embeddings:
        from services.enrichment.ingredient_resolution.embedding_resolver import (
            EmbeddingResolver,
        )

        embedding_model = EmbeddingResolver(
            master_ingredients=[
                row["canonical_name"]
                for row in rows
            ]
        )

    for row in rows:
        ingredient_id = repository.upsert_master_ingredient(
            canonical_name=row["canonical_name"],
            category=row["category"],
            default_unit=row["default_unit"],
        )

        for alias in sorted(set(row["aliases"])):
            repository.upsert_alias(
                ingredient_id=ingredient_id,
                alias_name=alias,
                source="seed_master_ingredients",
            )

        if embedding_model is not None:
            repository.upsert_embedding(
                ingredient_id=ingredient_id,
                embedding=embedding_model.embed_text(row["canonical_name"]),
            )

    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--with-embeddings", action="store_true")
    args = parser.parse_args()

    rows = build_master_ingredients()

    if args.dry_run:
        print(f"Master ingredient seed count: {len(rows)}")
        return

    count = seed_master_ingredients(
        with_embeddings=args.with_embeddings
    )
    print(f"Seeded {count} master ingredients")


if __name__ == "__main__":
    main()
