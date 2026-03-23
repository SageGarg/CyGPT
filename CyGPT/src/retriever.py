"""
Retriever — three-stage pipeline:

  1. Query Expansion  – GPT-4o-mini rewrites the question into N variants
  2. Hybrid Search    – Dense FAISS + Sparse BM25 fused via Reciprocal Rank Fusion
  3. OpenAI Reranking – GPT-4o-mini scores each candidate passage (no local model,
                        avoids the macOS PyTorch segfault from sentence-transformers)
"""
from __future__ import annotations

import json
import re
import sys
import pathlib
from typing import List

import faiss
import numpy as np
from loguru import logger
from openai import OpenAI
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import (
    EMBED_MODEL, OPENAI_API_KEY,
    TOP_K_FINAL, TOP_K_RETRIEVE,
)
from src.indexer import Chunk, embed_texts

client = OpenAI(api_key=OPENAI_API_KEY)


# ── 1. Query Expansion ────────────────────────────────────────────────────────

def expand_query(question: str, n: int = 3) -> List[str]:
    """Ask GPT-4o-mini to rephrase the question in N different ways."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You generate {n} alternative search queries for an Iowa State "
                        f"University catalog Q&A system. "
                        f"Return ONLY a JSON array of {n} strings. No preamble."
                    ),
                },
                {"role": "user", "content": f"Original question: {question}"},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content or "[]"
        match = re.search(r"\[.*?\]", raw, re.S)
        if match:
            variants = json.loads(match.group())
            return [question] + [str(v) for v in variants[:n]]
    except Exception as e:
        logger.debug(f"Query expansion failed (non-fatal): {e}")
    return [question]


# ── 2. Hybrid Search with RRF ─────────────────────────────────────────────────

def _rrf(rankings: List[List[int]], k: int = 60) -> List[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda d: scores[d], reverse=True)


def _vector_search(query: str, index: faiss.IndexFlatIP, k: int) -> List[int]:
    vec = embed_texts([query])
    faiss.normalize_L2(vec)
    _, ids = index.search(vec, k)
    return [i for i in ids[0].tolist() if i != -1]


def _bm25_search(query: str, bm25: BM25Okapi, k: int) -> List[int]:
    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)
    return np.argsort(scores)[::-1][:k].tolist()


# ── 3. OpenAI Reranker (replaces sentence-transformers cross-encoder) ─────────

def _rerank_openai(question: str, candidates: List[Chunk]) -> List[Chunk]:
    """
    Ask GPT-4o-mini to score each passage 1-10 on relevance.
    Single API call for all candidates. Falls back to RRF order on failure.
    """
    if not candidates:
        return candidates

    snippets = "\n\n".join(
        f"[{i}] {c.text[:400]}" for i, c in enumerate(candidates)
    )
    prompt = (
        f"Question: {question}\n\n"
        f"Rate each passage on relevance to the question (1=irrelevant, 10=perfect match).\n"
        f"Return ONLY a JSON array of numbers in passage order. Example: [7,3,9,2]\n\n"
        f"{snippets}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content or "[]"
        match = re.search(r"\[[\d,\s.]+\]", raw)
        if match:
            scores = json.loads(match.group())
            if len(scores) == len(candidates):
                for chunk, score in zip(candidates, scores):
                    chunk.score = float(score)
                return sorted(candidates, key=lambda c: c.score, reverse=True)
    except Exception as e:
        logger.debug(f"OpenAI reranker failed (using RRF order): {e}")

    for i, chunk in enumerate(candidates):
        chunk.score = float(len(candidates) - i)
    return candidates


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(
    question:  str,
    index:     faiss.IndexFlatIP,
    bm25:      BM25Okapi,
    chunks:    List[Chunk],
    expand:    bool = True,
) -> List[Chunk]:
    queries = expand_query(question) if expand else [question]
    logger.debug(f"Using {len(queries)} query variant(s): {queries}")

    vector_rankings: List[List[int]] = []
    bm25_rankings:   List[List[int]] = []

    for q in queries:
        vector_rankings.append(_vector_search(q, index, TOP_K_RETRIEVE))
        bm25_rankings.append(_bm25_search(q, bm25, TOP_K_RETRIEVE))

    fused_ids  = _rrf(vector_rankings + bm25_rankings)[:TOP_K_RETRIEVE]
    candidates = [chunks[i] for i in fused_ids]

    reranked = _rerank_openai(question, candidates)[:TOP_K_FINAL]

    logger.info(
        f"Retrieved {len(reranked)} chunks | "
        f"top score={reranked[0].score:.1f}/10 | "
        f"query='{question[:60]}'"
    )
    return reranked