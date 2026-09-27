"""Phase 4: ChromaDB wrapper. We always pass our own embeddings (never Chroma's built-in
embedding function), so ingestion and queries are guaranteed to use the same model."""
import shutil

import chromadb
from chromadb.api.client import SharedSystemClient

from src.config import CHROMA_PATH, COLLECTION


def get_client():
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def wipe_store() -> None:
    """Delete the whole on-disk store. Chroma's delete_collection() leaves the old
    index folder behind, so a reset would otherwise accumulate orphaned folders."""
    SharedSystemClient.clear_system_cache()  # drop any cached client pointing at the old files
    shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    (CHROMA_PATH / ".gitkeep").touch()


def get_collection(reset: bool = False):
    if reset:
        wipe_store()
    return get_client().get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}, embedding_function=None
    )


def upsert(chunks, vectors, collection=None) -> None:
    col = collection or get_collection()
    col.upsert(
        ids=[c.id for c in chunks],
        embeddings=vectors,
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
    )


def query(vector: list[float], k: int, where: dict | None = None, collection=None) -> list[dict]:
    """Return hits sorted by similarity: [{id, text, metadata, similarity}]."""
    col = collection or get_collection()
    res = col.query(
        query_embeddings=[vector],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"id": i, "text": doc, "metadata": meta, "similarity": 1 - dist}  # cosine: sim = 1 - distance
        for i, doc, meta, dist in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]


def count() -> int:
    return get_collection().count()
