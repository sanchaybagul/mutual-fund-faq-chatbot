"""Phase 5: scheme-aware retrieval over ChromaDB.

    python -m src.retriever "exit load of hdfc small cap"
"""
import sys
from dataclasses import dataclass, field
from typing import Literal

from src.config import SIM_THRESHOLD, TOP_K
from src.embedder import embed
from src.schemes import detect_schemes, mentions_other_amc, needs_scheme
from src.store import query


@dataclass
class RetrievalResult:
    status: Literal["ok", "not_found", "clarify"]
    chunks: list[dict] = field(default_factory=list)  # {id, text, metadata, similarity}
    schemes: list[str] = field(default_factory=list)


def retrieve(question: str, k: int = TOP_K, threshold: float = SIM_THRESHOLD) -> RetrievalResult:
    schemes = detect_schemes(question)

    # "SBI Small Cap" must not silently answer with HDFC Small Cap.
    if mentions_other_amc(question):
        return RetrievalResult("not_found", [], schemes)
    if not schemes and needs_scheme(question):
        return RetrievalResult("clarify", [], schemes)

    vec = embed([question])[0]
    if len(schemes) == 1:
        hits = query(vec, k, where={"scheme": schemes[0]})
    elif len(schemes) > 1:
        per = max(2, k // len(schemes))
        hits = [h for s in schemes for h in query(vec, per, where={"scheme": s})]
        hits.sort(key=lambda h: -h["similarity"])
    else:
        hits = query(vec, k)

    if not hits or hits[0]["similarity"] < threshold:
        return RetrievalResult("not_found", hits, schemes)
    return RetrievalResult("ok", hits, schemes)


def main() -> None:
    q = " ".join(sys.argv[1:]) or "What is the exit load of HDFC Small Cap Fund?"
    r = retrieve(q)
    print(f"Q: {q}\nstatus: {r.status} | schemes: {r.schemes}")
    for h in r.chunks:
        print(f"  {h['similarity']:.3f}  {h['id']}")


if __name__ == "__main__":
    main()
