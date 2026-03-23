"""
CyGPT – Streamlit Chat UI
=========================
Streaming chat interface with:
  • Multi-turn conversation memory
  • Expandable source cards (URL + snippet + reranker score)
  • Query expansion toggle
  • Live typing indicator
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from config import INDEX_DIR
from src.indexer import Chunk, load_index
from src.retriever import retrieve
from src.answerer import stream_answer

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CyGPT | ISU Assistant",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Source cards */
.source-card {
    background: #1e2329;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 0.85rem;
}
.source-card a { color: #58a6ff; text-decoration: none; }
.source-card a:hover { text-decoration: underline; }
.score-badge {
    display: inline-block;
    background: #238636;
    color: white;
    border-radius: 12px;
    padding: 1px 8px;
    font-size: 0.75rem;
    margin-left: 8px;
}
/* Sidebar */
[data-testid="stSidebar"] { background: #0d1117; }
/* Hide Streamlit branding */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌪️ CyGPT")
    st.caption("Iowa State University AI Assistant")
    st.divider()

    expand_queries = st.toggle(
        "🔍 Query Expansion",
        value=True,
        help="Generate multiple search variants for better recall. "
             "Adds ~1s but improves answer quality significantly.",
    )

    st.divider()
    st.markdown("**How it works**")
    st.markdown("""
1. Your question is expanded into variants
2. Hybrid BM25 + vector search finds candidates
3. A cross-encoder reranks for precision
4. GPT-4o synthesises a cited answer
    """)

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history  = []
        st.rerun()

    st.divider()
    st.caption("Built with GPT-4o · FAISS · BM25 · sentence-transformers")


# ── Load index (cached across sessions) ──────────────────────────────────────
@st.cache_resource(show_spinner="📚 Loading search index…")
def _load():
    return load_index()


try:
    faiss_index, bm25, chunks = _load()
except FileNotFoundError:
    st.error(
        "**No index found.**  \n"
        "Please run `python ingest.py` first, then refresh this page."
    )
    st.stop()


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history  = []


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🌪️  CyGPT — Iowa State University Assistant")
st.caption(
    f"Searching across **{len(chunks):,}** indexed chunks from the ISU catalog. "
    "Ask about majors, courses, requirements, pre-professional tracks, and more."
)

# ── Starter prompts (shown on first load) ────────────────────────────────────
if not st.session_state.messages:
    st.markdown("#### Try asking:")
    cols = st.columns(3)
    starters = [
        "What are the requirements for a Computer Science BS?",
        "Tell me about pre-med pathways at ISU.",
        "What minors are available in the College of Engineering?",
        "How do I apply for a second major?",
        "What is the difference between the Biology BS in LAS vs CALS?",
        "List all certificates offered by the College of Business.",
    ]
    for col, prompt in zip(cols * 2, starters):
        if col.button(prompt, use_container_width=True):
            st.session_state._starter = prompt
            st.rerun()

    # Handle starter button click
    if starter := st.session_state.pop("_starter", None):
        st.session_state.messages.append({"role": "user", "content": starter})

st.divider()

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Source cards for assistant messages
        if msg["role"] == "assistant" and msg.get("sources"):
            sources: list[Chunk] = msg["sources"]
            with st.expander(f"📚 {len(sources)} sources used", expanded=False):
                for i, chunk in enumerate(sources, 1):
                    score_color = (
                        "green" if chunk.score > 5
                        else "orange" if chunk.score > 0
                        else "red"
                    )
                    st.markdown(
                        f'<div class="source-card">'
                        f'<strong>Source {i}</strong>'
                        f'<span class="score-badge">score {chunk.score:.2f}</span><br>'
                        f'<a href="{chunk.url}" target="_blank">{chunk.url}</a><br>'
                        f'<small style="color:#8b949e">{chunk.text[:280]}…</small>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )


# ── Chat input ────────────────────────────────────────────────────────────────
if question := st.chat_input("Ask about ISU courses, majors, requirements…"):

    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Retrieve
    with st.spinner("🔍 Searching the catalog…"):
        hits = retrieve(
            question, faiss_index, bm25, chunks,
            expand=expand_queries,
        )

    # Stream GPT-4o answer
    with st.chat_message("assistant"):
        response = st.write_stream(
            stream_answer(question, hits, st.session_state.history)
        )

        # Source cards inline
        if hits:
            with st.expander(f"📚 {len(hits)} sources used", expanded=False):
                for i, chunk in enumerate(hits, 1):
                    st.markdown(
                        f'<div class="source-card">'
                        f'<strong>Source {i}</strong>'
                        f'<span class="score-badge">score {chunk.score:.2f}</span><br>'
                        f'<a href="{chunk.url}" target="_blank">{chunk.url}</a><br>'
                        f'<small style="color:#8b949e">{chunk.text[:280]}…</small>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    # Persist to history and message log
    st.session_state.history += [
        {"role": "user",      "content": question},
        {"role": "assistant", "content": response},
    ]
    st.session_state.messages.append({
        "role":    "assistant",
        "content": response,
        "sources": hits,
    })
