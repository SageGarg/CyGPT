"""
Indexer — builds and persists a dual search index:
  • FAISS IndexFlatIP  (dense vector search, cosine similarity)
  • BM25Okapi          (sparse keyword search)

Includes a quality filter to reject boilerplate/nav chunks before indexing.
"""
from __future__ import annotations

import pickle
import re
import sys
import pathlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from rank_bm25 import BM25Okapi
from tqdm import tqdm

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import (
    CHUNK_OVERLAP, CHUNK_SIZE, EMBED_DIM, EMBED_MODEL,
    INDEX_DIR, OPENAI_API_KEY,
)

client = OpenAI(api_key=OPENAI_API_KEY)

FAISS_PATH  = INDEX_DIR / "vectors.index"
BM25_PATH   = INDEX_DIR / "bm25.pkl"
CHUNKS_PATH = INDEX_DIR / "chunks.pkl"


@dataclass
class Chunk:
    url:      str
    text:     str
    chunk_id: int   = 0
    score:    float = 0.0


# ── Quality filter ────────────────────────────────────────────────────────────

# Nav phrases that appear repeatedly in ISU catalog boilerplate
_NAV_PHRASES = [
    "graduate college", "a-z courses", "registration and policies",
    "exchange programs and study abroad", "academic conduct",
    "veterinary medicine", "programs, certificates, minors",
]

def _is_boilerplate(text: str) -> bool:
    """
    Returns True if a chunk looks like navigation/boilerplate rather than
    real content. Heuristics:
      • Too many very short lines relative to total lines (nav menus)
      • Contains 3+ known ISU nav phrases
      • Average line length too short (pure link lists)
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return True

    # Reject if average line length is very short (nav menu pattern)
    avg_len = sum(len(l) for l in lines) / len(lines)
    if avg_len < 25 and len(lines) > 6:
        return True

    # Reject if >60% of lines are under 30 chars (bullet nav lists)
    short_lines = sum(1 for l in lines if len(l) < 30)
    if short_lines / len(lines) > 0.60 and len(lines) > 8:
        return True

    # Reject if contains multiple known nav phrases
    lower = text.lower()
    nav_hits = sum(1 for p in _NAV_PHRASES if p in lower)
    if nav_hits >= 3:
        return True

    return False


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str, url: str) -> List[Chunk]:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    text = re.sub(r"[ \t]+", " ", text)

    chunks, cid, start = [], 0, 0
    while start < len(text):
        end   = min(len(text), start + CHUNK_SIZE)
        piece = text[start:end].strip()

        if end < len(text):
            boundary = piece.rfind("\n\n")
            if boundary > CHUNK_SIZE * 0.8:
                end   = start + boundary
                piece = text[start:end].strip()

        if len(piece) > 80 and not _is_boilerplate(piece):
            chunks.append(Chunk(url=url, text=piece, chunk_id=cid))
            cid += 1

        if end >= len(text):
            break
        start = max(0, end - CHUNK_OVERLAP)

    return chunks


def build_chunks(scraped: dict[str, str]) -> List[Chunk]:
    chunks: List[Chunk] = []
    rejected = 0
    for url, text in scraped.items():
        before = len(chunks)
        chunks.extend(_chunk_text(text, url))
        added = len(chunks) - before
        if added == 0:
            rejected += 1

    logger.info(
        f"Built {len(chunks)} chunks from {len(scraped)} sources "
        f"({rejected} sources rejected as boilerplate)"
    )
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_texts(texts: List[str], batch_size: int = 512) -> np.ndarray:
    all_vecs: list[list[float]] = []
    for i in tqdm(range(0, len(texts), batch_size), desc="🔢 Embedding batches"):
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + batch_size])
        all_vecs.extend(d.embedding for d in resp.data)
    return np.array(all_vecs, dtype="float32")


# ── Build & save ──────────────────────────────────────────────────────────────

def build_and_save(chunks: List[Chunk]) -> Tuple[faiss.IndexFlatIP, BM25Okapi]:
    texts = [c.text for c in chunks]

    logger.info(f"Embedding {len(texts)} chunks with {EMBED_MODEL}…")
    vecs = embed_texts(texts)
    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(vecs)
    faiss.write_index(index, str(FAISS_PATH))
    logger.success(f"FAISS index saved ({index.ntotal} vectors)")

    logger.info("Building BM25 index…")
    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    BM25_PATH.write_bytes(pickle.dumps(bm25))
    logger.success("BM25 index saved")

    CHUNKS_PATH.write_bytes(pickle.dumps(chunks))
    logger.success(f"Chunk store saved → {len(chunks)} chunks")

    return index, bm25


# ── Load ──────────────────────────────────────────────────────────────────────

def load_index() -> Tuple[faiss.IndexFlatIP, BM25Okapi, List[Chunk]]:
    if not FAISS_PATH.exists():
        raise FileNotFoundError(
            "No index found. Run `python ingest.py` first."
        )
    index  = faiss.read_index(str(FAISS_PATH))
    bm25   = pickle.loads(BM25_PATH.read_bytes())
    chunks = pickle.loads(CHUNKS_PATH.read_bytes())
    logger.info(f"Index loaded: {len(chunks)} chunks, {index.ntotal} vectors")
    return index, bm25, chunks
