"""
Answerer — streams a GPT-4o response grounded in retrieved chunks.

Fixes applied:
  • History slice now ensures we never start mid-turn (always begins with
    a user message). A stale assistant message at the start of the slice
    caused GPT-4o to occasionally treat it as context it had already said,
    producing truncated or confused responses.
"""
from __future__ import annotations

import sys
import pathlib
from typing import Generator, List

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import CHAT_MODEL, OPENAI_API_KEY
from src.indexer import Chunk

client = OpenAI(api_key=OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are CyGPT, Iowa State University's AI academic advisor.
You help students with courses, majors, degree requirements, prerequisites, and academic planning.

ANSWERING RULES:
1. PREFER the provided [Source N] blocks — cite them with (Source N) after each fact.
2. If the sources contain the answer (even partially), use them as your primary basis.
3. If sources are INSUFFICIENT but you know the answer from ISU catalog knowledge,
   you MAY supplement with that knowledge — but say "(general ISU knowledge, verify with advisor)".
4. Never hallucinate course codes, credit counts, or requirements. If unsure, say so.
5. For four-year plans or course sequences, reproduce tables faithfully — use markdown tables.
6. Be concise and direct. Students need actionable answers, not disclaimers.
7. After your answer, add "💡 You might also ask:" with 3 specific follow-up questions.

SOURCE TAGS:
  [TABLE]  = structured catalog data (four-year plans, requirement lists). Trust it for
             course codes, credit counts, and semester sequences.
  [HEADER] = section header from a catalog page. Use to understand document structure.

FORMAT FOR COURSE PLANS:
| Semester | Course | Credits |
|----------|--------|---------|
Use this table format whenever showing a schedule or course list.

FORMAT FOR COMPARISONS:
Use a two-column markdown table.

If truly unable to answer: "I don't have enough information for that.
Check catalog.iastate.edu or contact your advisor at [college]@iastate.edu"
"""


def _build_context(chunks: List[Chunk]) -> str:
    blocks = []
    seen_urls: set[str] = set()
    for i, c in enumerate(chunks, 1):
        label = c.url if c.url not in seen_urls else f"{c.url} (cont.)"
        seen_urls.add(c.url)
        blocks.append(f"[Source {i}] {label}\n{c.text}")
    return "\n\n---\n\n".join(blocks)


def stream_answer(
    question: str,
    chunks:   List[Chunk],
    history:  List[dict],
) -> Generator[str, None, None]:
    context  = _build_context(chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # FIX #5: Slice last 8 entries (4 turns), then ensure we never start
    # mid-turn. If the first entry after slicing is an assistant message
    # (i.e. we cut the user message it was replying to), drop it so GPT-4o
    # always sees complete user→assistant pairs.
    tail = history[-8:]
    if tail and tail[0]["role"] != "user":
        tail = tail[1:]

    messages += tail
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


def answer(question: str, chunks: List[Chunk], history: List[dict] = []) -> str:
    return "".join(stream_answer(question, chunks, history))
