#!/usr/bin/env python3
"""
CyGPT Ingestion Pipeline
========================
Sources indexed:
  1. Text extracted directly from every PDF  ← NEW: catches tables, plans, etc.
  2. Web pages scraped from URLs found in PDFs

Run this once, or whenever your PDFs change.

Usage:
  python ingest.py                  # default MAX_URLS from config.py
  python ingest.py --max-urls 500
  python ingest.py --pdf-only       # skip web scraping (fast rebuild from PDFs)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path


from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent))

from config import ALLOWED_DOMAINS, MAX_URLS, PDF_DIR
from src.pdf_parser import extract_urls_from_folder, extract_all_pdf_texts
from src.scraper import scrape_all
from src.indexer import build_chunks, build_and_save

console = Console()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CyGPT ingestion pipeline")
    p.add_argument("--max-urls", type=int, default=MAX_URLS)
    p.add_argument("--pdf-only", action="store_true", help="Skip web scraping")
    return p.parse_args()


async def run(max_urls: int, pdf_only: bool) -> None:
    t0 = time.perf_counter()

    console.print(Panel(
        "[bold cyan]CyGPT — Ingestion Pipeline[/bold cyan]\n"
        "[dim]PDFs + Web Pages → Embed → Index[/dim]",
        expand=False,
    ))

    # ── Source 1: PDF text content ────────────────────────────────────────────
    console.rule("[bold]Step 1 / 3  Extract PDF Text[/bold]")
    pdf_texts = extract_all_pdf_texts(PDF_DIR)
    console.print(f"  PDFs with text : [green]{len(pdf_texts)}[/green]")
    for key, text in pdf_texts.items():
        console.print(f"  [dim]{key}[/dim] → {len(text):,} chars")

    # ── Source 2: Web pages linked from PDFs ──────────────────────────────────
    scraped: dict[str, str] = {}
    if not pdf_only:
        console.rule("[bold]Step 2 / 3  Scrape Linked Web Pages[/bold]")
        pdfs = list(PDF_DIR.glob("*.pdf"))
        urls = extract_urls_from_folder(PDF_DIR, ALLOWED_DOMAINS)[:max_urls]
        console.print(f"  URLs queued : [green]{len(urls)}[/green]  (cap={max_urls})")
        if urls:
            scraped = await scrape_all(urls)
            console.print(f"  Pages scraped : [green]{len(scraped)}[/green] / {len(urls)}")
    else:
        console.print("[yellow]--pdf-only: skipping web scraping[/yellow]")

    # ── Merge both sources ────────────────────────────────────────────────────
    all_sources = {**pdf_texts, **scraped}
    if not all_sources:
        console.print("[red]No content found. Check data/pdfs/ and ALLOWED_DOMAINS.[/red]")
        return

    console.print(
        f"\n  [bold]Total sources:[/bold] "
        f"[green]{len(pdf_texts)} PDF doc(s)[/green] + "
        f"[green]{len(scraped)} web page(s)[/green] = "
        f"[cyan]{len(all_sources)} total[/cyan]"
    )

    # ── Embed & index ─────────────────────────────────────────────────────────
    console.rule("[bold]Step 3 / 3  Embed & Build Index[/bold]")
    chunks = build_chunks(all_sources)
    build_and_save(chunks)

    elapsed = time.perf_counter() - t0

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("PDF sources",     f"[green]{len(pdf_texts)}[/green]")
    table.add_row("Web pages",       f"[green]{len(scraped)}[/green]")
    table.add_row("Chunks indexed",  f"[green]{len(chunks)}[/green]")
    table.add_row("Time elapsed",    f"[cyan]{elapsed:.1f}s[/cyan]")

    console.print(Panel(table, title="[bold green]✓  Done![/bold green]", expand=False))
    console.print("\nStart the app:  [bold]streamlit run app.py[/bold]\n")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(max_urls=args.max_urls, pdf_only=args.pdf_only))
