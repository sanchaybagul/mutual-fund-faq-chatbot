"""Phase 4: MiniLM embeddings. The same model is used for ingestion and queries.

Runs all-MiniLM-L6-v2 through Chroma's bundled ONNX build (onnxruntime + tokenizers) instead
of sentence-transformers, so PyTorch isn't needed and the app fits in 512 MB of RAM. Output
matches sentence-transformers (mean pooling, L2-normalized, 256-token truncation); the model
(~80 MB) downloads to ~/.cache/chroma on first use.
"""
from functools import lru_cache

from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2


@lru_cache
def get_model() -> ONNXMiniLM_L6_V2:
    return ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])


def embed(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in get_model()(texts)]
