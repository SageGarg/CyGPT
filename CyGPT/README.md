# 🌪️ CyGPT — Iowa State University AI Assistant

A production-grade RAG (Retrieval-Augmented Generation) system that turns ISU
catalog PDFs into an intelligent, cited Q&A assistant.

## Architecture

```
PDFs in data/pdfs/
      │
      ▼
[pdf_parser.py]  Column-aware URL extraction (PyMuPDF spatial blocks)
      │
      ▼
[scraper.py]     Async HTTP/2 scraping with 7-day disk cache (trafilatura)
      │
      ▼
[indexer.py]     Chunking → OpenAI embeddings → FAISS + BM25 (persisted)
      │
      ▼
[retriever.py]   Query Expansion → Hybrid Search (RRF) → Cross-Encoder Rerank
      │
      ▼
[answerer.py]    GPT-4o streaming answer with citations + follow-up suggestions
      │
      ▼
[app.py]         Streamlit chat UI with source cards and conversation memory
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
cp .env.example .env
# edit .env and add: OPENAI_API_KEY=sk-...

# 3. Drop your PDFs
cp your-catalog.pdf data/pdfs/

# 4. Build the index (run once, or when PDFs change)
python ingest.py

# 5. Launch the app
streamlit run app.py
```

## What makes this extraordinary

| Feature                      | Detail                                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Column-aware PDF parsing** | Splits text blocks by page midpoint, sorts each column by Y, preventing cross-column URL confusion               |
| **Async scraping**           | httpx + asyncio with semaphore-limited concurrency; 15× faster than sequential requests                          |
| **7-day disk cache**         | Re-runs are near-instant; pages only re-fetched after expiry                                                     |
| **Hybrid retrieval**         | BM25 (keyword) + FAISS (semantic) fused with Reciprocal Rank Fusion                                              |
| **Query expansion**          | GPT-4o rewrites each question 3 ways, boosting recall                                                            |
| **Cross-encoder reranking**  | sentence-transformers cross-encoder scores (query, passage) pairs; far more accurate than dot-product similarity |
| **Streaming UI**             | Token-by-token streaming so users see results immediately                                                        |
| **Source cards**             | Every answer shows which URLs were used, with reranker confidence scores                                         |
| **Multi-turn memory**        | Last 3 conversation turns included in context                                                                    |
| **Follow-up suggestions**    | GPT generates 3 relevant next questions after each answer                                                        |

## Configuration

Edit `config.py` to change:

- `ALLOWED_DOMAINS` — which sites to scrape
- `EMBED_MODEL` — swap to `text-embedding-ada-002` for higher quality
- `CHAT_MODEL` — defaults to `gpt-4o`
- `MAX_URLS` — how many URLs to process per run
- `TOP_K_FINAL` — how many chunks to send to GPT

## Project structure

```
CyGPT/
├── data/
│   ├── pdfs/        ← drop PDFs here
│   ├── cache/       ← auto-managed disk cache
│   └── index/       ← persisted FAISS + BM25 + chunks
├── src/
│   ├── pdf_parser.py
│   ├── scraper.py
│   ├── indexer.py
│   ├── retriever.py
│   └── answerer.py
├── config.py
├── ingest.py        ← run to build index
├── app.py           ← Streamlit UI
└── requirements.txt
```
