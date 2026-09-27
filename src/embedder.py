"""Phase 4: sentence-transformers wrapper. The same model is used for ingestion and queries."""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from src.config import EMBED_MODEL


@lru_cache
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    return get_model().encode(texts, normalize_embeddings=True).tolist()
