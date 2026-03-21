# CyGPT
AI-powered RAG chatbot for Iowa State that extracts links from an allowlisted curriculum PDF, scrapes approved university websites, and answers with cited sources. Now ships with a web UI and FastAPI backend.

## Quick start
1) **Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2) **Config**
   - Set `OPENAI_API_KEY` in your env.
   - Set `PDF_PATH` to a PDF that contains ISU URLs to crawl (default: `data/collegescurricula.pdf`).
   - Optional: `DEMO_MODE=1` lets `/api/chat` respond with a canned answer when no API key or crawl is available (useful for UI smoke tests).
3) **Run the API**
   ```bash
   uvicorn server:app --reload --port 8000
   ```
   - Health check: `GET http://localhost:8000/api/health`
   - Chat: `POST http://localhost:8000/api/chat` with `{"query": "your question"}`.
4) **Serve the UI**
   ```bash
   cd ui && python3 -m http.server 8001
   # or: npx serve -l 8001 .
   ```
   Open `http://localhost:8001`. The UI calls `/api/chat` relative to the current host, so if you use a different API port set a reverse proxy or change the fetch URL in `ui/app.js`.

## Notes
- Allowed domains are defined in `main.py` (`ALLOWED_DOMAINS`). Update as needed.
- Index is built lazily on first `/api/chat` request. Increase `MAX_URLS` for broader coverage.
- If ingestion returns zero chunks, check that the PDF actually lists HTTP/HTTPS links to allowed domains.
