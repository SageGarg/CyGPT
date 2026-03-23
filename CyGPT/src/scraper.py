"""
Async Web Scraper with persistent disk cache.

Uses:
  • httpx      – async HTTP/2 client
  • trafilatura – best-in-class main-content extractor
  • diskcache  – SQLite-backed 7-day cache
"""
from __future__ import annotations

import asyncio
import re
from typing import Dict, Optional

import diskcache
import httpx
import trafilatura
from loguru import logger
from tqdm.asyncio import tqdm as atqdm

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import CACHE_DIR, MAX_CONCURRENT, REQUEST_TIMEOUT

_cache = diskcache.Cache(str(CACHE_DIR), size_limit=2**30)

USER_AGENT = (
    "CyGPT-RAG/2.0 (Iowa State University Educational Bot; "
    "contact: github.com/SageGarg/CyGPT)"
)

# ── Skip URLs that are pure search/nav pages with no real content ─────────────
_SKIP_RE = re.compile(
    r"(/search/\?)"           # catalog.iastate.edu/search/?P=STAT%20542
    r"|(\?P=[A-Z]+%20\d+)"   # any ?P=COURSE%20number pattern
    r"|(/search/\?commit=)"
)


def _should_skip(url: str) -> bool:
    return bool(_SKIP_RE.search(url))


async def _fetch_one(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> Optional[str]:

    if _should_skip(url):
        logger.debug(f"Skipping nav/search URL: {url}")
        return None

    # Cache hit
    cached = _cache.get(url)
    if cached is not None:
        return cached  # type: ignore[return-value]

    async with semaphore:
        try:
            r = await client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            r.raise_for_status()

            ctype = r.headers.get("content-type", "")
            if "pdf" in ctype or url.lower().endswith(".pdf"):
                return None

            text = trafilatura.extract(
                r.text,
                include_tables=True,
                include_links=False,
                include_comments=False,
                no_fallback=False,
                favor_precision=False,
                favor_recall=True,
            )

            if text and len(text.strip()) > 300:
                _cache.set(url, text.strip(), expire=86_400 * 7)
                return text.strip()

        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP {e.response.status_code} → {url}")
        except Exception as e:
            logger.debug(f"Skip {url}: {type(e).__name__}: {e}")

    return None


async def scrape_all(urls: list[str]) -> Dict[str, str]:
    """Async-scrape all urls. Returns {url: clean_text}."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        headers=headers,
        http2=True,
        limits=httpx.Limits(
            max_connections=MAX_CONCURRENT + 5,
            max_keepalive_connections=MAX_CONCURRENT,
        ),
    ) as client:
        tasks = [_fetch_one(client, url, semaphore) for url in urls]
        texts = await atqdm.gather(*tasks, desc="🌐 Scraping pages")

    results: Dict[str, str] = {
        url: text
        for url, text in zip(urls, texts)
        if text is not None
    }

    logger.info(f"Scraped {len(results)}/{len(urls)} pages")
    return results
