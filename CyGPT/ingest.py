#!/usr/bin/env python3
"""
CyGPT Ingestion Pipeline
========================
Run this once (or whenever your PDFs change) to:
  1. Extract URLs from every PDF in data/pdfs/
  2. Async-scrape all pages (with 7-day disk cache)
  3. Chunk, embed, and persist a hybrid FAISS + BM25 index

Usage:
  python ingest.py                  # uses MAX_URLS from config.py
  python ingest.py --max-urls 500   # override URL cap
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Make sure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from config import ALLOWED_DOMAINS, MAX_URLS, PDF_DIR
from src.pdf_parser import extract_urls_from_folder
from src.scraper import scrape_all
from src.indexer import build_chunks, build_and_save

console = Console()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CyGPT ingestion pipeline")
    p.add_argument("--max-urls", type=int, default=MAX_URLS, help="URL cap per run")
    p.add_argument("--no-cache", action="store_true", help="Ignore existing disk cache")
    return p.parse_args()


async def run(max_urls: int) -> None:
    t0 = time.perf_counter()

    console.print(Panel(
        "[bold cyan]CyGPT — Ingestion Pipeline[/bold cyan]\n"
        "[dim]PDFs → URLs → Scrape → Embed → Index[/dim]",
        expand=False,
    ))

    # ── Step 1: PDF → URLs ────────────────────────────────────────────────────
    console.rule("[bold]Step 1 / 3  PDF Parsing[/bold]")
    pdfs  = list(PDF_DIR.glob("*.pdf"))
    urls  = extract_urls_from_folder(PDF_DIR, ALLOWED_DOMAINS)
    urls  = urls[:max_urls]
    console.print(f"  PDFs found  : [green]{len(pdfs)}[/green]")
    console.print(f"  URLs queued : [green]{len(urls)}[/green]  (cap={max_urls})")

    if not urls:
        console.print(
            "[yellow]⚠ No URLs found. Make sure PDFs are in data/pdfs/ "
            "and ALLOWED_DOMAINS is correct.[/yellow]"
        )
        return

    # ── Step 2: Async scrape ──────────────────────────────────────────────────
    console.rule("[bold]Step 2 / 3  Web Scraping[/bold]")
    scraped = await scrape_all(urls)
    console.print(f"  Pages scraped : [green]{len(scraped)}[/green] / {len(urls)}")

    if not scraped:
        console.print("[red]No pages scraped. Check network / ALLOWED_DOMAINS.[/red]")
        return

    # ── Step 3: Embed & index ─────────────────────────────────────────────────
    console.rule("[bold]Step 3 / 3  Embedding & Indexing[/bold]")
    chunks = build_chunks(scraped)
    build_and_save(chunks)

    elapsed = time.perf_counter() - t0

    # ── Summary ───────────────────────────────────────────────────────────────
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("PDFs scanned",    f"[green]{len(pdfs)}[/green]")
    table.add_row("URLs scraped",    f"[green]{len(scraped)}[/green]")
    table.add_row("Chunks indexed",  f"[green]{len(chunks)}[/green]")
    table.add_row("Time elapsed",    f"[cyan]{elapsed:.1f}s[/cyan]")

    console.print(Panel(table, title="[bold green]✓  Done![/bold green]", expand=False))
    console.print("\nStart the app with:  [bold]streamlit run app.py[/bold]\n")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(max_urls=args.max_urls))
