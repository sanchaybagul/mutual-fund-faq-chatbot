from collections import Counter

import pytest

from src.chunker import MODEL_MAX_TOKENS, chunk_all, get_tokenizer, split_section
from src.config import CHUNK_TOKENS
from src.parser import parse_all


@pytest.fixture(scope="module")
def docs():
    return parse_all()


@pytest.fixture(scope="module")
def chunks(docs):
    return chunk_all(docs)


def test_chunks_within_model_limit(chunks):
    tok = get_tokenizer()
    for c in chunks:
        n = len(tok.encode(c.text))  # includes [CLS]/[SEP]
        assert n <= MODEL_MAX_TOKENS, f"{c.id} has {n} tokens"


def test_section_chunks_within_target(chunks):
    tok = get_tokenizer()
    for c in chunks:
        if c.metadata["chunk_type"] == "section":
            assert len(tok.encode(c.text, add_special_tokens=False)) <= CHUNK_TOKENS, c.id


def test_every_chunk_has_scheme_prefix(chunks):
    for c in chunks:
        assert c.text.startswith(f"[{c.metadata['scheme']} – Direct Growth] ["), c.id


def test_one_facts_card_per_scheme(docs, chunks):
    cards = Counter(c.metadata["scheme"] for c in chunks if c.metadata["chunk_type"] == "facts_card")
    assert set(cards) == {d.scheme for d in docs}
    assert all(n == 1 for n in cards.values())


def test_ids_unique_and_deterministic(docs, chunks):
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
    assert ids == [c.id for c in chunk_all(docs)]


def test_metadata_complete(chunks):
    keys = {"scheme", "category", "section", "chunk_type", "source_url", "source_type", "fetched_at"}
    for c in chunks:
        assert keys <= c.metadata.keys(), c.id
        assert all(c.metadata[k] for k in keys), c.id


def test_facts_card_contains_key_fields(chunks):
    card = next(c for c in chunks if c.metadata["chunk_type"] == "facts_card"
                and c.metadata["scheme"] == "HDFC ELSS Tax Saver Fund")
    for label in ["Expense ratio:", "Exit load:", "Minimum SIP:", "Lock-in: 3 years", "Riskometer:", "Benchmark:"]:
        assert label in card.text


def test_split_section_keeps_decimals_intact():
    text = " ".join(["The expense ratio is 0.78% and tax is Rs 1.25 lakh."] * 40)
    pieces = split_section(text, budget=60, overlap=10)
    assert len(pieces) > 1
    assert all("0.78%" in p or "1.25" in p for p in pieces)
    assert not any(p.endswith("0.") for p in pieces)
