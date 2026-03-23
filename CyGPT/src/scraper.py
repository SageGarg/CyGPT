"""
Async Web Scraper with persistent disk cache.

Uses:
  • httpx  – async HTTP/2 client (much faster than requests)
  • trafilatura – state-of-the-art main-content extractor
    (beats custom BeautifulSoup parsers on recall and precision)
  • diskcache – SQLite-backed cache so re-runs are instant
  • asyncio Semaphore – polite concurrency cap
"""
from __future__ import annotations

import asyncio
from typing import Dict, Optional

import diskcache
import httpx
import trafilatura
from loguru import logger
from tqdm.asyncio import tqdm as atqdm

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import CACHE_DIR, MAX_CONCURRENT, REQUEST_TIMEOUT

# ── Persistent cache (1 GB, 7-day TTL) ───────────────────────────────────────
_cache = diskcache.Cache(str(CACHE_DIR), size_limit=2**30)

USER_AGENT = (
    "CyGPT-RAG/2.0 (Iowa State University Educational Bot; "
    "contact: github.com/SageGarg/CyGPT)"
)

# ── Core fetch ────────────────────────────────────────────────────────────────

async def _fetch_one(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> Optional[str]:
    """Fetch and extract text from a single URL. Returns None on failure."""

    # Cache hit – skip network entirely
    cached = _cache.get(url)
    if cached is not None:
        return cached  # type: ignore[return-value]

    async with semaphore:
        try:
            r = await client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            r.raise_for_status()

            ctype = r.headers.get("content-type", "")
            if "pdf" in ctype or url.lower().endswith(".pdf"):
                return None  # skip binary PDFs

            # trafilatura: removes boilerplate (nav, footer, ads) automatically
            text = trafilatura.extract(
                r.text,
                include_tables=True,
                include_links=False,
                include_comments=False,
                no_fallback=False,      # use readability fallback if needed
                favor_precision=False,
                favor_recall=True,
            )

            if text and len(text.strip()) > 300:
                _cache.set(url, text.strip(), expire=86_400 * 7)  # 7 days
                return text.strip()

        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP {e.response.status_code} → {url}")
        except Exception as e:
            logger.debug(f"Skip {url}: {type(e).__name__}: {e}")

    return None


# ── Batch entrypoint ──────────────────────────────────────────────────────────

async def scrape_all(urls: list[str]) -> Dict[str, str]:
    """
    Async-scrape all *urls* with capped concurrency.
    Returns {url: clean_text} for every successful fetch.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        headers=headers,
        http2=True,
        limits=httpx.Limits(max_connections=MAX_CONCURRENT + 5, max_keepalive_connections=MAX_CONCURRENT),
    ) as client:
        tasks = [_fetch_one(client, url, semaphore) for url in urls]
        texts = await atqdm.gather(*tasks, desc="🌐 Scraping pages")

    results: Dict[str, str] = {
        url: text
        for url, text in zip(urls, texts)
        if text is not None
    }

    cached_hits = sum(1 for url in urls if _cache.get(url) is not None) - len(results)
    logger.info(
        f"Scraped {len(results)}/{len(urls)} pages "
        f"(~{max(cached_hits,0)} served from cache)"
    )
    return results
