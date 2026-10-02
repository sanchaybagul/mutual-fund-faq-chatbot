"""Dump every chunk stored in ChromaDB to data/chunks.md for easy browsing.

    python -m src.export_chunks
"""
from collections import defaultdict

from src.chunker import n_tokens
from src.config import ROOT
from src.store import get_collection

OUT = ROOT / "data" / "chunks.md"


def main() -> None:
    res = get_collection().get(include=["documents", "metadatas"])
    by_doc = defaultdict(list)
    for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
        by_doc[(meta["scheme"], meta["title"])].append((cid, doc, meta))

    lines = ["# Chunks stored in ChromaDB", "",
             f"Collection: `hdfc_mf_faq` · {len(res['ids'])} chunks · "
             f"exported from `data/chroma/`", ""]
    for scheme, title in sorted(by_doc):
        items = sorted(by_doc[(scheme, title)], key=lambda x: (x[2]["chunk_type"] != "facts_card", x[0]))
        meta0 = items[0][2]
        lines += [f"## {title} ({len(items)} chunks)", "",
                  f"Scheme: {scheme} · type: `{meta0['source_type']}` · source: {meta0['source_url']} · "
                  f"fetched {meta0['fetched_at']}", ""]
        for cid, doc, meta in items:
            lines += [f"### `{cid}`", "",
                      f"*{meta['chunk_type']} · section: {meta['section']} · {n_tokens(doc)} tokens*", "",
                      "```text", doc, "```", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(res['ids'])} chunks to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
