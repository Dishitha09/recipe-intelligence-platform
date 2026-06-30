import re
from dataclasses import dataclass
from typing import Iterable, Optional


REGION_BY_STATE = {
    "Andhra Pradesh": "South",
    "Arunachal Pradesh": "Northeast",
    "Assam": "Northeast",
    "Bihar": "East",
    "Chhattisgarh": "Central",
    "Goa": "West",
    "Gujarat": "West",
    "Haryana": "North",
    "Himachal Pradesh": "North",
    "Jharkhand": "East",
    "Karnataka": "South",
    "Kerala": "South",
    "Madhya Pradesh": "Central",
    "Maharashtra": "West",
    "Manipur": "Northeast",
    "Meghalaya": "Northeast",
    "Mizoram": "Northeast",
    "Nagaland": "Northeast",
    "Odisha": "East",
    "Punjab": "North",
    "Rajasthan": "Northwest",
    "Sikkim": "Northeast",
    "Tamil Nadu": "South",
    "Telangana": "South",
    "Tripura": "Northeast",
    "Uttar Pradesh": "North",
    "Uttarakhand": "North",
    "West Bengal": "East",
    "Delhi": "North",
    "Puducherry": "South",
    "Chandigarh": "North",
    "Lakshadweep": "Southwest",
    "Andaman and Nicobar": "Island",
    "Dadra and Nagar Haveli and Daman and Diu": "West",
    "Ladakh": "North",
    "Jammu and Kashmir": "North",
}


KEYWORDS_BY_STATE = {
    "Andhra Pradesh": [
        "andhra",
        "guntur",
        "gongura",
        "pulihora",
        "pesarattu",
        "avakaya",
        "bobbatlu",
    ],
    "Arunachal Pradesh": ["arunachal", "apong", "zan", "lukter"],
    "Assam": ["assam", "assamese", "tenga", "khar", "joha", "pitha"],
    "Bihar": ["bihar", "bihari", "litti", "chokha", "sattu", "thekua"],
    "Chhattisgarh": ["chhattisgarh", "chila", "fara", "bafauri"],
    "Goa": ["goa", "goan", "xacuti", "vindaloo", "bebinca", "sorpotel"],
    "Gujarat": [
        "gujarat",
        "gujarati",
        "dhokla",
        "thepla",
        "khakhra",
        "undhiyu",
        "khandvi",
        "fafda",
        "handvo",
    ],
    "Haryana": ["haryana", "haryanvi", "bajra khichdi", "hara dhania chutney"],
    "Himachal Pradesh": ["himachal", "himachali", "dham", "siddu", "madra"],
    "Jharkhand": ["jharkhand", "dhuska", "rugra", "chilka roti"],
    "Karnataka": [
        "karnataka",
        "kannada",
        "mysore",
        "mangalore",
        "mangalorean",
        "udupi",
        "bisi bele",
        "neer dosa",
        "ragi mudde",
        "akki rotti",
    ],
    "Kerala": [
        "kerala",
        "malabar",
        "appam",
        "puttu",
        "avial",
        "olan",
        "erissery",
        "thoran",
        "meen moilee",
    ],
    "Madhya Pradesh": ["madhya pradesh", "indori", "bhutte ka kees", "dal bafla"],
    "Maharashtra": [
        "maharashtra",
        "maharashtrian",
        "marathi",
        "misal",
        "vada pav",
        "pav bhaji",
        "puran poli",
        "zunka",
        "bhakri",
        "kolhapuri",
    ],
    "Manipur": ["manipur", "manipuri", "eromba", "singju", "chamthong"],
    "Meghalaya": ["meghalaya", "khasi", "jadoh", "dohneiiong"],
    "Mizoram": ["mizoram", "mizo", "bai", "vawksa"],
    "Nagaland": ["nagaland", "naga", "axone", "akhuni", "smoked pork"],
    "Odisha": ["odisha", "odia", "oriya", "dalma", "pakhala", "chhena poda"],
    "Punjab": [
        "punjab",
        "punjabi",
        "amritsari",
        "sarson",
        "makki",
        "chole",
        "kulcha",
        "butter chicken",
    ],
    "Rajasthan": [
        "rajasthan",
        "rajasthani",
        "dal bati",
        "dal baati",
        "churma",
        "gatte",
        "ker sangri",
        "laal maas",
        "pyaaz kachori",
    ],
    "Sikkim": ["sikkim", "gundruk", "kinema"],
    "Tamil Nadu": [
        "tamil",
        "tamil nadu",
        "chettinad",
        "pongal",
        "rasam",
        "idli",
        "kootu",
        "poriyal",
        "sundal",
    ],
    "Telangana": ["telangana", "hyderabad", "hyderabadi", "bagara", "haleem", "sarva pindi"],
    "Tripura": ["tripura", "mui borok", "wahan mosdeng"],
    "Uttar Pradesh": ["uttar pradesh", "awadhi", "lucknow", "lucknowi", "banarasi", "nihari"],
    "Uttarakhand": ["uttarakhand", "kumaoni", "garhwali", "kafuli", "chainsoo", "jhangora"],
    "West Bengal": [
        "west bengal",
        "bengal",
        "bengali",
        "kolkata",
        "luchi",
        "shorshe",
        "posto",
        "sandesh",
        "mishti",
    ],
    "Delhi": ["delhi", "dilli", "chandni chowk"],
    "Puducherry": ["puducherry", "pondicherry"],
    "Chandigarh": ["chandigarh"],
    "Lakshadweep": ["lakshadweep"],
    "Andaman and Nicobar": ["andaman", "nicobar"],
    "Dadra and Nagar Haveli and Daman and Diu": ["daman", "diu", "dadra", "nagar haveli"],
    "Ladakh": ["ladakh", "ladakhi", "skyur"],
    "Jammu and Kashmir": ["jammu", "kashmir", "kashmiri", "rogan josh", "yakhni", "kahwa"],
}


AMBIGUOUS_REGION_KEYWORDS = {
    "South": ["dosa", "sambar", "uttapam", "upma", "coconut chutney"],
    "North": ["paratha", "kadhi", "rajma", "naan"],
    "East": ["pitha", "fish curry"],
    "West": ["poha", "shrikhand"],
    "Northeast": ["momo", "thukpa"],
}


@dataclass(frozen=True)
class StateClassification:
    state: Optional[str]
    region: Optional[str]
    confidence: float
    method: str
    matched_terms: tuple[str, ...] = ()


class RecipeStateClassifier:
    def classify(self, recipe) -> StateClassification:
        existing_state = getattr(recipe, "state", None)
        existing_region = getattr(recipe, "region", None)

        if existing_state:
            return StateClassification(
                state=existing_state,
                region=existing_region or REGION_BY_STATE.get(existing_state),
                confidence=1.0,
                method="provided_state",
                matched_terms=(existing_state,),
            )

        text = self._recipe_text(recipe)

        explicit = self._match_keywords(text, confidence=0.95)
        if explicit is not None:
            return explicit

        region = self._match_region(text)
        if region is not None:
            return region

        cuisine = self._normalize(getattr(recipe, "cuisine", None))
        if cuisine and cuisine not in {"indian", "india"}:
            cuisine_match = self._match_keywords(cuisine, confidence=0.72)
            if cuisine_match is not None:
                return StateClassification(
                    state=cuisine_match.state,
                    region=cuisine_match.region,
                    confidence=0.72,
                    method="cuisine_keyword",
                    matched_terms=cuisine_match.matched_terms,
                )

        return StateClassification(
            state=None,
            region=None,
            confidence=0.0,
            method="unclassified",
            matched_terms=(),
        )

    def _match_keywords(self, text: str, confidence: float):
        matches = []

        for state, keywords in KEYWORDS_BY_STATE.items():
            for keyword in keywords:
                if self._contains_term(text, keyword):
                    matches.append((state, keyword))

        if not matches:
            return None

        state, keyword = sorted(
            matches,
            key=lambda match: len(match[1]),
            reverse=True,
        )[0]

        return StateClassification(
            state=state,
            region=REGION_BY_STATE.get(state),
            confidence=confidence,
            method="state_keyword",
            matched_terms=(keyword,),
        )

    def _match_region(self, text: str):
        for region, keywords in AMBIGUOUS_REGION_KEYWORDS.items():
            for keyword in keywords:
                if self._contains_term(text, keyword):
                    return StateClassification(
                        state=None,
                        region=region,
                        confidence=0.45,
                        method="regional_keyword",
                        matched_terms=(keyword,),
                    )

        return None

    def _recipe_text(self, recipe) -> str:
        metadata = getattr(recipe, "metadata", None) or {}
        text_parts = [
            getattr(recipe, "title", None),
            getattr(recipe, "original_title", None),
            getattr(recipe, "description", None),
            getattr(recipe, "cuisine", None),
            getattr(recipe, "source_url", None),
            metadata.get("tags"),
            metadata.get("source_metadata"),
        ]

        return self._normalize(" ".join(self._flatten(text_parts)))

    def _flatten(self, values: Iterable) -> Iterable[str]:
        for value in values:
            if value is None:
                continue

            if isinstance(value, dict):
                yield from self._flatten(value.values())
            elif isinstance(value, (list, tuple, set)):
                yield from self._flatten(value)
            else:
                yield str(value)

    def _normalize(self, value) -> str:
        if value is None:
            return ""

        return re.sub(r"\s+", " ", str(value).lower()).strip()

    def _contains_term(self, text: str, term: str) -> bool:
        normalized_term = self._normalize(term)
        pattern = r"(?<![a-z0-9])" + re.escape(normalized_term) + r"(?![a-z0-9])"

        return re.search(pattern, text) is not None
