"""Phase 4: run the full ingestion pipeline: Load → Parse → Chunk → Embed → Store.

    python -m src.ingest --reset          # rebuild from saved snapshots
    python -m src.ingest --reset --fetch  # re-download pages first
"""
import argparse

from src import chunker, embedder, loader, parser, store

SANITY_QUERIES = [
    ("exit load small cap", "HDFC Small Cap Fund"),
    ("ELSS lock-in period", "HDFC ELSS Tax Saver Fund"),
    ("expense ratio of flexi cap fund", "HDFC Flexi Cap Fund"),
    ("how to download capital gains statement", "General"),
    ("what is a riskometer", "General"),
]


def main(reset: bool = True, fetch: bool = False) -> None:
    if fetch:
        print("Fetching sources…")
        loader.main()

    docs = parser.parse_all()
    chunks = chunker.chunk_all(docs)
    vectors = embedder.embed([c.text for c in chunks])

    collection = store.get_collection(reset=reset)
    store.upsert(chunks, vectors, collection=collection)
    print(f"Ingested {len(chunks)} chunks from {len(docs)} sources "
          f"→ collection count = {collection.count()}")


def sanity_check() -> None:
    from src.retriever import retrieve  # scheme-aware, as the app queries

    print("\nSanity check (scheme-aware top-4):")
    for q, expected in SANITY_QUERIES:
        hits = retrieve(q).chunks
        top = hits[0]["metadata"]["scheme"]
        print(f"\n  Q: {q!r}  → top-1 {'✓' if top == expected else '✗'} (expected {expected})")
        for h in hits:
            print(f"     {h['similarity']:.3f}  {h['id']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the ChromaDB vector store from sources.")
    ap.add_argument("--reset", action="store_true", help="drop and rebuild the collection")
    ap.add_argument("--fetch", action="store_true", help="re-download source pages first")
    args = ap.parse_args()
    main(reset=args.reset, fetch=args.fetch)
    sanity_check()
