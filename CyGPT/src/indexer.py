"""
Indexer — builds FAISS + BM25 dual index.

Fixes applied:
  • Overlap now scales with chunk_size for PDFs (was stuck at web-page size,
    causing table rows at chunk boundaries to be orphaned)
  • [TABLE] and [HEADER] metadata tags actually injected (were promised in
    docstring but never implemented — reranker was blind to table content)
  • Boilerplate filter unchanged (already loosened in v2)
"""
from __future__ import annotations

import pickle
import re
import sys
import pathlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
from loguru import logger
from openai import OpenAI
from rank_bm25 import BM25Okapi
from tqdm import tqdm
from dotenv import load_dotenv
import os

load_dotenv()

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import (
    CHUNK_OVERLAP, CHUNK_SIZE, EMBED_DIM, EMBED_MODEL,
    INDEX_DIR, OPENAI_API_KEY,
)

client = OpenAI(api_key=OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))

FAISS_PATH  = INDEX_DIR / "vectors.index"
BM25_PATH   = INDEX_DIR / "bm25.pkl"
CHUNKS_PATH = INDEX_DIR / "chunks.pkl"


@dataclass
class Chunk:
    url:      str
    text:     str
    chunk_id: int   = 0
    score:    float = 0.0


# ── Boilerplate filter (LOOSENED) ─────────────────────────────────────────────
# Only reject pure navigation menus, not content tables

_NAV_PHRASES = [
    "a-z courses", "registration and policies",
    "exchange programs and study abroad",
    "programs, certificates, minors",
    "search catalog", "skip to main content",
]

def _is_boilerplate(text: str) -> bool:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return True

    lower = text.lower()

    # Only reject if MANY nav phrases present
    nav_hits = sum(1 for p in _NAV_PHRASES if p in lower)
    if nav_hits >= 4:
        return True

    # Reject pure link lists (every line is a URL)
    url_lines = sum(1 for l in lines if l.startswith("http"))
    if url_lines / len(lines) > 0.8:
        return True

    # Must have at least some substance
    if len(text.strip()) < 60:
        return True

    return False


# ── Section-aware chunking ─────────────────────────────────────────────────────

_SECTION_BREAKS = re.compile(
    r"(\n(?=#{1,3}\s))"
    r"|(\n(?=[A-Z][a-z]+ Year\b))"
    r"|(\n(?=Fall\s+Credits))"
    r"|(\[PDF:.*?\|.*?Page \d+\])",
    re.MULTILINE
)

# FIX #6: Detect table-like content (3+ pipe separators on a line) and
# header content (**bold** markers from pdf_parser) to inject metadata tags.
def _classify_chunk(text: str) -> str:
    """Return a metadata prefix tag for the chunk, or empty string."""
    pipe_lines = sum(1 for line in text.splitlines() if line.count("|") >= 3)
    if pipe_lines >= 2:
        return "[TABLE] "
    if "**" in text:
        return "[HEADER] "
    return ""


def _chunk_text(text: str, url: str) -> List[Chunk]:
    """
    Split text into chunks, preferring breaks at:
    1. Page boundaries ([PDF: ... | Page N])
    2. Year headers (Freshman Year, Sophomore Year)
    3. Section headers (## Header)
    4. Paragraph breaks (\n\n)
    5. Hard character limit as last resort

    FIX #2: overlap now scales with chunk_size for PDF sources.
    Previously overlap stayed at CHUNK_OVERLAP (web-page size) even when
    chunk_size doubled for PDFs — table rows at boundaries were orphaned.
    """
    is_pdf = url.startswith("pdf::")
    chunk_size = CHUNK_SIZE * 2 if is_pdf else CHUNK_SIZE
    # FIX #2: Scale overlap proportionally for PDFs
    overlap = CHUNK_OVERLAP * 2 if is_pdf else CHUNK_OVERLAP

    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    text = re.sub(r"[ \t]+", " ", text)

    if not text:
        return []

    chunks = []
    cid    = 0
    start  = 0

    while start < len(text):
        end = min(len(text), start + chunk_size)
        piece = text[start:end]

        if end < len(text):
            # Priority 1: break at page boundary
            pb = piece.rfind("[PDF:")
            if pb > chunk_size * 0.3:
                end = start + pb
                piece = text[start:end]
            else:
                # Priority 2: break at Year header
                yb = max(
                    piece.rfind("\nFreshman"),
                    piece.rfind("\nSophomore"),
                    piece.rfind("\nJunior"),
                    piece.rfind("\nSenior"),
                )
                if yb > chunk_size * 0.3:
                    end = start + yb
                    piece = text[start:end]
                else:
                    # Priority 3: paragraph break
                    pb2 = piece.rfind("\n\n")
                    if pb2 > chunk_size * 0.5:
                        end = start + pb2
                        piece = text[start:end]

        piece = piece.strip()
        if len(piece) > 80 and not _is_boilerplate(piece):
            # FIX #6: Prepend metadata tag so reranker knows content type
            tag = _classify_chunk(piece)
            chunks.append(Chunk(url=url, text=tag + piece, chunk_id=cid))
            cid += 1

        if end >= len(text):
            break
        start = max(0, end - overlap)

    return chunks


def build_chunks(scraped: dict[str, str]) -> List[Chunk]:
    chunks: List[Chunk] = []
    rejected = 0
    for url, text in scraped.items():
        before = len(chunks)
        chunks.extend(_chunk_text(text, url))
        if len(chunks) == before:
            rejected += 1

    logger.info(
        f"Built {len(chunks)} chunks from {len(scraped)} sources "
        f"({rejected} sources fully rejected)"
    )
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_texts(texts: List[str], batch_size: int = 512) -> np.ndarray:
    all_vecs: list[list[float]] = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + batch_size])
        all_vecs.extend(d.embedding for d in resp.data)
    return np.array(all_vecs, dtype="float32")


# ── Build & save ──────────────────────────────────────────────────────────────

def build_and_save(chunks: List[Chunk]) -> Tuple[faiss.IndexFlatIP, BM25Okapi]:
    texts = [c.text for c in chunks]

    logger.info(f"Embedding {len(texts)} chunks...")
    vecs = embed_texts(texts)
    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(vecs)
    faiss.write_index(index, str(FAISS_PATH))
    logger.success(f"FAISS index saved ({index.ntotal} vectors)")

    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    BM25_PATH.write_bytes(pickle.dumps(bm25))
    logger.success("BM25 index saved")

    CHUNKS_PATH.write_bytes(pickle.dumps(chunks))
    logger.success(f"Chunks saved: {len(chunks)}")

    return index, bm25


# ── Load ──────────────────────────────────────────────────────────────────────

def load_index() -> Tuple[faiss.IndexFlatIP, BM25Okapi, List[Chunk]]:
    if not FAISS_PATH.exists():
        raise FileNotFoundError("No index found. Run `python ingest.py` first.")
    index  = faiss.read_index(str(FAISS_PATH))
    bm25   = pickle.loads(BM25_PATH.read_bytes())
    chunks = pickle.loads(CHUNKS_PATH.read_bytes())
    logger.info(f"Index loaded: {len(chunks)} chunks, {index.ntotal} vectors")
    return index, bm25, chunks
