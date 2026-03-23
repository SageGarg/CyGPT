"""
PDF Parser — column-aware URL + text extraction with table reconstruction.

Fixes applied:
  • _row_to_text(): Fixed broken join logic — separators no longer stripped before joining
  • Y-tolerance increased 4pt → 8pt to handle mixed font sizes in tables
    (credits like "3","4" often render slightly offset from course names)
  • Bold spans tagged inline as **text** so chunker can detect section headers
  • Works for: two-column layouts, full-width tables, mixed pages
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

# FIX #4: Increased from 4 to 8 — credits ("3","4") rendered by a smaller
# font sit 5-8pt below the course name on the same visual row. At 4pt
# tolerance they were split into separate rows, breaking "COMS 1010  3".
Y_TOLERANCE = 8


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
    doc = fitz.open(str(pdf_path))
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
    logger.info(f"Scanned {len(pdf_files)} PDF(s) -> {len(all_urls)} unique URLs")
    return sorted(all_urls)


# ── Row-aware text extraction ──────────────────────────────────────────────────

def _page_to_text(page: fitz.Page) -> str:
    """
    Extract text preserving table row structure.

    Key insight: a four-year plan table has 4 columns on one visual row:
      Fall Course | Credits | Spring Course | Credits
    Old approach split by page midpoint → lost row context.
    New approach: group ALL spans by Y-coordinate into rows, then join left→right.
    This keeps "COMS 1010  3  COMS 2270  4" on a single line.

    FIX #4: Y_TOLERANCE increased to 8pt (was 4pt) so credit numbers
    rendered in a smaller font are correctly merged with their course row.

    FIX #6: Bold spans tagged as **text** inline so the chunker can detect
    section headers and inject [HEADER] metadata tags.
    """
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    # Collect all text spans with position
    all_spans = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                x = span["origin"][0]
                y = span["origin"][1]
                bold = bool(span.get("flags", 0) & 16)
                # FIX #6: Tag bold spans so downstream chunker can detect headers
                if bold:
                    text = f"**{text}**"
                all_spans.append((y, x, text, bold))

    if not all_spans:
        return ""

    # Sort by Y (row), then X (column within row)
    all_spans.sort(key=lambda s: (s[0], s[1]))

    # Group into rows by Y proximity
    # FIX #4: Use Y_TOLERANCE=8 instead of hardcoded 4
    rows: List[List[Tuple]] = []
    current_row: List[Tuple] = []
    prev_y = None

    for span in all_spans:
        y = span[0]
        if prev_y is None or abs(y - prev_y) <= Y_TOLERANCE:
            current_row.append(span)
        else:
            if current_row:
                rows.append(current_row)
            current_row = [span]
        prev_y = y

    if current_row:
        rows.append(current_row)

    # Convert each row to a text line
    lines = []
    for row in rows:
        row.sort(key=lambda s: s[1])  # sort by X within row
        line = _row_to_text(row)
        if line:
            lines.append(line)

    return "\n".join(lines)


def _row_to_text(row: List[Tuple]) -> str:
    """
    Join spans in a row with context-aware separators.
    Small gap  = no separator (concatenate directly)
    Medium gap = double space (word boundary)
    Large gap  = pipe separator (table cell boundary)

    FIX #1: Previous version built parts with separators embedded as prefixes
    (e.g. "  " + text), then stripped them before joining with " ".join() —
    which destroyed all separators. Now we build the result string directly
    without a parts list, so separators are preserved correctly.
    """
    if not row:
        return ""

    result = row[0][2]
    prev_x = row[0][1]
    avg_char_w = 6  # approximate character width in points

    for span in row[1:]:
        y, x, text, bold = span
        # Estimate gap between end of previous text and start of this span.
        # Strip markdown bold markers when estimating text width.
        prev_text_clean = result.split()[-1].replace("**", "") if result.split() else ""
        prev_text_w = len(prev_text_clean) * avg_char_w
        gap = x - prev_x - prev_text_w

        if gap < 5:
            # Tiny gap — concatenate directly (handles split words)
            result += text
        elif gap < 30:
            # Word boundary gap
            result += "  " + text
        else:
            # Large gap = column separator in a table
            result += " | " + text

        prev_x = x

    return result.strip()


def extract_pdf_text(pdf_path: Path) -> str:
    doc   = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = _page_to_text(page).strip()
        if text:
            pages.append(f"[PDF: {pdf_path.name} | Page {i+1}]\n{text}")
    doc.close()
    full = "\n\n".join(pages)
    logger.info(f"{pdf_path.name}: extracted {len(full):,} chars from {len(pages)} pages")
    return full


def extract_all_pdf_texts(pdf_dir: Path) -> dict[str, str]:
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    results: dict[str, str] = {}
    for pdf in pdf_files:
        text = extract_pdf_text(pdf)
        if text.strip():
            results[f"pdf::{pdf.name}"] = text
    logger.info(f"Extracted text from {len(results)} PDF(s)")
    return results
