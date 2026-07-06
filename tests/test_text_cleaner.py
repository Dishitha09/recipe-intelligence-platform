from services.preprocessing.text_cleaner import clean_text


def test_clean_text_decodes_html_entities_and_whitespace():
    assert clean_text(" fry &amp; serve&nbsp; hot ") == "fry & serve hot"


def test_clean_text_repairs_common_mojibake():
    assert clean_text("saut\u00c3\u00a9 onions") == "saut\u00e9 onions"
    assert clean_text("\u00c2\u00bc to \u00e2\u2026\u201c cup water") == (
        "\u00bc to \u2153 cup water"
    )
