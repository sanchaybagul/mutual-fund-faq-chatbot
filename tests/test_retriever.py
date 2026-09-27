import pytest

from src.retriever import retrieve
from src.schemes import detect_schemes, mentions_other_amc, needs_scheme


@pytest.mark.parametrize("q,expected", [
    ("Expense ratio of HDFC Large Cap Fund?", ["HDFC Large Cap Fund"]),
    ("hdfc top 100 fund manager", ["HDFC Large Cap Fund"]),
    ("exit load of flexi-cap", ["HDFC Flexi Cap Fund"]),
    ("HDFC Equity Fund expense ratio", ["HDFC Flexi Cap Fund"]),
    ("ELSS lock-in?", ["HDFC ELSS Tax Saver Fund"]),
    ("minimum SIP for tax saver", ["HDFC ELSS Tax Saver Fund"]),
    ("smallcap benchmark", ["HDFC Small Cap Fund"]),
    ("HDFC Small Cap Fund riskometer", ["HDFC Small Cap Fund"]),
    ("BAF minimum SIP", ["HDFC Balanced Advantage Fund"]),
    ("balanced advantage exit load", ["HDFC Balanced Advantage Fund"]),
    ("large cap vs small cap exit load", ["HDFC Large Cap Fund", "HDFC Small Cap Fund"]),
    ("How do I download my capital gains statement?", []),
])
def test_detect_schemes(q, expected):
    assert detect_schemes(q) == expected


def test_bluechip_is_not_an_alias():
    assert detect_schemes("SBI Bluechip Fund NAV") == []


def test_needs_scheme_and_other_amc():
    assert needs_scheme("What is the expense ratio?")
    assert not needs_scheme("How do I download my capital gains statement?")
    assert mentions_other_amc("Expense ratio of Axis Small Cap Fund?")
    assert not mentions_other_amc("Expense ratio of HDFC Small Cap Fund?")


def test_clarify_when_scheme_missing():
    assert retrieve("What is the expense ratio?").status == "clarify"


@pytest.mark.parametrize("q", ["What is the capital of France?", "Tell me a joke",
                               "Expense ratio of Axis Small Cap Fund?"])
def test_out_of_scope_not_found(q):
    assert retrieve(q).status == "not_found"


@pytest.mark.parametrize("q,slug,field", [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", "hdfc-flexi-cap", "Expense ratio: 0.77%"),
    ("ELSS lock-in?", "hdfc-elss", "Lock-in: 3 years"),
    ("Exit load of HDFC Small Cap Fund?", "hdfc-small-cap", "Exit load"),
    ("Minimum SIP for HDFC Balanced Advantage Fund?", "hdfc-baf", "₹100"),
    ("Riskometer of HDFC Large Cap?", "hdfc-large-cap", "Very High"),
])
def test_field_questions_retrieve_right_scheme_and_fact(q, slug, field):
    r = retrieve(q)
    assert r.status == "ok"
    assert r.chunks[0]["id"].startswith(slug)          # right scheme at rank 1
    assert any(c["id"] == f"{slug}:key-facts:0" for c in r.chunks)  # facts card in top-k
    assert field in r.chunks[0]["text"]                # rank-1 chunk contains the answer
