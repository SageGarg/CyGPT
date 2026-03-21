"""
FastAPI wrapper that exposes the RAG pipeline in `main.py` as a web API
for the CyGPT UI. Start with `uvicorn server:app --reload --port 8000`.
"""

import os
import time
import threading
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from main import (
    extract_links_from_pdf,
    fetch_html,
    html_to_text,
    chunk_text,
    sha1,
    DocChunk,
    build_index,
    retrieve,
    answer,
    ALLOWED_DOMAINS,
    MAX_URLS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SLEEP_BETWEEN_REQUESTS,
)

app = FastAPI(title="CyGPT RAG API", version="0.1")

# Allow local UI (any origin ok for demo; tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, str]]


_index = None
_chunks: List[DocChunk] = []
_lock = threading.Lock()


def _demo_response(query: str) -> ChatResponse:
    """Offline/demo fallback when API key is missing or DEMO_MODE is set."""
    canned = (
        "Demo mode: connect OPENAI_API_KEY for live RAG. "
        "Example answer — The priority FAFSA deadline at Iowa State is March 1. "
        "Submit by then to maximize need-based aid eligibility."
    )
    sources = [
        {"label": "catalog.iastate.edu", "url": "https://catalog.iastate.edu"},
        {"label": "financialaid.iastate.edu", "url": "https://www.financialaid.iastate.edu"},
    ]
    return ChatResponse(answer=canned, sources=sources)


def _ingest() -> None:
    """Build the FAISS index from the PDF -> URL crawl."""
    global _index, _chunks

    pdf_path = os.getenv("PDF_PATH", "data/collegescurricula.pdf")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"PDF_PATH '{pdf_path}' not found. Set PDF_PATH env var to a PDF that lists allowed ISU URLs."
        )

    urls = extract_links_from_pdf(pdf_path)
    urls = urls[:MAX_URLS]

    seen_pages = set()
    chunks: List[DocChunk] = []

    for url in urls:
        if url in seen_pages:
            continue
        seen_pages.add(url)

        html = fetch_html(url)
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        if not html:
            continue

        text = html_to_text(html)
        if len(text) < 400:
            continue

        for t in chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP):
            cid = sha1(url + "::" + t[:120])
            chunks.append(DocChunk(url=url, chunk_id=cid, text=t))

    if not chunks:
        raise RuntimeError(
            "No webpage content was ingested. Try increasing MAX_URLS or checking ALLOWED_DOMAINS/PDF content."
        )

    index, _ = build_index(chunks)
    _index = index
    _chunks = chunks


def _ensure_index_ready() -> None:
    """Thread-safe, on-demand index builder."""
    if _index is not None:
        return
    with _lock:
        if _index is None:
            _ingest()


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "index_built": _index is not None,
        "chunks": len(_chunks),
        "allowed_domains": list(ALLOWED_DOMAINS),
        "max_urls": MAX_URLS,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")

    # Demo/offline path
    if os.getenv("DEMO_MODE", "0") == "1" or not os.getenv("OPENAI_API_KEY"):
        return _demo_response(body.query)

    try:
        _ensure_index_ready()
    except Exception as exc:  # surface ingestion errors
        raise HTTPException(status_code=500, detail=str(exc))

    hits = retrieve(body.query, _index, _chunks, k=6)
    if not hits:
        raise HTTPException(status_code=404, detail="No content available for answering.")

    response_text = answer(body.query, hits)
    sources = []
    for h in hits:
        sources.append({"label": h.url, "url": h.url})

    return ChatResponse(answer=response_text, sources=sources)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
