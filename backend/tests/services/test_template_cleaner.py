from app.services.analysis.text_cleaner import clean_template_sentences


def test_clean_template_sentences_filters_noise_and_duplicates() -> None:
    raw = (
        "This is a repeated template sentence that appears a lot in feeds. "
        "Short ping. Short ping. Unique topic emerges with detail."
    )

    def df_lookup(sentence: str) -> float:
        if "template sentence" in sentence:
            return 0.35
        return 0.0

    cleaned = clean_template_sentences(raw, df_lookup=df_lookup)

    assert "template sentence" not in cleaned
    assert cleaned.count("Short ping") == 1
    assert "Unique topic emerges" in cleaned
