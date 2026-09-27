"""Phase 3: turn SchemeDocs into section-aware chunks with a context prefix and metadata.

Rules (architecture §3.3):
- One "facts card" chunk per scheme with all key fields as `Label: value` lines.
- One chunk per section if it fits in CHUNK_TOKENS; otherwise split by paragraph,
  then sentence, packing up to CHUNK_TOKENS with ~CHUNK_OVERLAP tokens of overlap.
- Every chunk starts with `[<Scheme> – Direct Growth] [<Section>]`.
- Token counts use the MiniLM tokenizer (hard model limit: 256 incl. special tokens).
"""
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from transformers import AutoTokenizer

from src.config import CHUNK_OVERLAP, CHUNK_TOKENS, EMBED_MODEL
from src.parser import SchemeDoc, parse_all

MODEL_MAX_TOKENS = 256

FACTS_CARD_FIELDS = [
    ("Category", "category"),
    ("Plan", "plan_type"),
    ("Expense ratio", "expense_ratio"),
    ("Exit load", "exit_load"),
    ("Minimum SIP", "min_sip"),
    ("Minimum lumpsum", "min_lumpsum"),
    ("Lock-in", "lock_in"),
    ("Riskometer", "riskometer"),
    ("Benchmark", "benchmark_short"),
    ("Fund size (AUM)", "aum"),
    ("Fund managers", "fund_managers"),
    ("Launch date", "launch_date"),
]


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict


@lru_cache
def get_tokenizer():
    tok = AutoTokenizer.from_pretrained(EMBED_MODEL)
    tok.model_max_length = 10**6  # we count long texts on purpose; silence truncation warnings
    return tok


def n_tokens(text: str) -> int:
    return len(get_tokenizer().encode(text, add_special_tokens=False))


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def prefix(doc: SchemeDoc, section: str) -> str:
    return f"[{doc.scheme} – Direct Growth] [{section}]"


def base_metadata(doc: SchemeDoc, section: str, chunk_type: str) -> dict:
    return {
        "scheme": doc.scheme,
        "category": doc.category,
        "section": section,
        "chunk_type": chunk_type,
        "source_url": doc.source_url,
        "source_type": doc.source_type,
        "fetched_at": doc.fetched_at,
    }


def make_facts_card(doc: SchemeDoc) -> Chunk:
    section = "Key Facts"
    lines = [f"{label}: {doc.fields[key]}" for label, key in FACTS_CARD_FIELDS if doc.fields.get(key)]
    text = prefix(doc, section) + "\n" + "\n".join(lines)
    return Chunk(
        id=f"{doc.slug}:key-facts:0",
        text=text,
        metadata=base_metadata(doc, section, "facts_card"),
    )


def split_sentences(text: str) -> list[str]:
    # Split on . ! ? followed by whitespace and a capital/quote, so "0.78%" and "Rs 1.25" stay intact.
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(₹])", text) if s.strip()]


def split_long_piece(piece: str, budget: int) -> list[str]:
    """Last resort for a single sentence over budget: pack by words."""
    out, cur = [], []
    for word in piece.split():
        if cur and n_tokens(" ".join(cur + [word])) > budget:
            out.append(" ".join(cur))
            cur = []
        cur.append(word)
    if cur:
        out.append(" ".join(cur))
    return out


def split_section(text: str, budget: int, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into pieces of <= budget tokens, preferring paragraph then sentence boundaries."""
    if n_tokens(text) <= budget:
        return [text]

    units = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        if n_tokens(para) <= budget:
            units.append(para)
        else:
            for sent in split_sentences(para):
                units.extend([sent] if n_tokens(sent) <= budget else split_long_piece(sent, budget))

    pieces, cur = [], []
    for unit in units:
        if cur and n_tokens(" ".join(cur + [unit])) > budget:
            pieces.append(" ".join(cur))
            # Carry trailing units (up to `overlap` tokens) into the next piece for context.
            carry = []
            for prev in reversed(cur):
                if n_tokens(" ".join([prev] + carry)) > overlap:
                    break
                carry.insert(0, prev)
            cur = carry if n_tokens(" ".join(carry + [unit])) <= budget else []
        cur.append(unit)
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def chunk_doc(doc: SchemeDoc) -> list[Chunk]:
    chunks = [make_facts_card(doc)]
    for section, body in doc.sections.items():
        head = prefix(doc, section)
        budget = CHUNK_TOKENS - n_tokens(head) - 1  # -1 for the newline joining head and body
        for i, piece in enumerate(split_section(body, budget)):
            chunks.append(Chunk(
                id=f"{doc.slug}:{slugify(section)}:{i}",
                text=f"{head}\n{piece}",
                metadata=base_metadata(doc, section, "section"),
            ))
    return chunks


def chunk_all(docs: list[SchemeDoc] | None = None) -> list[Chunk]:
    docs = docs if docs is not None else parse_all()
    return [c for d in docs for c in chunk_doc(d)]


def main() -> None:
    chunks = chunk_all()
    per_scheme = Counter(c.metadata["scheme"] for c in chunks)
    sizes = [n_tokens(c.text) for c in chunks]

    print(f"Total chunks: {len(chunks)}  (tokens: min {min(sizes)}, max {max(sizes)}, "
          f"avg {sum(sizes) // len(sizes)})\n")
    for scheme, n in per_scheme.items():
        print(f"  {scheme:<32} {n} chunks")

    print("\n--- Sample: facts card ---")
    print(chunks[0].text)
    print("\n--- Sample: section chunk ---")
    sample = next(c for c in chunks if c.metadata["section"] == "Exit Load, Stamp Duty and Tax")
    print(sample.id, sample.metadata)
    print(sample.text)

    split = [c for c in chunks if not c.id.endswith(":0") or
             any(o.id == c.id[:-1] + "1" for o in chunks)]
    if split:
        print("\n--- Sections split into multiple chunks ---")
        for c in split:
            print(f"  {c.id:<48} {n_tokens(c.text)} tokens")


if __name__ == "__main__":
    main()
