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

st.set_page_config(
    page_title="CyGPT | ISU Academic Assistant",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700;900&display=swap');

/* ─── GLOBAL RESET ─────────────────────────────────── */
html, body { margin:0; padding:0; }

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
section.main,
section.main > div,
[data-testid="stVerticalBlock"] {
    background: #F4F4F4 !important;
    font-family: 'Source Sans 3', Arial, sans-serif !important;
    color: #1A1A1A !important;
}

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ─── HIDE ALL STREAMLIT CHROME ────────────────────── */
header[data-testid="stHeader"],
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

/* ─── TOP BAR ───────────────────────────────────────── */
.topbar {
    background: #C8102E;
    border-bottom: 4px solid #F1BE48;
    padding: 10px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.topbar-left { display: flex; align-items: center; gap: 14px; }
.topbar-brand { line-height: 1.1; }
.topbar-brand .uni  { font-size: 0.6rem; color: #F1BE48; letter-spacing: 3px; font-weight: 700; display:block; }
.topbar-brand .name { font-size: 1rem; color: white; font-weight: 900; letter-spacing: 0.5px; display:block; }
.topbar-divider { color: rgba(255,255,255,0.35); font-size: 1.4rem; }
.topbar-app { font-size: 1.15rem; font-weight: 700; color: white; }
.topbar-right { font-size: 0.8rem; color: rgba(255,255,255,0.65); }

/* ─── TABS ──────────────────────────────────────────── */
[data-testid="stTabs"] {
    background: #222222 !important;
    margin: 0 !important;
    padding: 0 28px !important;
}
[data-testid="stTabs"] > div:first-child {
    background: #222222 !important;
    border-bottom: 3px solid #C8102E !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #222222 !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}
button[data-baseweb="tab"] {
    background: transparent !important;
    color: rgba(255,255,255,0.65) !important;
    font-family: 'Source Sans 3', Arial, sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    padding: 14px 26px !important;
    border: none !important;
    border-bottom: 3px solid transparent !important;
    border-radius: 0 !important;
    margin-bottom: -3px !important;
}
button[data-baseweb="tab"]:hover {
    color: white !important;
    background: rgba(255,255,255,0.07) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: white !important;
    border-bottom: 3px solid #F1BE48 !important;
}
[data-testid="stTabsContent"] {
    padding: 28px 32px 100px !important;
    max-width: 1100px !important;
    margin: 0 auto !important;
    background: #F4F4F4 !important;
}

/* ─── HERO BANNER ───────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #C8102E 0%, #8B0000 100%);
    border-radius: 12px;
    border-bottom: 5px solid #F1BE48;
    padding: 26px 32px;
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(200,16,46,0.18);
}
.hero h1 { color:white !important; font-size:1.9rem !important; font-weight:900 !important; margin:0 0 6px !important; }
.hero p  { color:rgba(255,255,255,0.85) !important; font-size:0.95rem !important; margin:0 !important; }
.hero .gold { color:#F1BE48 !important; font-weight:700 !important; }

/* ─── SECTION LABEL ─────────────────────────────────── */
.sec-label {
    font-size: 0.72rem; font-weight: 700; color: #999;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px;
}

/* ─── BUTTONS ───────────────────────────────────────── */
.stButton > button {
    background: white !important;
    color: #C8102E !important;
    border: 2px solid #C8102E !important;
    border-radius: 8px !important;
    font-family: 'Source Sans 3', Arial, sans-serif !important;
    font-size: 0.87rem !important;
    font-weight: 600 !important;
    padding: 10px 14px !important;
    white-space: normal !important;
    height: auto !important;
    min-height: 50px !important;
    transition: all 0.15s !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: #C8102E !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(200,16,46,0.25) !important;
    transform: translateY(-1px) !important;
}
[data-testid="baseButton-primary"] {
    background: #C8102E !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    padding: 12px 28px !important;
    border-radius: 8px !important;
    box-shadow: 0 3px 10px rgba(200,16,46,0.3) !important;
    font-size: 0.95rem !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #9B0020 !important;
    transform: translateY(-1px) !important;
}

/* ─── CHAT MESSAGES ─────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: white !important;
    border: 1px solid #E5E5E5 !important;
    border-radius: 12px !important;
    margin-bottom: 10px !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06) !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] td,
[data-testid="stChatMessage"] th,
[data-testid="stChatMessage"] span { color: #1A1A1A !important; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    border-left: 5px solid #F1BE48 !important;
    background: #FFFDF0 !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    border-left: 5px solid #C8102E !important;
}

/* ─── CHAT INPUT ────────────────────────────────────── */
[data-testid="stBottom"] {
    background: #EFEFEF !important;
    border-top: 2px solid #E0E0E0 !important;
    padding: 10px 32px !important;
}
[data-testid="stChatInputContainer"] {
    background: white !important;
    border: 2px solid #DCDCDC !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07) !important;
}
[data-testid="stChatInputContainer"]:focus-within {
    border-color: #C8102E !important;
    box-shadow: 0 0 0 3px rgba(200,16,46,0.1) !important;
}
[data-testid="stChatInputTextArea"] {
    background: white !important;
    color: #1A1A1A !important;
    font-family: 'Source Sans 3', Arial, sans-serif !important;
    font-size: 0.97rem !important;
}
[data-testid="stChatInputTextArea"]::placeholder { color: #BBBBBB !important; }

/* ─── TEXT INPUTS ───────────────────────────────────── */
.stTextInput > div > div,
.stTextArea > div > div {
    background: white !important;
    border: 1.5px solid #DCDCDC !important;
    border-radius: 8px !important;
}
.stTextInput input, .stTextArea textarea {
    background: white !important;
    color: #1A1A1A !important;
    font-family: 'Source Sans 3', Arial, sans-serif !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #BBBBBB !important; }
.stTextInput > div > div:focus-within,
.stTextArea > div > div:focus-within {
    border-color: #C8102E !important;
    box-shadow: 0 0 0 3px rgba(200,16,46,0.1) !important;
}
.stTextInput label, .stTextArea label {
    color: #444 !important; font-weight: 700 !important;
    font-size: 0.8rem !important; text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* ─── SOURCE CARDS ──────────────────────────────────── */
.src {
    background: white; border: 1px solid #E5E5E5;
    border-left: 5px solid #C8102E; border-radius: 0 10px 10px 0;
    padding: 12px 16px; margin: 6px 0;
    font-size: 0.83rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.src a { color: #C8102E !important; font-weight:700; text-decoration:none; font-size:0.82rem; }
.src a:hover { text-decoration: underline; }
.src small { color: #777 !important; display:block; margin-top:4px; line-height:1.4; }
.badge {
    display:inline-block; background:#F1BE48; color:#5A3C00;
    border-radius:20px; padding:2px 9px; font-size:0.7rem;
    font-weight:800; margin-left:8px;
}

/* ─── EXPANDERS ─────────────────────────────────────── */
[data-testid="stExpander"] {
    background: white !important; border: 1px solid #E5E5E5 !important;
    border-radius: 10px !important; overflow: hidden !important;
}
[data-testid="stExpander"] summary { background: #F9F9F9 !important; }
[data-testid="stExpander"] summary p { color: #C8102E !important; font-weight:700 !important; font-size:0.88rem !important; }

/* ─── SETTINGS ROW ──────────────────────────────────── */
.settings-bar {
    background: white; border: 1px solid #E5E5E5; border-radius: 10px;
    padding: 14px 20px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* ─── MISC ──────────────────────────────────────────── */
hr { border:none !important; border-top: 2px solid #E8E8E8 !important; margin: 20px 0 !important; }
[data-testid="stToggle"] span { color: #1A1A1A !important; font-size:0.9rem !important; }
[data-testid="stAudioInput"] { background: white !important; border: 1.5px solid #DCDCDC !important; border-radius: 8px !important; }
[data-testid="stAlert"] { border-radius: 10px !important; }
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
for k, v in {"messages": [], "history": [], "pending_q": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helper ────────────────────────────────────────────────────────────────────
def render_sources(sources: list[Chunk]):
    for i, c in enumerate(sources, 1):
        st.markdown(
            f'<div class="src"><strong>Source {i}</strong>'
            f'<span class="badge">score {c.score:.1f}</span><br>'
            f'<a href="{c.url}" target="_blank">{c.url}</a>'
            f'<small>{c.text[:240]}…</small></div>',
            unsafe_allow_html=True,
        )

# ── Top bar ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topbar">
  <div class="topbar-left">
    <div class="topbar-brand">
      <span class="uni">IOWA STATE</span>
      <span class="name">UNIVERSITY</span>
    </div>
    <span class="topbar-divider">/</span>
    <span class="topbar-app">🌪️ CyGPT</span>
  </div>
  <div class="topbar-right">{len(chunks):,} chunks indexed</div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chat, tab_planner, tab_conflict, tab_compare = st.tabs([
    "💬  Chat",
    "🎓  Degree Planner",
    "⚠️  Conflict Checker",
    "⚖️  Compare Majors",
])

# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT TAB
# ═══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.markdown(f"""
    <div class="hero">
      <h1>🌪️ CyGPT</h1>
      <p>Iowa State University Academic Assistant &nbsp;·&nbsp;
      Searching <span class="gold">{len(chunks):,} indexed chunks</span>
      from the ISU catalog, PDFs, and course pages.</p>
    </div>""", unsafe_allow_html=True)

    # ── Settings row ──────────────────────────────────────────────────────────
    with st.expander("⚙️  Settings & Tools", expanded=False):
        s1, s2, s3 = st.columns([2, 3, 2])
        with s1:
            expand_queries = st.toggle("🔍 Query expansion", value=True,
                help="Rewrites your question 3 ways for better recall")
        with s2:
            audio_data = st.audio_input("🎤 Speak your question",
                                        label_visibility="visible")
            if audio_data:
                with st.spinner("Transcribing…"):
                    try:
                        t = transcribe_audio(audio_data.read(), "q.webm")
                        st.session_state.pending_q = t
                        st.success(f"Heard: *{t}*")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")
        with s3:
            st.write("")
            if st.button("🗑️ Clear conversation", use_container_width=True):
                st.session_state.messages = []
                st.session_state.history  = []
                st.rerun()

    expand_queries = True  # always on by default

    # ── Starter prompts ───────────────────────────────────────────────────────
    if not st.session_state.messages:
        st.markdown('<div class="sec-label">Try asking</div>', unsafe_allow_html=True)
        starters = [
            "What are the CS BS requirements?",
            "Tell me about pre-med pathways.",
            "Minors in the College of Engineering?",
            "Four year plan for Computer Science BS",
            "Difference between CS and SE?",
            "College of Business certificates",
        ]
        c1, c2, c3 = st.columns(3)
        for col, p in zip([c1,c2,c3,c1,c2,c3], starters):
            with col:
                if st.button(p, key=f"s_{p[:18]}", use_container_width=True):
                    st.session_state.pending_q = p
                    st.rerun()
        st.write("")

    # ── Chat history ──────────────────────────────────────────────────────────
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

    # (chat input is rendered below, outside tabs, so it always stays visible)

# ═══════════════════════════════════════════════════════════════════════════════
#  DEGREE PLANNER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_planner:
    st.markdown("""
    <div class="hero">
      <h1>🎓 Degree Planner</h1>
      <p>Enter any ISU major and get a full 4-year semester-by-semester plan
      pulled directly from the catalog.</p>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([5, 1])
    with c1:
        major_input = st.text_input("Major name",
            placeholder="e.g. Computer Science, B.S.",
            key="planner_major")
    with c2:
        st.write("")
        st.write("")
        go = st.button("Generate", type="primary",
                        use_container_width=True, key="planner_go")

    if go and major_input.strip():
        with st.spinner(f"Finding {major_input} requirements…"):
            hits = retrieve(
                f"four year plan {major_input} course sequence credits requirements",
                faiss_index, bm25, chunks, expand=True)
        st.divider()
        with st.chat_message("assistant"):
            ph, result = st.empty(), ""
            for tok in stream_degree_plan(major_input.strip(), hits):
                result += tok; ph.markdown(result + "▌")
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
    st.markdown("""
    <div class="hero">
      <h1>⚠️ Conflict &amp; Prereq Checker</h1>
      <p>Paste your planned schedule — CyGPT flags missing prerequisites,
      wrong sequencing, and credit overloads.</p>
    </div>""", unsafe_allow_html=True)

    conflict_major = st.text_input("Your major",
        placeholder="e.g. Computer Science, B.S.", key="conflict_major")
    schedule_input = st.text_area(
        "Your planned schedule (one semester per line)", height=200,
        placeholder=(
            "Freshman Fall:   COMS 1010, COMS 1270, MATH 1650, ENGL 1500\n"
            "Freshman Spring: COMS 2270, MATH 1660, ENGL 2500, LIB 1600\n"
            "Sophomore Fall:  COMS 2280, COMS 2300, MATH 2650\n"
            "Sophomore Spring: COMS 3210, COMS 3110, COMS 3000 elective\n..."
        ), key="conflict_schedule")

    if st.button("Check my schedule", type="primary", key="conflict_go"):
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
                for tok in stream_conflict_check(
                        schedule_input.strip(), conflict_major or "undeclared", hits):
                    result += tok; ph.markdown(result + "▌")
                ph.markdown(result)
                if hits:
                    with st.expander(f"📚 {len(hits)} sources used"):
                        render_sources(hits)

# ═══════════════════════════════════════════════════════════════════════════════
#  COMPARE MAJORS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("""
    <div class="hero">
      <h1>⚖️ Major Comparison</h1>
      <p>Compare any two ISU majors side by side — credits, requirements,
      flexibility, and career paths.</p>
    </div>""", unsafe_allow_html=True)

    c1, mid, c2 = st.columns([5, 1, 5])
    with c1:
        major_a = st.text_input("First major",
            placeholder="e.g. Computer Science, B.S.", key="cmp_a")
    with mid:
        st.markdown(
            "<div style='text-align:center;margin-top:32px;"
            "font-size:1.5rem;color:#C8102E;font-weight:900'>vs</div>",
            unsafe_allow_html=True)
    with c2:
        major_b = st.text_input("Second major",
            placeholder="e.g. Software Engineering, B.S.", key="cmp_b")

    if st.button("Compare majors", type="primary", key="cmp_go"):
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
                    result += tok; ph.markdown(result + "▌")
                ph.markdown(result)
                if hits:
                    with st.expander(f"📚 {len(hits)} sources used"):
                        render_sources(hits)


# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT INPUT — outside tabs so it always stays visible
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.get("active_tab", "chat") == "chat" or True:
    question = st.session_state.pop("pending_q", None) or                st.chat_input("Ask about courses, majors, requirements, prerequisites…")

    if question:
        # Switch to chat tab context by storing and rerunning
        st.session_state.messages.append({"role": "user", "content": question})
        with tab_chat:
            with st.chat_message("user"):
                st.markdown(question)

            with st.spinner("Searching the catalog…"):
                hits = retrieve(question, faiss_index, bm25, chunks, expand=True)

            full = ""
            with st.chat_message("assistant"):
                ph = st.empty()
                for tok in stream_answer(question, hits, st.session_state.history):
                    full += tok
                    ph.markdown(full + "▌")
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
        st.rerun()