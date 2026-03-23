"""
PDF Parser — two jobs:
  1. extract_urls()        → column-aware URL extraction (unchanged)
  2. extract_pdf_text()    → extract ALL readable text from PDFs,
                             preserving table structure as best as possible,
                             so content like four-year plans gets indexed too.
"""
from __future__ import annotations

import re
import sys
import pathlib
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

import fitz  # PyMuPDF
from loguru import logger

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def _normalize(url: str) -> str:
    return url.rstrip(".,;)]\">")


def _is_allowed(url: str, allowed: set[str]) -> bool:
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return any(host == d or host.endswith("." + d) for d in allowed)
    except Exception:
        return False


# ── URL extraction (column-aware) ─────────────────────────────────────────────

def extract_urls(pdf_path: Path, allowed_domains: set[str]) -> List[str]:
    doc  = fitz.open(str(pdf_path))
    urls: set[str] = set()

    for page in doc:
        mid_x  = page.rect.width / 2
        blocks = page.get_text("blocks")
        left   = sorted((b for b in blocks if b[0] <  mid_x), key=lambda b: b[1])
        right  = sorted((b for b in blocks if b[0] >= mid_x), key=lambda b: b[1])

        for block in left + right:
            for raw_url in URL_RE.findall(block[4]):
                urls.add(_normalize(raw_url))

        for link in page.get_links():
            u = link.get("uri", "")
            if u.startswith("http"):
                urls.add(_normalize(u))

    doc.close()
    result = sorted(u for u in urls if _is_allowed(u, allowed_domains))
    logger.info(f"{pdf_path.name}: {len(result)} allowed URLs found")
    return result


def extract_urls_from_folder(pdf_dir: Path, allowed_domains: set[str]) -> List[str]:
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {pdf_dir}")
        return []
    all_urls: set[str] = set()
    for pdf in pdf_files:
        all_urls.update(extract_urls(pdf, allowed_domains))
    logger.info(f"Scanned {len(pdf_files)} PDF(s) → {len(all_urls)} unique URLs")
    return sorted(all_urls)


# ── Full text extraction (column-aware, table-preserving) ─────────────────────

def _page_to_text(page: fitz.Page) -> str:
    """
    Extract text from a single page in reading order.

    Strategy:
      • Use 'dict' mode to get individual text spans with coordinates.
      • Split spans into left / right columns by page midpoint.
      • Sort each column top-to-bottom, then concatenate left → right.
      • This correctly handles two-column layouts AND wide single-column tables.
    """
    mid_x  = page.rect.width / 2
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    left_lines:  List[Tuple[float, str]] = []   # (y, text)
    right_lines: List[Tuple[float, str]] = []

    for block in blocks:
        if block.get("type") != 0:   # 0 = text block
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = " ".join(s["text"] for s in spans).strip()
            if not text:
                continue
            x0 = spans[0]["origin"][0]
            y0 = spans[0]["origin"][1]
            if x0 < mid_x:
                left_lines.append((y0, text))
            else:
                right_lines.append((y0, text))

    left_lines.sort(key=lambda t: t[0])
    right_lines.sort(key=lambda t: t[0])

    all_lines = [t for _, t in left_lines] + [t for _, t in right_lines]
    return "\n".join(all_lines)


def extract_pdf_text(pdf_path: Path) -> str:
    """
    Return all readable text from *pdf_path* as a single string,
    with page separators so chunk boundaries are clear.
    """
    doc   = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = _page_to_text(page).strip()
        if text:
            pages.append(f"[PDF: {pdf_path.name} | Page {i+1}]\n{text}")
    doc.close()

    full = "\n\n".join(pages)
    logger.info(
        f"{pdf_path.name}: extracted {len(full):,} chars of text "
        f"from {len(pages)} pages"
    )
    return full


def extract_all_pdf_texts(pdf_dir: Path) -> dict[str, str]:
    """
    Extract text from every PDF in *pdf_dir*.
    Returns {pdf_filename: full_text}.
    """
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    results: dict[str, str] = {}
    for pdf in pdf_files:
        text = extract_pdf_text(pdf)
        if text.strip():
            results[f"pdf::{pdf.name}"] = text
    logger.info(f"Extracted text from {len(results)} PDF(s)")
    return results
