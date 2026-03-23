"""
Indexer — builds and persists a dual search index:
  • FAISS IndexFlatIP  (dense vector search, cosine similarity)
  • BM25Okapi           (sparse keyword search)

Both are saved to disk so ingest.py only needs to run when PDFs change.
Retrieval uses Reciprocal Rank Fusion across both indexes.
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
from rank_bm25 import BM25Okapi
from tqdm import tqdm

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import (
    CHUNK_OVERLAP, CHUNK_SIZE, EMBED_DIM, EMBED_MODEL,
    INDEX_DIR, OPENAI_API_KEY,
)

client = OpenAI(api_key=OPENAI_API_KEY)

# ── Saved-file paths ──────────────────────────────────────────────────────────
FAISS_PATH  = INDEX_DIR / "vectors.index"
BM25_PATH   = INDEX_DIR / "bm25.pkl"
CHUNKS_PATH = INDEX_DIR / "chunks.pkl"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    url:      str
    text:     str
    chunk_id: int   = 0
    score:    float = 0.0   # populated during retrieval, not stored in index


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str, url: str) -> List[Chunk]:
    """
    Split page text into overlapping chunks.
    Prefers paragraph boundaries over mid-sentence splits.
    """
    # Normalise whitespace
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    text = re.sub(r"[ \t]+", " ", text)

    chunks, cid, start = [], 0, 0
    while start < len(text):
        end   = min(len(text), start + CHUNK_SIZE)
        piece = text[start:end].strip()

        # Try to end on a paragraph boundary within the last 20 %
        if end < len(text):
            boundary = piece.rfind("\n\n")
            if boundary > CHUNK_SIZE * 0.8:
                end   = start + boundary
                piece = text[start:end].strip()

        if len(piece) > 80:
            chunks.append(Chunk(url=url, text=piece, chunk_id=cid))
            cid += 1

        if end >= len(text):
            break
        start = max(0, end - CHUNK_OVERLAP)

    return chunks


def build_chunks(scraped: dict[str, str]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for url, text in scraped.items():
        chunks.extend(_chunk_text(text, url))
    logger.info(f"Built {len(chunks)} chunks from {len(scraped)} pages")
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_texts(texts: List[str], batch_size: int = 512) -> np.ndarray:
    """Embed texts in batches; returns float32 array of shape (N, EMBED_DIM)."""
    all_vecs: list[list[float]] = []
    for i in tqdm(range(0, len(texts), batch_size), desc="🔢 Embedding batches"):
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + batch_size])
        all_vecs.extend(d.embedding for d in resp.data)
    return np.array(all_vecs, dtype="float32")


# ── Build & save ──────────────────────────────────────────────────────────────

def build_and_save(chunks: List[Chunk]) -> Tuple[faiss.IndexFlatIP, BM25Okapi]:
    """Embed all chunks, build FAISS + BM25, persist everything to INDEX_DIR."""
    texts = [c.text for c in chunks]

    # ── Dense vector index ────────────────────────────────────────────────────
    logger.info(f"Embedding {len(texts)} chunks with {EMBED_MODEL}…")
    vecs = embed_texts(texts)
    faiss.normalize_L2(vecs)            # cosine sim via inner product
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(vecs)
    faiss.write_index(index, str(FAISS_PATH))
    logger.success(f"FAISS index saved ({index.ntotal} vectors, dim={EMBED_DIM})")

    # ── Sparse BM25 index ─────────────────────────────────────────────────────
    logger.info("Building BM25 index…")
    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    BM25_PATH.write_bytes(pickle.dumps(bm25))
    logger.success("BM25 index saved")

    # ── Chunk metadata ────────────────────────────────────────────────────────
    CHUNKS_PATH.write_bytes(pickle.dumps(chunks))
    logger.success(f"Chunk store saved → {len(chunks)} chunks")

    return index, bm25


# ── Load ──────────────────────────────────────────────────────────────────────

def load_index() -> Tuple[faiss.IndexFlatIP, BM25Okapi, List[Chunk]]:
    """Load all index artefacts from disk. Raises FileNotFoundError if missing."""
    if not FAISS_PATH.exists():
        raise FileNotFoundError(
            "No index found. Run `python ingest.py` first to build the index."
        )
    index  = faiss.read_index(str(FAISS_PATH))
    bm25   = pickle.loads(BM25_PATH.read_bytes())
    chunks = pickle.loads(CHUNKS_PATH.read_bytes())
    logger.info(f"Index loaded: {len(chunks)} chunks, {index.ntotal} vectors")
    return index, bm25, chunks
