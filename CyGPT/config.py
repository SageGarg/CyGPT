"""
CyGPT – Central Configuration
All tuneable knobs live here. Change once, applies everywhere.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"
PDF_DIR   = DATA_DIR / "pdfs"       # drop your PDFs here
INDEX_DIR = DATA_DIR / "index"      # auto-created FAISS + BM25 files
CACHE_DIR = DATA_DIR / "cache"      # 7-day disk cache for scraped pages

for _d in [PDF_DIR, INDEX_DIR, CACHE_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

#   text-embedding-3-small  →  1536 dims  (fast, cheap)
#   text-embedding-3-large  →  3072 dims  (best quality, swap below)
EMBED_MODEL = "text-embedding-ada-002"
EMBED_DIM   = 1536
CHAT_MODEL  = "gpt-4o"

# ── Scraping ──────────────────────────────────────────────────────────────────
ALLOWED_DOMAINS: set[str] = {
    "catalog.iastate.edu",
    "pre-health.las.iastate.edu",
    "iastate.edu",
}
MAX_CONCURRENT  = 15     # parallel HTTP connections
REQUEST_TIMEOUT = 20     # seconds per request
MAX_URLS        = 300    # cap per ingestion run

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800   # characters
CHUNK_OVERLAP = 150

# ── Retrieval ─────────────────────────────────────────────────────────────────
TOP_K_RETRIEVE = 30   # candidates from hybrid search before reranking
TOP_K_FINAL    = 10    # chunks shown to GPT after reranking

# Tiny but powerful cross-encoder (≈ 80 MB, downloads once)
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
