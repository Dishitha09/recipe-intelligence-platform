"""Collect recipe-like records from public PDF/OCR cookbook sources.

The scraper uses Internet Archive text/OCR sidecars when available and stores
the original PDF URL as provenance. Each parsed recipe gets a unique URL anchor
so loader idempotency prevents duplicates without collapsing a whole book into
one recipe.
"""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

import requests

from services.enrichment.ingredient_resolution.ingredient_resolver import (
    IngredientResolver,
)
from services.enrichment.recipe_enricher import RecipeEnricher
from services.ingestion.raw_record import RawRecord
from services.pipeline.recipe_pipeline import RecipePipeline


ROOT = Path("data/datasets/pdf_scrape")
RAW_TEXT_DIR = ROOT / "raw_text"
NORMALIZED_PATH = ROOT / "normalized_pdf_recipes.csv"
SOURCES_PATH = ROOT / "pdf_sources.json"
SOURCE_ID = "pdf.internet_archive"
IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_METADATA_URL = "https://archive.org/metadata/{identifier}"
IA_DOWNLOAD_URL = "https://archive.org/download/{identifier}/{filename}"

SEARCH_QUERIES = (
    '"The Indian Cookery Book" AND mediatype:texts',
    '"Culinary Jottings for Madras" AND mediatype:texts',
    '"The Curry Cook" AND mediatype:texts',
    '"Indian Domestic Economy" AND mediatype:texts',
    '"Wyvern" "Madras" "cookery" AND mediatype:texts',
    'title:"Indian Cookery" AND mediatype:texts',
    'title:"Indian Cooking" AND mediatype:texts',
    'title:"Indian Recipes" AND mediatype:texts',
    'title:curry AND (cookery OR cooking OR recipes) AND mediatype:texts',
    'subject:cookery AND (india OR indian OR curry) AND mediatype:texts',
)

TITLE_DENYLIST = {
    "contents",
    "index",
    "preface",
    "introduction",
    "chapter",
    "appendix",
    "advertisements",
    "notes",
    "glossary",
}

COOKING_VERBS = (
    "add",
    "bake",
    "boil",
    "cook",
    "fry",
    "grind",
    "heat",
    "mix",
    "pour",
    "roast",
    "serve",
    "simmer",
    "stir",
    "strain",
    "wash",
)

INGREDIENT_WORDS = (
    "atta",
    "bajra",
    "chilli",
    "chili",
    "coconut",
    "coriander",
    "cumin",
    "curd",
    "dal",
    "flour",
    "garlic",
    "ghee",
    "ginger",
    "gram",
    "jaggery",
    "masala",
    "mustard",
    "oil",
    "onion",
    "pepper",
    "rice",
    "salt",
    "tamarind",
    "turmeric",
    "water",
)

INDIAN_SIGNALS = (
    "achar",
    "bajra",
    "bengal",
    "bindaloo",
    "biriyani",
    "biryani",
    "chapati",
    "chappatee",
    "chutnee",
    "chutney",
    "curry",
    "curried",
    "dal",
    "dhal",
    "ghee",
    "hindoo",
    "hindu",
    "jagree",
    "jaggery",
    "kedgeree",
    "korma",
    "kurma",
    "madras",
    "masala",
    "mulligatawny",
    "pilau",
    "pulao",
    "rasam",
    "sambhar",
    "tamarind",
    "vindaloo",
)

LOCAL_SKIP_IDENTIFIERS = {
    "practicalcookeng00breg",
}


def clean_text(value):
    value = str(value or "").replace("\u00a0", " ")
    value = value.replace("\ufeff", "")
    return re.sub(r"\s+", " ", value).strip()


def search_internet_archive(rows=40):
    seen = set()
    results = []

    for query in SEARCH_QUERIES:
        response = requests.get(
            IA_SEARCH_URL,
            params={
                "q": query,
                "fl[]": ["identifier", "title", "date", "downloads"],
                "rows": rows,
                "output": "json",
            },
            timeout=40,
        )
        response.raise_for_status()

        for doc in response.json().get("response", {}).get("docs", []):
            identifier = doc.get("identifier")
            title = clean_text(doc.get("title"))

            if not identifier or identifier in seen:
                continue

            if not _is_relevant_title(title):
                continue

            seen.add(identifier)
            results.append(
                {
                    "identifier": identifier,
                    "title": title,
                    "date": doc.get("date"),
                    "downloads": doc.get("downloads"),
                }
            )

    return results


def _is_relevant_title(title):
    lower = title.lower()
    if any(
        phrase in lower
        for phrase in (
            "english and foreign",
            "american indian",
            "west indian",
            "financial",
            "insurance",
        )
    ):
        return False

    return any(
        token in lower
        for token in ("india", "indian", "curry", "bengal", "madras", "hindu")
    ) and any(
        token in lower
        for token in ("cook", "recipe", "curry", "kitchen", "dish")
    )


def metadata_for(identifier):
    response = requests.get(
        IA_METADATA_URL.format(identifier=quote(identifier)),
        timeout=40,
    )
    response.raise_for_status()
    return response.json()


def choose_text_and_pdf_files(metadata):
    files = metadata.get("files") or []
    text_files = [
        file
        for file in files
        if str(file.get("name", "")).lower().endswith(("_djvu.txt", ".txt"))
    ]
    pdf_files = [
        file
        for file in files
        if str(file.get("name", "")).lower().endswith(".pdf")
    ]

    text_files.sort(key=lambda item: (not item.get("name", "").endswith("_djvu.txt"), item.get("name", "")))
    pdf_files.sort(key=lambda item: item.get("name", ""))

    return (
        text_files[0].get("name") if text_files else None,
        pdf_files[0].get("name") if pdf_files else None,
    )


def download_text(identifier, filename):
    RAW_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    local_path = RAW_TEXT_DIR / f"{identifier}.txt"

    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path

    response = requests.get(
        IA_DOWNLOAD_URL.format(
            identifier=quote(identifier),
            filename=quote(filename),
        ),
        timeout=80,
    )
    response.raise_for_status()
    local_path.write_text(response.text, encoding="utf-8", errors="ignore")
    return local_path


def parse_recipes_from_text(text, pdf_url, source_title, max_recipes=None):
    lines = _clean_ocr_lines(text)
    title_candidates = _title_candidates(lines)
    recipes = []

    for position, candidate in enumerate(title_candidates):
        start = candidate["index"]
        end = (
            title_candidates[position + 1]["index"]
            if position + 1 < len(title_candidates)
            else min(start + 90, len(lines))
        )
        title = candidate["title"]
        body_lines = lines[start + 1:end]
        recipe = _recipe_from_block(
            title=title,
            body_lines=body_lines,
            pdf_url=pdf_url,
            source_title=source_title,
            index=len(recipes) + 1,
        )

        if recipe:
            recipes.append(recipe)

        if max_recipes and len(recipes) >= max_recipes:
            break

    return recipes


def _title_candidates(lines):
    candidates = []
    seen_indexes = set()

    for index, line in enumerate(lines):
        numbered_title = _numbered_recipe_title(line)

        if numbered_title:
            candidates.append(
                {
                    "index": index,
                    "title": numbered_title,
                    "kind": "numbered",
                }
            )
            seen_indexes.add(index)

    for index, line in enumerate(lines):
        if index in seen_indexes:
            continue

        if _looks_like_title(line):
            candidates.append(
                {
                    "index": index,
                    "title": _normalize_title(line),
                    "kind": "heading",
                }
            )

    candidates.sort(key=lambda candidate: candidate["index"])
    return candidates


def _numbered_recipe_title(line):
    stripped = clean_text(line).strip()
    match = re.match(
        r"^\s*\d{1,4}\s*[.)]?\s*[—–-]\s*(.{3,90})$",
        stripped,
    )

    if not match:
        return None

    title = _normalize_title(match.group(1))
    lower = title.lower()

    if lower in TITLE_DENYLIST:
        return None

    if len(title) < 4 or len(title) > 80:
        return None

    if re.search(r"\.{3,}| {3,}", title):
        return None

    return title


def _clean_ocr_lines(text):
    cleaned = []

    for raw_line in str(text or "").splitlines():
        line = clean_text(raw_line)

        if not line:
            continue

        if re.search(r"^(digitized by|google|internet archive|copyright)", line, re.I):
            continue

        if re.fullmatch(r"[\W\d_]{1,8}", line):
            continue

        cleaned.append(line)

    return cleaned


def _looks_like_title(line):
    stripped = clean_text(line).strip(".:- ")
    lower = stripped.lower()

    if not stripped or lower in TITLE_DENYLIST:
        return False

    if len(stripped) < 4 or len(stripped) > 70:
        return False

    if re.search(r"\.{3,}| {3,}|\bib\.?$", stripped, re.I):
        return False

    if any(char in stripped for char in ("�", "□", "■")):
        return False

    if re.match(
        r"^(allow|as to|boiling|broiling|decide|equal|hard-boiled|melted|on stock|pepper|perfumery|the juice|to make)\b",
        stripped,
        re.I,
    ):
        return False

    if re.search(r"\d", stripped):
        return False

    if _looks_like_ingredient(stripped):
        return False

    word_count = len(stripped.split())

    if word_count > 9:
        return False

    upper_ratio = sum(char.isupper() for char in stripped) / max(1, sum(char.isalpha() for char in stripped))
    title_case = stripped[:1].isupper() and not stripped.endswith(".")
    food_hint = any(word in lower for word in INGREDIENT_WORDS) or any(
        word in lower
        for word in ("curry", "chutney", "pulao", "rice", "dal", "pickle", "soup", "bread", "cake", "pudding")
    )

    return (upper_ratio > 0.45 or title_case) and food_hint


def _normalize_title(title):
    title = clean_text(title).strip(" .:-")
    title = re.sub(r"^\d+[\). -]+", "", title)
    return title.title() if title.isupper() else title


def _recipe_from_block(title, body_lines, pdf_url, source_title, index):
    text = " ".join(body_lines)
    lower = text.lower()
    signal_text = f"{title} {text}".lower()

    if not any(signal in signal_text for signal in INDIAN_SIGNALS):
        return None

    if sum(verb in lower for verb in COOKING_VERBS) < 2:
        return None

    ingredients = _extract_ingredients(body_lines)
    steps = _extract_steps(text)

    if len(ingredients) < 3 or len(steps) < 2:
        return None

    recipe_hash = hashlib.sha1(f"{source_title}|{title}|{index}".encode("utf-8")).hexdigest()[:12]
    source_url = f"{pdf_url}#recipe={recipe_hash}"

    return {
        "title": title,
        "description": f"Parsed from PDF source: {source_title}",
        "source_url": source_url,
        "ingredients": " | ".join(ingredients[:24]),
        "instructions": " | ".join(steps[:18]),
        "raw_text": (
            f"{title}\nIngredients:\n"
            + "\n".join(ingredients[:24])
            + "\nInstructions:\n"
            + "\n".join(steps[:18])
        ),
        "pdf_source_title": source_title,
        "pdf_source_url": pdf_url,
    }


def _extract_ingredients(lines):
    ingredients = []

    for line in lines[:45]:
        if _looks_like_ingredient(line):
            ingredients.extend(_split_ingredient_line(line))

    return _dedupe([item for item in ingredients if len(item) >= 3])


def _looks_like_ingredient(line):
    lower = clean_text(line).lower()
    has_quantity = bool(
        re.search(
            r"\b(\d+|one|two|three|four|half|quarter|pinch|spoon|cup|lb|oz|tsp|tbsp|teaspoon|tablespoon|seer|chatak)\b",
            lower,
        )
    )
    has_food = any(word in lower for word in INGREDIENT_WORDS)
    return has_quantity and has_food and len(lower) <= 160


def _split_ingredient_line(line):
    line = clean_text(line)
    parts = re.split(r"\s{2,}|;\s+|,\s+(?=\d|\bone\b|\btwo\b|\bhalf\b)", line, flags=re.I)
    return [clean_text(part.strip(" .;")) for part in parts if clean_text(part)]


def _extract_steps(text):
    candidates = re.split(r"(?<=[.!?])\s+", clean_text(text))
    steps = []

    for sentence in candidates:
        lower = sentence.lower()

        if len(sentence) < 20 or len(sentence) > 420:
            continue

        if not any(verb in lower for verb in COOKING_VERBS):
            continue

        if sentence in steps:
            continue

        steps.append(sentence)

    return steps


def _dedupe(values):
    seen = set()
    output = []

    for value in values:
        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        output.append(value)

    return output


def collect(max_sources=20, max_recipes=1000):
    ROOT.mkdir(parents=True, exist_ok=True)
    sources = []
    recipes = []

    for candidate in search_internet_archive(rows=max(40, max_sources * 3)):
        if len(sources) >= max_sources or len(recipes) >= max_recipes:
            break

        try:
            metadata = metadata_for(candidate["identifier"])
            text_filename, pdf_filename = choose_text_and_pdf_files(metadata)

            if not text_filename or not pdf_filename:
                continue

            text_path = download_text(candidate["identifier"], text_filename)
            pdf_url = IA_DOWNLOAD_URL.format(
                identifier=quote(candidate["identifier"]),
                filename=quote(pdf_filename),
            )
            text = text_path.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_recipes_from_text(
                text=text,
                pdf_url=pdf_url,
                source_title=candidate["title"],
                max_recipes=max_recipes - len(recipes),
            )

            if not parsed:
                continue

            sources.append(
                {
                    **candidate,
                    "text_filename": text_filename,
                    "pdf_filename": pdf_filename,
                    "pdf_url": pdf_url,
                    "local_text_path": str(text_path),
                    "parsed_recipe_count": len(parsed),
                }
            )
            recipes.extend(parsed)
        except Exception as exc:
            sources.append(
                {
                    **candidate,
                    "error": f"{type(exc).__name__}: {exc}",
                    "parsed_recipe_count": 0,
                }
            )

    _write_sources(sources)
    _write_recipes(recipes)
    return {
        "sources_examined": len(sources),
        "recipes_collected": len(recipes),
        "normalized_path": str(NORMALIZED_PATH),
        "sources_path": str(SOURCES_PATH),
    }


def collect_identifiers(identifiers, max_recipes=1000):
    ROOT.mkdir(parents=True, exist_ok=True)
    sources = []
    recipes = []

    for identifier in identifiers:
        if len(recipes) >= max_recipes:
            break

        try:
            metadata = metadata_for(identifier)
            text_filename, pdf_filename = choose_text_and_pdf_files(metadata)

            if not text_filename or not pdf_filename:
                sources.append(
                    {
                        "identifier": identifier,
                        "error": "No OCR text/PDF file found",
                        "parsed_recipe_count": 0,
                    }
                )
                continue

            text_path = download_text(identifier, text_filename)
            title = clean_text(metadata.get("metadata", {}).get("title")) or identifier
            pdf_url = IA_DOWNLOAD_URL.format(
                identifier=quote(identifier),
                filename=quote(pdf_filename),
            )
            parsed = parse_recipes_from_text(
                text=text_path.read_text(encoding="utf-8", errors="ignore"),
                pdf_url=pdf_url,
                source_title=title,
                max_recipes=max_recipes - len(recipes),
            )
            sources.append(
                {
                    "identifier": identifier,
                    "title": title,
                    "text_filename": text_filename,
                    "pdf_filename": pdf_filename,
                    "pdf_url": pdf_url,
                    "local_text_path": str(text_path),
                    "parsed_recipe_count": len(parsed),
                    "targeted": True,
                }
            )
            recipes.extend(parsed)
        except Exception as exc:
            sources.append(
                {
                    "identifier": identifier,
                    "error": f"{type(exc).__name__}: {exc}",
                    "parsed_recipe_count": 0,
                    "targeted": True,
                }
            )

    _write_sources(sources)
    _write_recipes(recipes)
    return {
        "sources_examined": len(sources),
        "recipes_collected": len(recipes),
        "normalized_path": str(NORMALIZED_PATH),
        "sources_path": str(SOURCES_PATH),
    }


def collect_from_local_text(max_recipes=1000):
    ROOT.mkdir(parents=True, exist_ok=True)
    sources = []
    recipes = []

    for text_path in sorted(RAW_TEXT_DIR.glob("*.txt")):
        if len(recipes) >= max_recipes:
            break

        identifier = text_path.stem

        if identifier in LOCAL_SKIP_IDENTIFIERS:
            continue

        source_title = identifier.replace("_", " ").replace("-", " ").title()
        pdf_url = f"https://archive.org/download/{quote(identifier)}/{quote(identifier)}.pdf"
        existing_source = _source_from_existing_manifest(identifier)

        if existing_source:
            source_title = existing_source.get("title") or source_title
            pdf_url = existing_source.get("pdf_url") or pdf_url

        parsed = parse_recipes_from_text(
            text=text_path.read_text(encoding="utf-8", errors="ignore"),
            pdf_url=pdf_url,
            source_title=source_title,
            max_recipes=max_recipes - len(recipes),
        )

        sources.append(
            {
                "identifier": identifier,
                "title": source_title,
                "pdf_url": pdf_url,
                "local_text_path": str(text_path),
                "parsed_recipe_count": len(parsed),
                "local_parse": True,
            }
        )
        recipes.extend(parsed)

    _write_sources(sources)
    _write_recipes(recipes)
    return {
        "sources_examined": len(sources),
        "recipes_collected": len(recipes),
        "normalized_path": str(NORMALIZED_PATH),
        "sources_path": str(SOURCES_PATH),
    }


def _source_from_existing_manifest(identifier):
    if not SOURCES_PATH.exists():
        return None

    try:
        sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    for source in sources:
        if source.get("identifier") == identifier:
            return source

    return None


def _write_sources(sources):
    SOURCES_PATH.write_text(
        json.dumps(sources, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _write_recipes(recipes):
    fieldnames = [
        "title",
        "description",
        "source_url",
        "ingredients",
        "instructions",
        "raw_text",
        "pdf_source_title",
        "pdf_source_url",
    ]
    with NORMALIZED_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(recipes)


def ingest(path=NORMALIZED_PATH, limit=None):
    records = []

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        for index, row in enumerate(reader, start=1):
            if limit is not None and len(records) >= limit:
                break

            records.append(
                RawRecord(
                    source_id=SOURCE_ID,
                    source_type="pdf",
                    _raw_content=dict(row),
                    metadata={
                        "file_path": str(path),
                        "row_number": index,
                        "pdf_source_url": row.get("pdf_source_url"),
                    },
                )
            )

    pipeline = RecipePipeline(
        enricher=RecipeEnricher(
            ingredient_resolver=IngredientResolver(enable_embedding=False)
        )
    )
    return pipeline.run_records(
        records,
        source_id=SOURCE_ID,
        source_name=str(path),
        source_type="pdf",
    )


def compact_summary(summary):
    if "validation_reports" not in summary:
        return summary

    return {
        "records_found": summary.get("records_found"),
        "coerced": summary.get("coerced"),
        "enriched": summary.get("enriched"),
        "accepted": summary.get("accepted"),
        "review": summary.get("review"),
        "loaded": summary.get("loaded"),
        "rejected": summary.get("rejected"),
        "dead_letter_count": len(summary.get("dead_letter") or []),
        "review_queue_count": len(summary.get("review_queue") or []),
        "validation_error_count": len(summary.get("validation_errors") or []),
        "validation_report_count": len(summary.get("validation_reports") or []),
        "ingestion_run_id": summary.get("ingestion_run_id"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape recipe-like records from public PDF/OCR cookbook sources."
    )
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--collect-local", action="store_true")
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--list-candidates", action="store_true")
    parser.add_argument("--max-sources", type=int, default=20)
    parser.add_argument("--max-recipes", type=int, default=1000)
    parser.add_argument("--identifier", action="append", default=[])
    parser.add_argument("--ingest-path", default=str(NORMALIZED_PATH))
    parser.add_argument("--ingest-limit", type=int)
    args = parser.parse_args()

    output = {}

    if args.list_candidates:
        output["candidates"] = search_internet_archive(
            rows=max(40, args.max_sources * 3)
        )[: args.max_sources]

    if args.collect:
        if args.identifier:
            output["collect"] = collect_identifiers(
                identifiers=args.identifier,
                max_recipes=args.max_recipes,
            )
        else:
            output["collect"] = collect(
                max_sources=args.max_sources,
                max_recipes=args.max_recipes,
            )

    if args.collect_local:
        output["collect_local"] = collect_from_local_text(
            max_recipes=args.max_recipes,
        )

    if args.ingest:
        output["ingest"] = compact_summary(
            ingest(
                path=args.ingest_path,
                limit=args.ingest_limit,
            )
        )

    if not output:
        output["collect"] = collect(
            max_sources=args.max_sources,
            max_recipes=args.max_recipes,
        )

    print(json.dumps(output, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
