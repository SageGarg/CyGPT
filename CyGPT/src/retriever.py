"""
Retriever — three-stage pipeline.

Fixes applied:
  • _normalize_query(): Pads terse keyword queries (<= 3 words) into full
    natural-language questions before expansion and reranking — fixes the
    "colleges in isu" → fallback failure reported in production.
  • _boost_exact_matches(): Only boosts chunks already scoring >= 5.0 so a
    weak chunk (score 2/10) with a code match can't leapfrog a strong
    chunk (score 9/10) that also answers the question.
  • stream_answer history slice: Ensures we never start mid-turn.
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
from dotenv import load_dotenv
import os

load_dotenv()

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import EMBED_MODEL, OPENAI_API_KEY
from src.indexer import Chunk, embed_texts

TOP_K_RETRIEVE = 30   # candidates from hybrid search
TOP_K_FINAL    = 8    # chunks sent to GPT-4o

client = OpenAI(api_key=OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))


# ── 0. Query Normalization ────────────────────────────────────────────────────

def _normalize_query(question: str) -> str:
    """
    FIX: Convert terse keyword queries into natural questions before
    expansion and reranking.

    Without this, short queries like "colleges in isu" or "cs prereqs"
    produce poor expansions AND get scored low by the reranker (which
    looks for passages that "directly answer" the question — hard to
    satisfy for a 3-word keyword string).

    Examples:
      "colleges in isu"      → "What are the colleges in ISU?"
      "cs prereqs"           → "What are the cs prereqs at Iowa State University?"
      "COMS 3110 prereq"     → left alone (has a course code — specific enough)
      "what courses are required for CS major?" → left alone (already a question)
    """
    q = question.strip()

    # Already a proper question — leave it alone
    if "?" in q or len(q.split()) > 5:
        return q

    # Contains a course code — specific enough as-is
    if re.search(r'\b[A-Z]{2,4}\s+\d{3,4}\b', q.upper()):
        return q

    # Short keyword query — wrap it
    return f"What are the {q} at Iowa State University?"


# ── 1. Query Expansion ────────────────────────────────────────────────────────

def expand_query(question: str, n: int = 3) -> List[str]:
    """
    Generate N rephrasings optimized for ISU catalog search.
    Receives a pre-normalized question from _normalize_query().
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You generate {n} alternative search queries for the Iowa State University "
                        "course catalog. Focus on:\n"
                        "- Course codes and numbers (e.g. COMS 3110, MATH 1650)\n"
                        "- Department names and college names\n"
                        "- Academic terms (prerequisites, credits, electives, four-year plan)\n"
                        f"Return ONLY a JSON array of {n} strings. No preamble."
                    ),
                },
                {"role": "user", "content": f"Original question: {question}"},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content or "[]"
        match = re.search(r"\[.*?\]", raw, re.S)
        if match:
            variants = json.loads(match.group())
            return [question] + [str(v) for v in variants[:n]]
    except Exception as e:
        logger.debug(f"Query expansion failed: {e}")
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


def _boost_exact_matches(
    question: str,
    candidates: List[Chunk],
    boost_factor: float = 0.5
) -> List[Chunk]:
    """
    Boost chunks that contain exact course codes mentioned in the question.

    FIX #3: Only boost chunks already scoring >= 5.0 (top half).
    Previously, a chunk scoring 2/10 with a code match could leapfrog
    a 9/10 chunk that also answers the question — wrong ordering.
    The boost should tip close competitors, not rescue irrelevant chunks.
    """
    codes = re.findall(r'\b[A-Z]{2,4}\s+\d{3,4}\b', question.upper())
    if not codes:
        return candidates

    for chunk in candidates:
        chunk_upper = chunk.text.upper()
        for code in codes:
            if code in chunk_upper:
                # FIX: Only boost competitive chunks
                if chunk.score >= 5.0:
                    chunk.score = chunk.score + boost_factor
                break

    return sorted(candidates, key=lambda c: c.score, reverse=True)


# ── 3. OpenAI Reranker ────────────────────────────────────────────────────────

def _rerank_openai(question: str, candidates: List[Chunk]) -> List[Chunk]:
    """
    Score candidates 1-10. Uses 600 chars per chunk so table rows and
    course requirements aren't cut off mid-content.
    """
    if not candidates:
        return candidates

    snippets = "\n\n".join(
        f"[{i}] {c.text[:600]}" for i, c in enumerate(candidates)
    )

    prompt = (
        f"Question: {question}\n\n"
        f"Rate each passage 1-10 for relevance to the question.\n"
        f"10 = directly answers it, 1 = completely irrelevant.\n"
        f"For course/degree questions: prefer passages with specific course codes,\n"
        f"credit counts, prerequisites, and semester-by-semester plans.\n"
        f"Passages tagged [TABLE] or [HEADER] are structured catalog data — "
        f"score them higher when the question asks about requirements or plans.\n"
        f"Respond with ONLY a JSON array of {len(candidates)} integers.\n\n"
        f"{snippets}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You output only a JSON array of integers. No other text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw = (resp.choices[0].message.content or "").strip()
        logger.debug(f"Reranker response: {raw[:80]}")

        match = re.search(r"\[[\d\s,\.]+\]", raw)
        if match:
            scores = json.loads(match.group())
            scores = [max(0.0, min(10.0, float(s))) for s in scores]
            if len(scores) == len(candidates):
                for chunk, score in zip(candidates, scores):
                    chunk.score = score
                reranked = sorted(candidates, key=lambda c: c.score, reverse=True)
                logger.debug(f"Scores: {[round(c.score,1) for c in reranked[:5]]}")
                return reranked
    except Exception as e:
        logger.debug(f"Reranker failed: {e}")

    # Fallback
    for i, chunk in enumerate(candidates):
        chunk.score = round(max(1.0, 5.0 - i * 0.15), 1)
    return candidates


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(
    question: str,
    index:    faiss.IndexFlatIP,
    bm25:     BM25Okapi,
    chunks:   List[Chunk],
    expand:   bool = True,
) -> List[Chunk]:
    # FIX: Normalize before expansion and reranking
    question = _normalize_query(question)
    logger.debug(f"Normalized question: '{question}'")

    queries = expand_query(question) if expand else [question]
    logger.debug(f"Queries: {queries}")

    vector_rankings: List[List[int]] = []
    bm25_rankings:   List[List[int]] = []

    for q in queries:
        vector_rankings.append(_vector_search(q, index, TOP_K_RETRIEVE))
        bm25_rankings.append(_bm25_search(q, bm25, TOP_K_RETRIEVE))

    fused_ids  = _rrf(vector_rankings + bm25_rankings)[:TOP_K_RETRIEVE]
    candidates = [chunks[i] for i in fused_ids]

    # Rerank first, then boost
    reranked = _rerank_openai(question, candidates)
    reranked = _boost_exact_matches(question, reranked)

    final = reranked[:TOP_K_FINAL]

    logger.info(
        f"Retrieved {len(final)} chunks | "
        f"top score={final[0].score:.1f}/10 | "
        f"query='{question[:60]}'"
    )
    return final
