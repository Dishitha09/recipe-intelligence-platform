import html
import re


_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "\ufffd")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value):
    if value is None:
        return None

    text = str(value)

    for _ in range(2):
        text = html.unescape(text)

    text = _repair_mojibake(text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = _WHITESPACE_RE.sub(" ", text)

    return text.strip()


def _repair_mojibake(text):
    if not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text

    try:
        repaired = text.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return text

    if _mojibake_score(repaired) <= _mojibake_score(text):
        return repaired

    return text


def _mojibake_score(text):
    return sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
