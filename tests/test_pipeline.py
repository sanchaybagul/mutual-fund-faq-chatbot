"""PRD §10 acceptance tests: the real pipeline end to end, including real Groq LLM calls.

    pytest tests/test_pipeline.py            # ~15 s (calls Groq)
    pytest -m "not llm"                      # everything except these
"""
import re
from pathlib import Path

import pytest

from src.pipeline import answer
from src.postprocess import split_sentences

# 10 factual questions across all 5 schemes, with a substring the answer must contain
# (values from the official HDFC MF pages snapshotted in data/raw/).
FACTS = [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", "0.77%"),
    ("What is the expense ratio of HDFC Large Cap Fund?", "1.04%"),
    ("What is the lock-in period for HDFC ELSS Tax Saver Fund?", "3 years"),
    ("What is the minimum SIP for HDFC ELSS Tax Saver Fund?", "₹500"),
    ("What is the exit load on HDFC Small Cap Fund?", "1.00%"),
    ("What is the benchmark of HDFC Small Cap Fund?", "BSE 250 SmallCap"),
    ("What is the minimum SIP for HDFC Balanced Advantage Fund?", "₹100"),
    ("What is the exit load of HDFC Balanced Advantage Fund?", "15%"),
    ("What is the riskometer level of HDFC Large Cap Fund?", "Very High"),
    ("Who are the fund managers of HDFC Flexi Cap Fund?", "Dhruv Muchhal"),
]
URL_RE = re.compile(r"https?://")
OFFICIAL = ("https://www.hdfcfund.com/", "https://files.hdfcfund.com/")
APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture(scope="module")
def fact_results():
    return [(q, expected, answer(q)) for q, expected in FACTS]


@pytest.mark.llm
def test_1_factual_accuracy_at_least_9_of_10(fact_results):
    correct = [q for q, expected, r in fact_results if r.kind == "answer" and expected in r.text]
    failures = [(q, r.kind, r.text) for q, expected, r in fact_results if q not in correct]
    assert len(correct) >= 9, f"only {len(correct)}/10 correct: {failures}"


@pytest.mark.llm
def test_1_every_answer_has_one_citation_and_date(fact_results):
    for q, _, r in fact_results:
        assert r.citation_url and r.citation_url.startswith(OFFICIAL), q
        assert not URL_RE.search(r.text), f"extra URL in answer text: {q}"
        assert r.last_updated, q
        assert "Last updated from sources:" in r.render(), q


@pytest.mark.llm
def test_6_answers_at_most_three_sentences(fact_results):
    for q, _, r in fact_results:
        assert len(split_sentences(r.text)) <= 3, f"{q}: {r.text}"


def test_2_advice_refused_with_edu_link():
    r = answer("Should I buy HDFC Small Cap?")
    assert r.kind == "advice" and r.citation_url
    assert "can't give investment advice" in r.text


def test_3_performance_redirects_to_factsheet_without_numbers():
    r = answer("Which fund gave better returns, large cap or flexi cap?")
    assert r.kind == "performance" and "Factsheet" in r.citation_url
    assert not re.search(r"\d+(\.\d+)?\s*%", r.text)  # no computed returns


def test_4_pii_blocked_and_not_echoed():
    r = answer("My PAN is ABCDE1234F, what's my balance?")
    assert r.kind == "pii_block" and "ABCDE1234F" not in r.render()


# Questions answered from the general (non-scheme) sources: HDFC MF service pages, SEBI, AMFI.
GENERAL = [
    ("How do I download my capital gains statement?", "hdfcfund.com/learn/blog/how-get-capital-gain"),
    ("Is there a fee for downloading my account statement?", "hdfcfund.com/services/consolidated-account"),
    ("What is a riskometer?", "investor.sebi.gov.in/riskometer"),
    ("What is exit load?", "investor.sebi.gov.in/exit_load"),
    ("What is a lock-in period?", "mutualfundssahihai.com"),
]


@pytest.mark.llm
@pytest.mark.parametrize("q,url_part", GENERAL)
def test_1_general_questions_cite_the_right_page(q, url_part):
    r = answer(q)
    assert r.kind == "answer", r.text
    assert url_part in r.citation_url
    assert len(split_sentences(r.text)) <= 3


@pytest.mark.llm
def test_5_out_of_corpus_question_not_hallucinated():
    r = answer("Who is the CEO of HDFC Small Cap Fund's AMC?")
    assert r.kind == "not_found"


def test_5_other_amc_not_answered_with_hdfc_data():
    assert answer("Expense ratio of Axis Small Cap Fund?").kind == "not_found"


def test_7_ui_elements_present():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=120).run()
    assert not at.exception
    page = " ".join(m.value for m in at.markdown)
    assert "Ask me facts about 5 HDFC Mutual Fund schemes" in page          # welcome line
    assert at.get("popover")[0].proto.popover.label == "5 schemes · 18 sources"  # source list
    assert "Facts-only. No investment advice." in page                      # disclaimer
    examples = [b for b in at.button if b.key and b.key.startswith("ex_")]
    assert len(examples) >= 3                                               # example questions
    assert any(t.label == "Dark mode" for t in at.toggle)                   # theme toggle


def test_7_theme_toggle_switches_palette():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=120).run()
    assert "--bg: #F4F6FA" in at.markdown[0].value
    at.toggle(key="dark").set_value(True).run()
    assert "--bg: #08111F" in at.markdown[0].value
