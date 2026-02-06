import os
import re
import json
import time
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
import numpy as np
import faiss
from tqdm import tqdm

from openai import OpenAI

# ----------------------------
# Config
# ----------------------------
PDF_PATH = "data/collegescurricula.pdf"  # put in same folder, or use full path
ALLOWED_DOMAINS = {
    "catalog.iastate.edu",
    "pre-health.las.iastate.edu",
    "iastate.edu",
}  # edit as needed

MAX_URLS = 60              # keep it small for a first test run
REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_REQUESTS = 0.3
CHUNK_SIZE = 900           # characters
CHUNK_OVERLAP = 120
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"  # swap if you use another
TOP_K = 6

USER_AGENT = "CyGPT-RAG/0.1 (contact: you@example.com)"
load_dotenv()
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# Utilities
# ----------------------------
URL_RE = re.compile(r"https?://[^\s)>\]]+")

def is_allowed(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
        host = host.split(":")[0]
        # allow subdomains of allowed domains
        for d in ALLOWED_DOMAINS:
            if host == d or host.endswith("." + d):
                return True
        return False
    except Exception:
        return False

def normalize_url(url: str) -> str:
    # remove trailing punctuation that often sticks in PDFs
    return url.rstrip(").,;]")

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks

# ----------------------------
# Step A: Extract links from PDF
# ----------------------------
def extract_links_from_pdf(pdf_path: str) -> List[str]:
    doc = fitz.open(pdf_path)

    urls = set()

    # 1) URLs visible in text
    for page in doc:
        text = page.get_text("text") or ""
        for u in URL_RE.findall(text):
            urls.add(normalize_url(u))

    # 2) URLs in link annotations
    for page in doc:
        for link in page.get_links():
            u = link.get("uri")
            if u and u.startswith("http"):
                urls.add(normalize_url(u))

    # filter
    urls = [u for u in urls if is_allowed(u)]
    urls.sort()
    return urls

# ----------------------------
# Step B: Fetch & clean webpage text
# ----------------------------
def fetch_html(url: str) -> Optional[str]:
    try:
        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type") or "").lower()
        # Part 1: ONLY HTML pages. Skip PDFs for now (we’ll do that next step).
        if "application/pdf" in ctype or url.lower().endswith(".pdf"):
            return None
        return r.text
    except Exception:
        return None

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # remove noise
    for tag in soup(["script", "style", "noscript", "svg", "img", "header", "footer", "nav"]):
        tag.decompose()

    # try to focus on main content
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n")

    # cleanup
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # drop super-short junk
        if len(line) < 3:
            continue
        lines.append(line)

    return "\n".join(lines)

# ----------------------------
# Step C: Embed + FAISS index
# ----------------------------
@dataclass
class DocChunk:
    url: str
    chunk_id: str
    text: str

def embed_texts(texts: List[str]) -> np.ndarray:
    # OpenAI embeddings API
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    vectors = np.array([d.embedding for d in resp.data], dtype="float32")
    return vectors

def build_index(chunks: List[DocChunk]) -> Tuple[faiss.IndexFlatIP, np.ndarray]:
    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)

    # cosine similarity via inner product on normalized vectors
    faiss.normalize_L2(vectors)

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index, vectors

def retrieve(query: str, index: faiss.IndexFlatIP, chunks: List[DocChunk], k: int) -> List[DocChunk]:
    qvec = embed_texts([query])
    faiss.normalize_L2(qvec)

    scores, ids = index.search(qvec, k)
    out = []
    for idx in ids[0]:
        if idx == -1:
            continue
        out.append(chunks[idx])
    return out

# ----------------------------
# Step D: Answer with citations
# ----------------------------
def answer(question: str, retrieved: List[DocChunk]) -> str:
    context_blocks = []
    for i, ch in enumerate(retrieved, start=1):
        context_blocks.append(
            f"[Source {i}] URL: {ch.url}\n{ch.text}\n"
        )

    system = (
        "You are a helpful assistant for an Iowa State University information bot. "
        "Answer using only the provided sources. "
        "If the answer is not in the sources, say you don't have enough information. "
        "Cite sources like (Source 1), (Source 2)."
    )

    sources_text = "\n\n".join(context_blocks)

    user = f"""Question: {question}

    Sources:

    {sources_text}
    """


    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content

# ----------------------------
# Main
# ----------------------------
def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in your environment first.")

    print(f"Reading PDF: {PDF_PATH}")
    urls = extract_links_from_pdf(PDF_PATH)
    print(f"Found {len(urls)} allowed URLs from the PDF.")
    urls = urls[:MAX_URLS]
    print(f"Using first {len(urls)} URLs for this test run.\n")

    chunks: List[DocChunk] = []
    seen_pages = set()

    for url in tqdm(urls, desc="Fetching pages"):
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
        raise RuntimeError("No webpage content was ingested. Try increasing MAX_URLS or checking ALLOWED_DOMAINS.")

    print(f"\nCreated {len(chunks)} chunks from webpages. Building vector index...")
    index, _ = build_index(chunks)
    print("Index ready.\n")

    print("Type a question and press Enter. Type 'exit' to quit.\n")
    while True:
        q = input("Q> ").strip()
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            break

        hits = retrieve(q, index, chunks, TOP_K)
        resp = answer(q, hits)

        print("\n--- Answer ---")
        print(resp)
        print("--------------\n")

if __name__ == "__main__":
    main()
