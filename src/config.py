"""Central configuration: paths, model names, thresholds, and env-driven settings."""
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()


def _setting(name: str, default: str = "") -> str:
    """Env var / .env first, then Streamlit Cloud secrets (for hosted deployments)."""
    if os.getenv(name):
        return os.getenv(name)
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:  # no secrets file, or not running under Streamlit
        return default


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CHROMA_PATH = ROOT / "data" / "chroma"
SOURCES_CSV = ROOT / "sources.csv"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION = "hdfc_mf_faq"
TOP_K = int(os.getenv("TOP_K", 4))
SIM_THRESHOLD = float(os.getenv("SIM_THRESHOLD", 0.25))  # tuned in Phase 5: in-scope min 0.280, out-of-scope max 0.197
CHUNK_TOKENS, CHUNK_OVERLAP = 200, 30

GROQ_API_KEY = _setting("GROQ_API_KEY")
GROQ_MODEL = _setting("GROQ_MODEL") or "qwen/qwen3.8-27b"
USE_LLM_INTENT = os.getenv("USE_LLM_INTENT", "false").lower() == "true"
