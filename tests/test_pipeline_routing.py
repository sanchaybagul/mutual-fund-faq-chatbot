"""Routing tests for answer(); the LLM call is stubbed so these run fast and offline."""
import pytest

from src import pipeline, templates
from src.generator import GenerationError


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    def fake_generate(question, chunks):
        calls.append(question)
        return "The exit load is 1% if redeemed within 1 year."
    monkeypatch.setattr(pipeline, "generate", fake_generate)
    return calls


def test_fact_goes_through_llm_with_citation(fake_llm):
    r = pipeline.answer("What is the exit load on HDFC Small Cap Fund?")
    assert r.kind == "answer" and fake_llm
    assert r.citation_url == "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
    assert r.last_updated


@pytest.mark.parametrize("q,kind", [
    ("My PAN is ABCDE1234F", "pii_block"),
    ("Should I buy HDFC Small Cap?", "advice"),
    ("Which fund gave better returns, large cap or flexi cap?", "performance"),
    ("Tell me a joke", "off_topic"),
    ("What is the expense ratio?", "clarify"),
    ("Expense ratio of Axis Small Cap Fund?", "not_found"),
    ("", "off_topic"),
])
def test_non_llm_routes_never_call_llm(fake_llm, q, kind):
    r = pipeline.answer(q)
    assert r.kind == kind
    assert fake_llm == []


def test_refusal_links():
    assert pipeline.answer("Should I buy HDFC ELSS?").citation_url == templates.EDU_LINK
    perf = pipeline.answer("What were the returns of HDFC ELSS?")
    assert perf.citation_url == "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth"
    assert pipeline.answer("How have HDFC funds performed?").citation_url == pipeline.AMC_URL


def test_pii_block_has_no_link_and_no_echo():
    r = pipeline.answer("my phone is 9876543210, what's the exit load?")
    assert r.kind == "pii_block" and r.citation_url is None and "9876543210" not in r.text


def test_llm_failure_returns_friendly_error(monkeypatch):
    def boom(q, c):
        raise GenerationError("down")
    monkeypatch.setattr(pipeline, "generate", boom)
    r = pipeline.answer("What is the exit load on HDFC Small Cap Fund?")
    assert r.kind == "error" and r.text == templates.SERVICE_ERROR


def test_not_found_without_scheme_links_amc_site(monkeypatch):
    monkeypatch.setattr(pipeline, "generate", lambda q, c: "NOT_FOUND")
    r = pipeline.answer("How do I download my capital gains statement?")
    assert r.kind == "not_found" and r.citation_url == pipeline.AMC_URL
    r = pipeline.answer("Who is the CEO of HDFC Small Cap Fund's AMC?")
    assert r.citation_url == "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
