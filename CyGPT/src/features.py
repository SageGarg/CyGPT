"""
CyGPT Feature Modules
=====================
  1. degree_planner()    – generate a full 4-year schedule for any major
  2. conflict_checker()  – detect prereq / sequencing violations in a schedule
  3. compare_majors()    – side-by-side markdown table of two majors
  4. transcribe_audio()  – Whisper API voice → text
"""
from __future__ import annotations

import json
import re
import sys
import pathlib
from typing import Generator, List

from openai import OpenAI

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from config import CHAT_MODEL, OPENAI_API_KEY
from src.indexer import Chunk

client = OpenAI(api_key=OPENAI_API_KEY)


def _context(chunks: List[Chunk]) -> str:
    return "\n\n---\n\n".join(
        f"[Source {i}] {c.url}\n{c.text}"
        for i, c in enumerate(chunks, 1)
    )


# ── 1. Degree Planner ─────────────────────────────────────────────────────────

PLANNER_SYSTEM = """You are CyGPT, an academic planning assistant for Iowa State University.
Using ONLY the provided sources, generate a detailed 4-year semester-by-semester degree plan.

Output format — use this EXACT markdown table structure for each year:

### Freshman Year
| Semester | Course | Credits |
|----------|--------|---------|
| Fall | COURSE NAME | N |
| Spring | COURSE NAME | N |

Add a **Total credits** row at the end of each year.
After all 4 years, add:
- **Total degree credits:** N
- **Notes:** any important requirements, GPA thresholds, application deadlines

If a four-year plan is directly in the sources, reproduce it faithfully.
Cite sources like (Source N) after each semester block.
If you cannot find enough information, say so clearly."""


def stream_degree_plan(
    major: str,
    chunks: List[Chunk],
) -> Generator[str, None, None]:
    ctx = _context(chunks)
    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": f"Sources:\n\n{ctx}\n\nGenerate the 4-year plan for: {major}"},
        ],
        temperature=0.1,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta


# ── 2. Conflict / Prereq Checker ─────────────────────────────────────────────

CONFLICT_SYSTEM = """You are CyGPT, an academic advisor assistant for Iowa State University.
A student will provide their planned course schedule. Using the provided catalog sources,
check for:
  1. Missing prerequisites (taking a course before its prereq)
  2. Courses that must be taken in a specific sequence
  3. Credit hour overloads (flag any semester over 18 credits)
  4. Missing required core courses for their major

Output format:
## Schedule review

### Issues found
| # | Severity | Course | Problem | Fix |
|---|----------|--------|---------|-----|
| 1 | 🔴 Critical | COMS 2280 | Missing prereq COMS 1270 | Move COMS 1270 to Fall Yr 1 |

### Looks good
List courses/semesters that are correctly sequenced.

### Recommendations
2-3 bullet suggestions to strengthen the plan.

If the sources don't contain enough info to verify a course, say "Could not verify" for that row."""


def stream_conflict_check(
    schedule_text: str,
    major: str,
    chunks: List[Chunk],
) -> Generator[str, None, None]:
    ctx = _context(chunks)
    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": CONFLICT_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Sources:\n\n{ctx}\n\n"
                    f"Major: {major}\n\n"
                    f"Student's planned schedule:\n{schedule_text}"
                ),
            },
        ],
        temperature=0.1,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta


# ── 3. Major Comparison ───────────────────────────────────────────────────────

COMPARE_SYSTEM = """You are CyGPT, an academic advisor assistant for Iowa State University.
Compare two ISU majors using ONLY the provided sources.

Output a structured markdown comparison:

## [Major A] vs [Major B]

| Category | [Major A] | [Major B] |
|----------|-----------|-----------|
| College | | |
| Total credits | | |
| Core courses | | |
| Math requirements | | |
| Science requirements | | |
| Lab requirements | | |
| Elective flexibility | | |
| Typical career paths | | |
| Notable strengths | | |

### Key differences
3-5 bullet points on the most important distinctions.

### Which to choose if…
- You prefer X → [Major A/B] because…
- You prefer Y → [Major A/B] because…

Cite sources like (Source N). If info is missing for a field, write "See advisor"."""


def stream_comparison(
    major_a: str,
    major_b: str,
    chunks: List[Chunk],
) -> Generator[str, None, None]:
    ctx = _context(chunks)
    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": COMPARE_SYSTEM},
            {
                "role": "user",
                "content": f"Sources:\n\n{ctx}\n\nCompare these two majors:\n1. {major_a}\n2. {major_b}",
            },
        ],
        temperature=0.1,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta


# ── 4. Voice Transcription ───────────────────────────────────────────────────

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribe audio bytes using OpenAI Whisper.
    Returns the transcribed text string.
    """
    import io
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="en",
    )
    return result.text


# ── 5. Follow-up chip parser ──────────────────────────────────────────────────

def parse_followups(response_text: str) -> tuple[str, list[str]]:
    """
    Split a GPT response into (main_answer, [followup1, followup2, followup3]).
    Looks for the '💡 You might also ask:' section.
    """
    marker = "💡 You might also ask:"
    if marker not in response_text:
        return response_text, []

    parts      = response_text.split(marker, 1)
    main       = parts[0].strip()
    followup_block = parts[1].strip()

    followups = []
    for line in followup_block.splitlines():
        line = line.strip().lstrip("•·-*").strip()
        if line:
            followups.append(line)

    return main, followups[:3]
