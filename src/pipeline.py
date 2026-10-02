"""Phase 8: single entry point — answer(question) -> Response (architecture §4.6).

Flow: guardrails → scheme-aware retrieval → Groq LLM → post-processing.
Nothing here logs or stores the user's question.
"""
import json
from functools import lru_cache

from src import templates
from src.config import RAW_DIR
from src.generator import GenerationError, generate
from src.guardrails import classify
from src.loader import load_sources
from src.postprocess import Response, finalize
from src.retriever import retrieve
from src.schemes import detect_schemes

AMC_URL = "https://www.hdfcfund.com"  # official AMC site; used when no scheme is named


def _with_date(source: dict) -> dict:
    meta_path = RAW_DIR / f"{source['slug']}.meta.json"
    fetched = json.loads(meta_path.read_text())["fetched_at"] if meta_path.exists() else None
    return {"url": source["url"], "fetched_at": fetched}


@lru_cache
def scheme_sources() -> dict[str, dict]:
    """scheme name -> {url, fetched_at} of its official scheme page (sources.csv + snapshot metadata)."""
    return {s["scheme"]: _with_date(s) for s in load_sources() if s["source_type"] == "scheme_page"}


@lru_cache
def factsheet_source() -> dict:
    """{url, fetched_at} of the official monthly factsheet; performance questions link here."""
    return next((_with_date(s) for s in load_sources() if s["source_type"] == "factsheet"),
                {"url": AMC_URL, "fetched_at": None})


def scheme_link(question: str) -> tuple[str | None, str | None]:
    """Source page + date for the first scheme named in the question, if any."""
    schemes = detect_schemes(question)
    if not schemes:
        return None, None
    src = scheme_sources().get(schemes[0], {})
    return src.get("url"), src.get("fetched_at")


def answer(question: str) -> Response:
    question = (question or "").strip()
    if not question:
        return Response("off_topic", templates.OFF_TOPIC)

    kind = classify(question)
    if kind == "pii":
        return Response("pii_block", templates.PII_BLOCK)
    if kind == "performance":
        fs = factsheet_source()  # brief: "link to the official factsheet if asked"
        return Response("performance", templates.PERFORMANCE, fs["url"], fs["fetched_at"])
    if kind == "advice":
        return Response("advice", templates.ADVICE, templates.EDU_LINK)
    if kind == "off_topic":
        return Response("off_topic", templates.OFF_TOPIC)

    r = retrieve(question)
    if r.status == "clarify":
        return Response("clarify", templates.CLARIFY)
    if r.status == "not_found":
        return not_found(question)

    try:
        raw = generate(question, r.chunks)
    except GenerationError:
        return Response("error", templates.SERVICE_ERROR)
    resp = finalize(raw, r.chunks)
    # finalize() cites the top chunk; for a scheme-less question that chunk is arbitrary.
    return not_found(question) if resp.kind == "not_found" else resp


def not_found(question: str) -> Response:
    """Link the named scheme's page, or the AMC site when no scheme was named."""
    url, updated = scheme_link(question)
    return Response("not_found", templates.NOT_FOUND, url or AMC_URL, updated)
