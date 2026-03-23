"""
Answerer — streams a GPT-4o response grounded in retrieved chunks.

Features:
  • Streaming tokens (no waiting for full response)
  • Source citations inline ((Source 1), (Source 2) …)
  • Multi-turn conversation history (last 3 exchanges)
  • GPT-generated follow-up question suggestions
"""
from __future__ import annotations

import sys
import pathlib
from typing import Generator, List

from openai import OpenAI

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import CHAT_MODEL, OPENAI_API_KEY
from src.indexer import Chunk

client = OpenAI(api_key=OPENAI_API_KEY)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are CyGPT, the official AI assistant for Iowa State University (ISU).
You help students, faculty, and staff find information about courses, majors, minors,
certificates, pre-professional programs, and academic requirements.

RULES:
1. Answer using ONLY the provided [Source N] blocks. Do not use prior knowledge.
2. Cite every factual claim with (Source N) immediately after the claim.
3. If the answer is not in the sources, say: "I don't have that information in my sources.
   Try checking catalog.iastate.edu directly or contacting your advisor."
4. Be concise, friendly, and helpful — bullet points are fine for lists.
5. After your answer, add a section titled "💡 You might also ask:" with exactly
   3 relevant follow-up questions the user could ask next.

Format:
[Main answer with (Source N) citations]

💡 You might also ask:
• …
• …
• …
"""


def _build_context(chunks: List[Chunk]) -> str:
    blocks = []
    seen_urls: set[str] = set()
    for i, c in enumerate(chunks, 1):
        url_label = c.url if c.url not in seen_urls else f"{c.url} (continued)"
        seen_urls.add(c.url)
        blocks.append(f"[Source {i}] {url_label}\n{c.text}")
    return "\n\n---\n\n".join(blocks)


# ── Streaming answer ──────────────────────────────────────────────────────────

def stream_answer(
    question: str,
    chunks:   List[Chunk],
    history:  List[dict],
) -> Generator[str, None, None]:
    """
    Yields response tokens as they arrive from the OpenAI streaming API.
    history is a list of {"role": "user"|"assistant", "content": "…"} dicts.
    """
    context  = _build_context(chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Include last 3 conversation turns (6 messages) for multi-turn context
    messages += history[-6:]

    messages.append({
        "role":    "user",
        "content": f"Sources:\n\n{context}\n\nQuestion: {question}",
    })

    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
        stream=True,
    )

    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta


# ── Non-streaming (for CLI / testing) ────────────────────────────────────────

def answer(question: str, chunks: List[Chunk], history: List[dict] = []) -> str:
    return "".join(stream_answer(question, chunks, history))
