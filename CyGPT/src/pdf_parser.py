"""
PDF Parser — column-aware URL extraction from one or many PDF files.

Key insight for two-column PDFs: PyMuPDF's default get_text("text") reads
blocks top-to-bottom, mixing left and right columns. We fix this by splitting
blocks spatially at the page midpoint and sorting each column independently.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import fitz  # PyMuPDF
from loguru import logger

# ── Regex & helpers ───────────────────────────────────────────────────────────
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def _normalize(url: str) -> str:
    """Strip trailing punctuation that sticks to URLs in PDFs."""
    return url.rstrip(".,;)]\">")


def _is_allowed(url: str, allowed: set[str]) -> bool:
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return any(host == d or host.endswith("." + d) for d in allowed)
    except Exception:
        return False


# ── Single PDF ────────────────────────────────────────────────────────────────

def extract_urls(pdf_path: Path, allowed_domains: set[str]) -> List[str]:
    """
    Extract all allowed URLs from *pdf_path* using column-aware text parsing.

    Strategy:
      1. For each page, split text blocks into left / right columns by the
         page midpoint, sort each column by Y coordinate, then concatenate.
         This prevents inter-column URL confusion.
      2. Also grab annotation (clickable) links, which are more reliable.
    """
    doc   = fitz.open(str(pdf_path))
    urls: set[str] = set()

    for page in doc:
        mid_x = page.rect.width / 2

        # ── 1. Spatial text blocks ─────────────────────────────────────────
        blocks = page.get_text("blocks")  # [(x0,y0,x1,y1,text,…), …]
        left   = sorted((b for b in blocks if b[0] <  mid_x), key=lambda b: b[1])
        right  = sorted((b for b in blocks if b[0] >= mid_x), key=lambda b: b[1])

        for block in left + right:
            raw_text = block[4]
            for raw_url in URL_RE.findall(raw_text):
                urls.add(_normalize(raw_url))

        # ── 2. Clickable link annotations (more reliable) ──────────────────
        for link in page.get_links():
            u = link.get("uri", "")
            if u.startswith("http"):
                urls.add(_normalize(u))

    doc.close()

    result = sorted(u for u in urls if _is_allowed(u, allowed_domains))
    logger.info(f"{pdf_path.name}: {len(result)} allowed URLs found")
    return result


# ── Folder of PDFs ────────────────────────────────────────────────────────────

def extract_urls_from_folder(pdf_dir: Path, allowed_domains: set[str]) -> List[str]:
    """
    Scan every *.pdf in *pdf_dir*, deduplicate URLs across files,
    and return a sorted list of allowed URLs.
    """
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {pdf_dir}. Drop your PDFs into data/pdfs/")
        return []

    all_urls: set[str] = set()
    for pdf in pdf_files:
        all_urls.update(extract_urls(pdf, allowed_domains))

    logger.info(
        f"Scanned {len(pdf_files)} PDF(s) → {len(all_urls)} unique URLs total"
    )
    return sorted(all_urls)


# ── CLI helper ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    from config import ALLOWED_DOMAINS, PDF_DIR

    urls = extract_urls_from_folder(PDF_DIR, ALLOWED_DOMAINS)
    print(json.dumps(urls, indent=2))
    print(f"\nTotal: {len(urls)}")
