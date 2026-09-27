from src import templates
from src.postprocess import cap_sentences, contains_advice, finalize, split_sentences

CHUNKS = [{"text": "...", "metadata": {"source_url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
                                       "fetched_at": "2026-09-27"}}]


def test_answer_gets_citation_and_date():
    r = finalize("The exit load is 1% if redeemed within 1 year.", CHUNKS)
    assert r.kind == "answer"
    assert r.citation_url == CHUNKS[0]["metadata"]["source_url"]
    assert r.last_updated == "2026-09-27"
    assert "Last updated from sources: 2026-09-27" in r.render()


def test_not_found_variants():
    for raw in ["NOT_FOUND", "NOT_FOUND.", "**NOT_FOUND**", "NOTFOUND", "not found", ""]:
        assert finalize(raw, CHUNKS).kind == "not_found", raw


def test_llm_urls_are_stripped_citation_from_metadata():
    r = finalize("See https://evil.example.com for details. Expense ratio is 0.78%.", CHUNKS)
    assert "evil" not in r.text and r.citation_url.startswith("https://groww.in")


def test_advice_failsafe():
    r = finalize("The expense ratio is 0.78%. You should invest in this fund.", CHUNKS)
    assert r.kind == "advice" and r.text == templates.ADVICE and r.citation_url == templates.EDU_LINK
    assert not contains_advice("The expense ratio is 0.78%.")


def test_three_sentence_cap_keeps_decimals_and_abbreviations():
    text = ("Expense ratio is 0.78%. Mr. Dhruv Muchhal manages it since Jun 2023. "
            "Tax above Rs 1.25 lakh is 12.5%. Fourth sentence. Fifth.")
    assert split_sentences(text)[1] == "Mr. Dhruv Muchhal manages it since Jun 2023."
    assert cap_sentences(text) == ("Expense ratio is 0.78%. Mr. Dhruv Muchhal manages it since Jun 2023. "
                                   "Tax above Rs 1.25 lakh is 12.5%.")
