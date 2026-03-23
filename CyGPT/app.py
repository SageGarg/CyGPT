"""
CyGPT — Iowa State University AI Assistant
Clean top-nav layout matching iastate.edu design language.
"""
from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from src.indexer import Chunk, load_index
from src.retriever import retrieve
from src.answerer import stream_answer
from src.features import (
    stream_degree_plan, stream_conflict_check,
    stream_comparison, transcribe_audio, parse_followups,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CyGPT | ISU Academic Assistant",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Full CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;600;700;900&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="block-container"],
[data-testid="stVerticalBlock"],
section.main, section.main > div {
    background: #F0F0F0 !important;
    font-family: 'Source Sans 3', 'Helvetica Neue', Arial, sans-serif !important;
    color: #1A1A1A !important;
}

/* ── Hide all Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
    visibility: hidden !important;
}

/* ── Main content padding ── */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    padding: 0 !important;
}

/* ── ISU Top bar ── */
.isu-topbar {
    background: #C8102E;
    border-bottom: 4px solid #F1BE48;
    padding: 0 32px;
    display: flex;
    align-items: center;
    gap: 12px;
    height: 54px;
    position: sticky;
    top: 0;
    z-index: 999;
}
.isu-topbar-logo {
    display: flex;
    flex-direction: column;
    line-height: 1;
    text-decoration: none;
    border-right: 1px solid rgba(255,255,255,0.3);
    padding-right: 16px;
    margin-right: 4px;
}
.isu-topbar-logo .uni  { font-size: 0.65rem; color: #F1BE48; letter-spacing: 3px; font-weight: 700; }
.isu-topbar-logo .name { font-size: 1.05rem; color: white; font-weight: 900; letter-spacing: 0.5px; }
.isu-topbar-app { font-size: 1.1rem; font-weight: 700; color: white; letter-spacing: -0.2px; }
.isu-topbar-sep { color: rgba(255,255,255,0.4); font-size: 1.2rem; }

/* ── Nav tabs bar ── */
.isu-nav {
    background: #1A1A1A;
    padding: 0 32px;
    display: flex;
    gap: 2px;
    border-bottom: 3px solid #C8102E;
}
.isu-nav a {
    color: rgba(255,255,255,0.75);
    text-decoration: none;
    font-size: 0.88rem;
    font-weight: 600;
    padding: 13px 20px;
    border-bottom: 3px solid transparent;
    margin-bottom: -3px;
    transition: all 0.15s;
    cursor: pointer;
    white-space: nowrap;
}
.isu-nav a:hover { color: white; background: rgba(255,255,255,0.08); }
.isu-nav a.active { color: white; border-bottom-color: #F1BE48; }

/* ── Page content wrapper ── */
.isu-content {
    max-width: 1100px;
    margin: 0 auto;
    padding: 28px 32px 120px;
}

/* ── Hero banner ── */
.isu-hero {
    background: linear-gradient(135deg, #C8102E 0%, #8B0000 100%);
    border-radius: 14px;
    border-bottom: 5px solid #F1BE48;
    padding: 28px 36px;
    margin-bottom: 28px;
    box-shadow: 0 6px 24px rgba(200,16,46,0.2);
}
.isu-hero h1 {
    color: white !important;
    font-size: 2.1rem !important;
    font-weight: 900 !important;
    margin: 0 0 6px !important;
    letter-spacing: -0.5px !important;
}
.isu-hero p {
    color: rgba(255,255,255,0.88) !important;
    font-size: 0.96rem !important;
    margin: 0 !important;
}
.isu-hero .gold { color: #F1BE48 !important; font-weight: 700 !important; }

/* ── Section label ── */
.isu-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 12px;
}

/* ── Starter buttons ── */
.stButton > button {
    background: white !important;
    color: #C8102E !important;
    border: 2px solid #C8102E !important;
    border-radius: 8px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
    padding: 10px 14px !important;
    white-space: normal !important;
    height: auto !important;
    min-height: 52px !important;
    line-height: 1.35 !important;
    transition: all 0.14s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: #C8102E !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(200,16,46,0.28) !important;
    transform: translateY(-1px) !important;
}
[data-testid="baseButton-primary"] {
    background: #C8102E !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 12px 28px !important;
    border-radius: 8px !important;
    box-shadow: 0 3px 12px rgba(200,16,46,0.3) !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #9B0020 !important;
    transform: translateY(-1px) !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: white !important;
    border: 1px solid #E5E5E5 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    color: #1A1A1A !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span {
    color: #1A1A1A !important;
}
/* User — gold accent */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    border-left: 5px solid #F1BE48 !important;
    background: #FEFAE8 !important;
}
/* Assistant — cardinal accent */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    border-left: 5px solid #C8102E !important;
}

/* ── Chat input ── */
[data-testid="stBottom"] {
    background: #F0F0F0 !important;
    padding: 12px 0 !important;
    border-top: 2px solid #E0E0E0 !important;
}
[data-testid="stChatInputContainer"] {
    background: white !important;
    border: 2px solid #DCDCDC !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08) !important;
}
[data-testid="stChatInputContainer"]:focus-within {
    border-color: #C8102E !important;
    box-shadow: 0 0 0 3px rgba(200,16,46,0.1) !important;
}
[data-testid="stChatInputTextArea"] {
    background: white !important;
    color: #1A1A1A !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 0.97rem !important;
}
[data-testid="stChatInputTextArea"]::placeholder { color: #AAAAAA !important; }

/* ── Text inputs / textareas ── */
.stTextInput > div > div,
.stTextArea > div > div {
    background: white !important;
    border: 1.5px solid #DCDCDC !important;
    border-radius: 8px !important;
}
.stTextInput input,
.stTextArea textarea {
    background: white !important;
    color: #1A1A1A !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 0.96rem !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder { color: #AAAAAA !important; }
.stTextInput > div > div:focus-within,
.stTextArea > div > div:focus-within {
    border-color: #C8102E !important;
    box-shadow: 0 0 0 3px rgba(200,16,46,0.1) !important;
}
.stTextInput label, .stTextArea label {
    color: #1A1A1A !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* ── Source cards ── */
.src-card {
    background: white;
    border: 1px solid #E5E5E5;
    border-left: 5px solid #C8102E;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 0.83rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.src-card a { color: #C8102E !important; font-weight: 700; text-decoration: none; }
.src-card a:hover { text-decoration: underline; }
.src-card small { color: #666 !important; display: block; margin-top: 4px; }
.badge {
    display: inline-block;
    background: #F1BE48;
    color: #5A3C00;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.70rem;
    font-weight: 800;
    margin-left: 8px;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: white !important;
    border: 1px solid #E5E5E5 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary p { color: #C8102E !important; font-weight: 700 !important; }
[data-testid="stExpander"] > details > summary {
    background: #F9F9F9 !important;
}

/* ── Toggle ── */
.stToggle span { color: #1A1A1A !important; font-size: 0.9rem !important; }

/* ── Divider ── */
hr { border: none !important; border-top: 2px solid #E5E5E5 !important; margin: 20px 0 !important; }

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Audio ── */
[data-testid="stAudioInput"] {
    background: white !important;
    border: 1.5px solid #DCDCDC !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Load index ────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="📚 Loading index…")
def _load():
    return load_index()

try:
    faiss_index, bm25, chunks = _load()
except FileNotFoundError:
    st.error("No index found. Run `python ingest.py` first.")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"messages": [], "history": [], "mode": "chat", "pending_q": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helper: render source cards ───────────────────────────────────────────────
def render_sources(sources: list[Chunk]):
    for i, c in enumerate(sources, 1):
        st.markdown(
            f'<div class="src-card"><strong>Source {i}</strong>'
            f'<span class="badge">score {c.score:.1f}</span><br>'
            f'<a href="{c.url}" target="_blank">{c.url}</a>'
            f'<small>{c.text[:240]}…</small></div>',
            unsafe_allow_html=True,
        )

# ── Top bar + Nav (rendered as HTML, mode stored in session) ──────────────────
st.markdown(f"""
<div class="isu-topbar">
    <div class="isu-topbar-logo">
        <span class="uni">IOWA STATE</span>
        <span class="name">UNIVERSITY</span>
    </div>
    <span class="isu-topbar-sep">/</span>
    <span class="isu-topbar-app">🌪️ CyGPT</span>
    <span style="margin-left:auto;color:rgba(255,255,255,0.6);font-size:0.8rem">
        {len(chunks):,} chunks indexed
    </span>
</div>
""", unsafe_allow_html=True)

# ── Nav tabs ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Style st.tabs to look like ISU nav bar */
[data-testid="stTabs"] {
    background: #1A1A1A !important;
    padding: 0 24px !important;
    border-bottom: 3px solid #C8102E !important;
    margin-bottom: 0 !important;
}
[data-testid="stTabs"] > div:first-child {
    background: #1A1A1A !important;
    border-bottom: none !important;
    gap: 0 !important;
}
button[data-baseweb="tab"] {
    background: transparent !important;
    color: rgba(255,255,255,0.72) !important;
    font-size: 0.93rem !important;
    font-weight: 600 !important;
    padding: 14px 24px !important;
    border: none !important;
    border-bottom: 3px solid transparent !important;
    border-radius: 0 !important;
    font-family: 'Source Sans 3', sans-serif !important;
}
button[data-baseweb="tab"]:hover {
    color: white !important;
    background: rgba(255,255,255,0.08) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: white !important;
    border-bottom: 3px solid #F1BE48 !important;
    background: transparent !important;
}
/* Hide the tab indicator line Streamlit adds */
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    display: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}
/* Tab content area */
[data-testid="stTabsContent"] {
    padding: 0 !important;
    background: #F0F0F0 !important;
}
</style>
""", unsafe_allow_html=True)

tab_chat, tab_planner, tab_conflict, tab_compare = st.tabs([
    "💬  Chat",
    "🎓  Degree Planner",
    "⚠️  Conflict Checker",
    "⚖️  Compare Majors",
])

st.markdown('<div class="isu-content">', unsafe_allow_html=True)

# ── Settings row ─────────────────────────────────────────────────────────────
with st.expander("⚙️ Settings & Voice Input", expanded=False):
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        expand_queries = st.toggle("🔍 Query expansion", value=True,
            help="Rewrites your question 3 ways for better recall")
    with col2:
        audio_data = st.audio_input("🎤 Speak your question", label_visibility="visible")
        if audio_data:
            with st.spinner("Transcribing…"):
                try:
                    transcript = transcribe_audio(audio_data.read(), "q.webm")
                    st.session_state.pending_q = transcript
                    st.success(f"Heard: *{transcript}*")
                    st.rerun()
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
    with col3:
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.history  = []
            st.rerun()

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.markdown(f"""
    <div class="isu-hero">
        <h1>🌪️ CyGPT</h1>
        <p>Iowa State University Academic Assistant &nbsp;·&nbsp;
        Searching <span class="gold">{len(chunks):,} indexed chunks</span>
        from the ISU catalog, PDFs, and course pages.</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown('<div class="isu-label">Try asking</div>', unsafe_allow_html=True)
        starters = [
            "What are the CS BS requirements?",
            "Tell me about pre-med pathways.",
            "Minors in the College of Engineering?",
            "Four year plan for Computer Science BS",
            "Difference between CS and SE?",
            "College of Business certificates",
        ]
        c1, c2, c3 = st.columns(3)
        for col, prompt in zip([c1,c2,c3,c1,c2,c3], starters):
            with col:
                if st.button(prompt, use_container_width=True, key=f"s_{prompt[:20]}"):
                    st.session_state.pending_q = prompt
                    st.rerun()
        st.divider()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                if msg.get("followups"):
                    fc = st.columns(len(msg["followups"]))
                    for col, fq in zip(fc, msg["followups"]):
                        if col.button(fq, key=f"fq_{hash(fq)}", use_container_width=True):
                            st.session_state.pending_q = fq
                            st.rerun()
                if msg.get("sources"):
                    with st.expander(f"📚 {len(msg['sources'])} sources used"):
                        render_sources(msg["sources"])

    question = st.session_state.pop("pending_q", None) or st.chat_input(
        "Ask about courses, majors, requirements, prerequisites…"
    )

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.spinner("Searching the catalog…"):
            hits = retrieve(question, faiss_index, bm25, chunks, expand=expand_queries)

        full = ""
        with st.chat_message("assistant"):
            ph = st.empty()
            for tok in stream_answer(question, hits, st.session_state.history):
                full += tok
                ph.markdown(full + "▌")
            ph.markdown(full)

            main_text, followups = parse_followups(full)
            ph.markdown(main_text)

            if followups:
                fc = st.columns(len(followups))
                for col, fq in zip(fc, followups):
                    if col.button(fq, key=f"fqn_{hash(fq)}", use_container_width=True):
                        st.session_state.pending_q = fq
                        st.rerun()

            if hits:
                with st.expander(f"📚 {len(hits)} sources used"):
                    render_sources(hits)

        st.session_state.history += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": full},
        ]
        st.session_state.messages.append({
            "role": "assistant", "content": main_text,
            "followups": followups, "sources": hits,
        })


# ═══════════════════════════════════════════════════════════════════════════════
#  DEGREE PLANNER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_planner:
    st.markdown(f"""
    <div class="isu-hero">
        <h1>🎓 Degree Planner</h1>
        <p>Enter any ISU major and get a full 4-year semester-by-semester plan
        pulled directly from the catalog.</p>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([5, 1])
    with c1:
        major_input = st.text_input("Major name", placeholder="e.g. Computer Science, B.S.")
    with c2:
        st.markdown("<div style='margin-top:26px'/>", unsafe_allow_html=True)
        go = st.button("Generate plan", type="primary", use_container_width=True)

    if go and major_input.strip():
        with st.spinner(f"Finding {major_input} requirements…"):
            hits = retrieve(
                f"four year plan {major_input} course sequence credits requirements",
                faiss_index, bm25, chunks, expand=True)
        st.divider()
        with st.chat_message("assistant"):
            ph, result = st.empty(), ""
            for tok in stream_degree_plan(major_input.strip(), hits):
                result += tok
                ph.markdown(result + "▌")
            ph.markdown(result)
            if hits:
                with st.expander(f"📚 {len(hits)} sources used"):
                    render_sources(hits)
    elif go:
        st.warning("Please enter a major name.")


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFLICT CHECKER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_conflict:
    st.markdown(f"""
    <div class="isu-hero">
        <h1>⚠️ Conflict &amp; Prereq Checker</h1>
        <p>Paste your planned schedule — CyGPT flags missing prerequisites,
        wrong sequencing, and credit overloads.</p>
    </div>""", unsafe_allow_html=True)

    conflict_major = st.text_input("Your major", placeholder="e.g. Computer Science, B.S.")
    schedule_input = st.text_area("Your planned schedule (one semester per line)", height=220,
        placeholder=(
            "Freshman Fall:   COMS 1010, COMS 1270, MATH 1650, ENGL 1500\n"
            "Freshman Spring: COMS 2270, MATH 1660, ENGL 2500, LIB 1600\n"
            "Sophomore Fall:  COMS 2280, COMS 2300, MATH 2650\n"
            "Sophomore Spring: COMS 3210, COMS 3110\n..."
        ))

    if st.button("Check my schedule", type="primary"):
        if not schedule_input.strip():
            st.warning("Paste your schedule first.")
        else:
            with st.spinner("Checking prerequisites and sequencing…"):
                hits = retrieve(
                    f"{conflict_major} prerequisites required courses sequence",
                    faiss_index, bm25, chunks, expand=True)
            st.divider()
            with st.chat_message("assistant"):
                ph, result = st.empty(), ""
                for tok in stream_conflict_check(schedule_input.strip(), conflict_major or "undeclared", hits):
                    result += tok
                    ph.markdown(result + "▌")
                ph.markdown(result)
                if hits:
                    with st.expander(f"📚 {len(hits)} sources used"):
                        render_sources(hits)


# ═══════════════════════════════════════════════════════════════════════════════
#  COMPARE MAJORS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown(f"""
    <div class="isu-hero">
        <h1>⚖️ Major Comparison</h1>
        <p>Compare any two ISU majors side by side — credits, requirements,
        flexibility, and career paths.</p>
    </div>""", unsafe_allow_html=True)

    c1, mid, c2 = st.columns([5, 1, 5])
    with c1:
        major_a = st.text_input("First major", placeholder="e.g. Computer Science, B.S.")
    with mid:
        st.markdown("<div style='text-align:center;margin-top:30px;font-size:1.6rem;color:#C8102E;font-weight:900'>vs</div>",
                    unsafe_allow_html=True)
    with c2:
        major_b = st.text_input("Second major", placeholder="e.g. Software Engineering, B.S.")

    if st.button("Compare majors", type="primary"):
        if not major_a.strip() or not major_b.strip():
            st.warning("Enter both major names.")
        else:
            with st.spinner(f"Comparing {major_a} vs {major_b}…"):
                hits = retrieve(
                    f"{major_a} {major_b} requirements credits courses curriculum",
                    faiss_index, bm25, chunks, expand=True)
            st.divider()
            with st.chat_message("assistant"):
                ph, result = st.empty(), ""
                for tok in stream_comparison(major_a.strip(), major_b.strip(), hits):
                    result += tok
                    ph.markdown(result + "▌")
                ph.markdown(result)
                if hits:
                    with st.expander(f"📚 {len(hits)} sources used"):
                        render_sources(hits)

st.markdown('</div>', unsafe_allow_html=True)
