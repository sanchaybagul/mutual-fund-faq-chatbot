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
    assert needs_scheme("exit load?")
    assert not needs_scheme("How do I download my capital gains statement?")
    # Definitions are answered from SEBI/AMFI pages, not by asking which scheme.
    assert not needs_scheme("What is an exit load?")
    assert not needs_scheme("What is a riskometer?")
    assert not needs_scheme("Explain expense ratio")
    assert mentions_other_amc("Expense ratio of Axis Small Cap Fund?")
    assert not mentions_other_amc("Expense ratio of HDFC Small Cap Fund?")


def test_clarify_when_scheme_missing():
    assert retrieve("What is the expense ratio?").status == "clarify"


@pytest.mark.parametrize("q", ["What is the capital of France?", "Tell me a joke",
                               "Expense ratio of Axis Small Cap Fund?"])
def test_out_of_scope_not_found(q):
    assert retrieve(q).status == "not_found"


@pytest.mark.parametrize("q,scheme,top_id,field", [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", "HDFC Flexi Cap Fund",
     "hdfc-flexi-cap:expense-ratio-and-fund-size:0", "0.77%"),
    ("Exit load of HDFC Small Cap Fund?", "HDFC Small Cap Fund", "hdfc-small-cap:exit-load:0", "1.00%"),
    ("Minimum SIP for HDFC Balanced Advantage Fund?", "HDFC Balanced Advantage Fund",
     "hdfc-baf:minimum-investment-and-lock-in:0", "₹100"),
    ("Riskometer of HDFC Large Cap?", "HDFC Large Cap Fund",
     "hdfc-large-cap:riskometer-and-benchmark:0", "Very High"),
])
def test_field_questions_rank_the_scheme_page_first(q, scheme, top_id, field):
    r = retrieve(q)
    assert r.status == "ok"
    assert all(c["metadata"]["scheme"] == scheme for c in r.chunks)  # only that scheme's documents
    assert r.chunks[0]["id"] == top_id                              # scheme page section at rank 1
    assert field in r.chunks[0]["text"]                             # and it contains the answer


def test_elss_lock_in_found_in_scheme_documents():
    r = retrieve("ELSS lock-in?")
    assert r.status == "ok"
    assert all(c["metadata"]["scheme"] == "HDFC ELSS Tax Saver Fund" for c in r.chunks)
    assert any("3 years" in c["text"] for c in r.chunks)


@pytest.mark.parametrize("q,slug", [
    ("How do I download my capital gains statement?", "hdfc-capital-gains"),
    ("Is there a charge for the account statement?", "hdfc-cas"),
    ("What is a riskometer?", "sebi-riskometer"),
    ("What is exit load?", "sebi-exit-load"),
    ("What is a lock-in period?", "amfi-lock-in"),
])
def test_general_questions_retrieve_general_sources(q, slug):
    r = retrieve(q)
    assert r.status == "ok"
    assert r.chunks[0]["id"].startswith(slug)


def test_kim_answers_redemption_questions():
    r = retrieve("How long does redemption payout take for HDFC Large Cap Fund?")
    assert r.chunks[0]["id"] == "kim-hdfc-large-cap:redemption-payout-timeline:0"
