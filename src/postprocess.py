"""Phase 6: enforce the answer contract on raw LLM output.

≤3 sentences, advice fail-safe, exactly one citation from chunk metadata (never from
LLM text), and a "Last updated from sources" date.
"""
import re
from dataclasses import dataclass
from typing import Literal

from src import templates

ResponseKind = Literal["answer", "not_found", "advice", "performance",
                       "pii_block", "off_topic", "clarify", "error"]

ADVICE_PHRASES = ["you should", "i recommend", "we recommend", "recommended for you",
                  "better option", "good investment", "ideal for you", "worth investing",
                  "consider investing", "should invest", "should buy", "should sell"]

# Tokens ending in "." that don't end a sentence.
ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "rs", "no", "st", "ltd", "pvt", "vs", "etc",
                 "i.e", "e.g", "inc", "co", "jr", "sr"}


@dataclass
class Response:
    kind: ResponseKind
    text: str
    citation_url: str | None = None
    last_updated: str | None = None

    def render(self) -> str:
        out = [self.text]
        if self.citation_url:
            out.append(f"Source: {self.citation_url}")
        if self.last_updated:
            out.append(f"Last updated from sources: {self.last_updated}")
        return "\n".join(out)


def split_sentences(text: str) -> list[str]:
    # Split on . ! ? + whitespace + capital/quote/₹, so "0.78%" and "Rs 1.25" stay intact...
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(₹])", text.strip())
    # ...then re-join pieces that were split after an abbreviation like "Mr." or "Pvt.".
    merged = []
    for p in parts:
        if merged:
            last_word = merged[-1].rstrip(".").split()[-1].lower() if merged[-1].split() else ""
            if last_word in ABBREVIATIONS:
                merged[-1] += " " + p
                continue
        merged.append(p)
    return [s for s in merged if s]


def cap_sentences(text: str, n: int = 3) -> str:
    return " ".join(split_sentences(text)[:n])


def contains_advice(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in ADVICE_PHRASES)


def clean_llm_text(raw: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)       # stray reasoning tags
    text = re.sub(r"https?://\S+", "", text)                        # the system adds the link
    text = re.sub(r"[*`#]+", "", text)                              # markdown noise (keep "_" for NOT_FOUND)
    return re.sub(r"\s+", " ", text).strip()


def finalize(raw: str, chunks: list[dict]) -> Response:
    top = chunks[0]["metadata"] if chunks else {}
    url, updated = top.get("source_url"), top.get("fetched_at")
    text = clean_llm_text(raw)

    if not text or re.sub(r"[^A-Z]", "", text.upper()).startswith("NOTFOUND"):
        return Response("not_found", templates.NOT_FOUND, url, updated)
    if contains_advice(text):
        return Response("advice", templates.ADVICE, templates.EDU_LINK, None)
    return Response("answer", cap_sentences(text), url, updated)
