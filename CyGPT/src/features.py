"""
CyGPT Feature Modules
=====================
  1. degree_planner()    – generate a full 4-year schedule for any major
  2. prereq_checker()    – detect prereq / sequencing violations in a schedule
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

_PLANNER_PROGRAMS = {
    "undergrad": {
        "retrieve_hint": "four year plan",
        "system": """You are CyGPT, an academic planning assistant for Iowa State University.
Using ONLY the provided sources, generate a detailed 4-year semester-by-semester undergraduate degree plan.

Output format — use this EXACT markdown table structure for each year:

### Freshman Year
| Semester | Course | Credits |
|----------|--------|---------|
| Fall | COURSE NAME | N |
| Spring | COURSE NAME | N |

Repeat for Sophomore, Junior, and Senior years.
Add a **Total credits** row at the end of each year.
After all 4 years, add:
- **Total degree credits:** N
- **Notes:** GPA thresholds, gen-ed requirements, application deadlines

Flag any semester over 18 credits. If a four-year plan is in the sources, reproduce it faithfully.
Cite sources like (Source N) after each year block.""",
        "user_suffix": "Generate the 4-year undergraduate plan for",
    },
    "grad": {
        "retrieve_hint": "graduate two year plan master's",
        "system": """You are CyGPT, an academic planning assistant for Iowa State University.
Using ONLY the provided sources, generate a detailed 2-year semester-by-semester master's degree plan.

Output format — use this EXACT markdown table structure for each year:

### Graduate Year 1
| Semester | Course | Credits |
|----------|--------|---------|
| Fall | COURSE NAME | N |
| Spring | COURSE NAME | N |

### Graduate Year 2
(same table structure)

Add a **Total credits** row at the end of each year.
After both years, add:
- **Total degree credits:** N
- **Notes:** thesis/creative component options, graduate credit limits (15/semester typical), deadlines

Flag any semester over 15 credits. Cite sources like (Source N) after each year block.""",
        "user_suffix": "Generate the 2-year master's graduate plan for",
    },
    "phd": {
        "retrieve_hint": "PhD doctoral program plan coursework dissertation",
        "system": """You are CyGPT, an academic planning assistant for Iowa State University.
Using ONLY the provided sources, generate a doctoral (PhD) program plan — NOT a 4-year bachelor's layout.

Output format:

### Coursework phase
| Term | Course / milestone | Credits |
|------|------------------|---------|
| ... | ... | ... |

### Research & dissertation phase
| Stage | Activity | Notes |
|-------|----------|-------|
| ... | ... | ... |

Then add:
- **Total program credits (if stated):** N
- **Qualifying / comprehensive exams:** (from sources or "See advisor")
- **Dissertation requirements:** brief summary from sources
- **Notes:** residency, committee, typical timeline

Cite sources like (Source N). If sources lack PhD detail, say what is missing and advise consulting the DOGE/advisor.""",
        "user_suffix": "Generate the PhD doctoral program plan for",
    },
    "certificate": {
        "retrieve_hint": "certificate program requirements courses credits",
        "system": """You are CyGPT, an academic planning assistant for Iowa State University.
Using ONLY the provided sources, generate a certificate program plan (typically shorter than a full degree).

Output format:

### Required courses
| Course | Credits | Notes |
|--------|---------|-------|
| ... | ... | ... |

### Suggested sequence
| Term | Courses | Credits |
|------|---------|---------|
| ... | ... | ... |

Then add:
- **Total certificate credits:** N
- **Notes:** admission requirements, stackability with a degree, transcript notation

Cite sources like (Source N). If the certificate is course-list only (no semesters in sources), organize by requirement groups.""",
        "user_suffix": "Generate the certificate program plan for",
    },
}


def _planner_config(program_type: str) -> dict:
    return _PLANNER_PROGRAMS.get(program_type, _PLANNER_PROGRAMS["undergrad"])


def planner_retrieve_query(major: str, program_type: str) -> str:
    cfg = _planner_config(program_type)
    return f"{cfg['retrieve_hint']} {major} course sequence credits requirements"


def stream_degree_plan(
    major: str,
    chunks: List[Chunk],
    program_type: str = "undergrad",
) -> Generator[str, None, None]:
    cfg = _planner_config(program_type)
    ctx = _context(chunks)
    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": cfg["system"]},
            {
                "role": "user",
                "content": f"Sources:\n\n{ctx}\n\n{cfg['user_suffix']}: {major}",
            },
        ],
        temperature=0.1,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta


# ── 2. Pre Req Checker ───────────────────────────────────────────────────────

PREREQ_SYSTEM = """You are CyGPT, an academic advisor assistant for Iowa State University.
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


def stream_prereq_check(
    schedule_text: str,
    major: str,
    chunks: List[Chunk],
) -> Generator[str, None, None]:
    ctx = _context(chunks)
    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": PREREQ_SYSTEM},
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
