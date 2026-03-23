from __future__ import annotations
import sys, base64
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

# ── Logo as base64 for CSS embedding ─────────────────────────────────────────
LOGO_PATH = Path(__file__).parent / "static" / "logo.png"
if LOGO_PATH.exists():
    _logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
    LOGO_URI = f"data:image/png;base64,{_logo_b64}"
else:
    LOGO_URI = ""

st.set_page_config(
    page_title="CyGPT | ISU Academic Assistant",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ─── VARIABLES ─────────────────────────────────────── */
:root {
    --isu-red:       #C8102E;
    --isu-red-glow:  rgba(200, 16, 46, 0.35);
    --isu-dark-red:  #9B0020;
    --isu-gold:      #FDE68A;   /* lighter butter yellow */
    --isu-gold-mid:  #F1BE48;   /* standard ISU gold for accents */
    --isu-gold-dark: #C99A1A;
    --isu-gold-glow: rgba(253, 230, 138, 0.25);
    --bg-dark:       #12120F;   /* very dark warm-tinted black (not blue) */
    --bg-card:       #1C1C17;   /* warm dark card */
    --bg-card-hover: #242419;
    --bg-elevated:   #2A2A22;
    --bg-sidebar:    #0E0E0B;   /* darkest warm black for sidebar */
    --text-primary:  #F5F0E8;   /* warm white */
    --text-secondary:#A89F8C;   /* warm gray */
    --text-muted:    #6B6355;   /* warm muted */
    --border-color:  rgba(255,240,200,0.07);  /* warm-tinted border */
    --border-glow:   rgba(200, 16, 46, 0.3);
    --radius-sm:     10px;
    --radius-md:     14px;
    --radius-lg:     20px;
    --radius-xl:     24px;
    --shadow-card:   0 4px 24px rgba(0,0,0,0.35);
    --shadow-glow-red: 0 0 30px rgba(200,16,46,0.15);
    --transition:    all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

html, body { margin:0; padding:0; }

/* ─── GLOBAL ────────────────────────────────────────── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
section.main,
section.main > div,
[data-testid="stVerticalBlock"] {
    background: var(--bg-dark) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing: antialiased;
}

.block-container {
    padding: 1.5rem 3rem 6rem !important;
    max-width: 100% !important;
}

/* ─── HIDE STREAMLIT CHROME ─────────────────────────── */
header[data-testid="stHeader"],
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
}

/* ─── SIDEBAR ───────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-color) !important;
    width: 220px !important;
    min-width: 220px !important;
}
[data-testid="stSidebar"] > div:first-child {
    background: var(--bg-sidebar) !important;
    padding: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    overflow: hidden !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 100% !important;
    padding-bottom: 70px !important;
}
/* Logo — nuclear flush to top */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div,
[data-testid="stSidebar"] section,
[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stSidebar"] .stElementContainer,
[data-testid="stSidebar"] .block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stImage"],
[data-testid="stSidebar"] [data-testid="stImage"] > div {
    padding: 0 !important;
    margin: 0 !important;
    line-height: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stImage"] img {
    display: block !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    border-radius: 0 !important;
}
/* Push user profile to bottom */
[data-testid="stSidebar"] .sidebar-user-wrap {
    margin-top: auto !important;
}

/* Sidebar collapse button */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    color: var(--text-secondary) !important;
    background: transparent !important;
}

/* ─── SIDEBAR RADIO — hide dots, make clean nav ────── */
[data-testid="stSidebar"] .stRadio > div {
    gap: 0 !important;
}
[data-testid="stSidebar"] .stRadio > div > label {
    background: transparent !important;
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    padding: 11px 20px !important;
    border-radius: 0 !important;
    cursor: pointer !important;
    transition: var(--transition) !important;
    margin: 0 !important;
    border-left: 3px solid transparent !important;
    display: flex !important;
    align-items: center !important;
    gap: 0 !important;
}
/* Hide the radio circle completely */
[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(255,255,255,0.04) !important;
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background: rgba(200,16,46,0.1) !important;
    color: white !important;
    border-left: 3px solid var(--isu-red) !important;
    font-weight: 600 !important;
}
/* Hide the "Navigation" label text */
[data-testid="stSidebar"] .stRadio > label {
    display: none !important;
}

/* ─── SIDEBAR BUTTONS ──────────────────────────────── */
[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #2A2318 0%, #1E1A10 100%) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 10px 16px !important;
    width: 100% !important;
    transition: var(--transition) !important;
    margin: 4px 0 !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: linear-gradient(135deg, #3A3020 0%, #2E2614 100%) !important;
    border-color: rgba(255,255,255,0.2) !important;
}

/* ─── SIDEBAR DIVIDER ──────────────────────────────── */
[data-testid="stSidebar"] hr {
    border: none !important;
    border-top: 1px solid var(--border-color) !important;
    margin: 12px 16px !important;
}

/* ─── SIDEBAR TEXT ─────────────────────────────────── */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ─── ANIMATIONS ────────────────────────────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 20px rgba(200,16,46,0.2); }
    50%      { box-shadow: 0 0 40px rgba(200,16,46,0.4); }
}
@keyframes starRotate {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}

/* ─── HERO BANNER ───────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, var(--isu-red) 0%, var(--isu-dark-red) 60%, #3a0008 100%);
    border-radius: var(--radius-lg);
    padding: 36px 40px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(200,16,46,0.3);
    animation: fadeInUp 0.6s ease forwards;
    box-shadow: 0 8px 40px rgba(200,16,46,0.2);
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%; right: -30%;
    width: 60%; height: 200%;
    background: radial-gradient(ellipse, rgba(241,190,72,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.hero h1 {
    margin: 0 0 10px 0; font-size: 1.8rem;
    font-weight: 900; color: white !important;
    display: flex; align-items: center; gap: 12px;
}
.hero p {
    margin: 0; font-size: 0.95rem; line-height: 1.6;
    color: rgba(255,255,255,0.85) !important; max-width: 700px;
}
.hero .gold { color: var(--isu-gold) !important; font-weight: 700; }

/* ─── INDEXED BADGE ─────────────────────────────────── */
.index-badge {
    text-align: right;
    margin-bottom: 8px;
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: 500;
}

/* ─── SECTION LABEL ─────────────────────────────────── */
.sec-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    color: var(--text-muted);
    margin: 24px 0 14px;
    padding-left: 4px;
}

/* ─── STARTER PROMPT BUTTONS ────────────────────────── */
[data-testid="stVerticalBlock"] .stButton button {
    background: var(--bg-card) !important;
    border: 1px solid rgba(200,16,46,0.25) !important;
    color: var(--text-primary) !important;
    border-radius: var(--radius-md) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 14px 20px !important;
    transition: var(--transition) !important;
    text-align: center !important;
}
[data-testid="stVerticalBlock"] .stButton button:hover {
    background: var(--bg-card-hover) !important;
    border-color: var(--isu-red) !important;
    box-shadow: var(--shadow-glow-red) !important;
    transform: translateY(-2px) !important;
    color: white !important;
}

/* ─── PRIMARY BUTTONS ───────────────────────────────── */
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, var(--isu-red), var(--isu-dark-red)) !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    padding: 14px 32px !important;
    border-radius: var(--radius-md) !important;
    box-shadow: 0 4px 20px var(--isu-red-glow) !important;
    font-size: 1rem !important;
}
[data-testid="baseButton-primary"]:hover {
    box-shadow: 0 8px 30px var(--isu-red-glow) !important;
    transform: translateY(-2px) !important;
}

/* ─── CHAT MESSAGES ─────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-lg) !important;
    margin-bottom: 20px !important;
    padding: 24px !important;
    box-shadow: var(--shadow-card) !important;
    animation: fadeInUp 0.4s ease forwards;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] td,
[data-testid="stChatMessage"] th,
[data-testid="stChatMessage"] span { 
    color: var(--text-primary) !important; 
    font-size: 1rem !important; 
    line-height: 1.7 !important; 
}
[data-testid="stChatMessage"] strong { color: var(--isu-gold) !important; }
[data-testid="stChatMessage"] code { 
    background: rgba(253,230,138,0.12) !important; 
    color: var(--isu-gold) !important; 
    padding: 2px 6px !important; 
    border-radius: 4px !important; 
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    border-left: 4px solid var(--isu-gold) !important;
    background: linear-gradient(135deg, var(--bg-card) 0%, rgba(241,190,72,0.03) 100%) !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    border-left: 4px solid var(--isu-red) !important;
    background: linear-gradient(135deg, var(--bg-card) 0%, rgba(200,16,46,0.03) 100%) !important;
}

/* ─── CHAT INPUT ────────────────────────────────────── */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div,
[data-testid="stBottom"] [data-testid="stVerticalBlock"],
[data-testid="stBottom"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stBottom"] .stElementContainer {
    background: #0E0E0B !important;
    background-color: #0E0E0B !important;
}
[data-testid="stBottom"] {
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-top: 1px solid var(--border-color) !important;
    padding: 16px 40px 24px !important;
}
[data-testid="stChatInputContainer"] {
    background: #1E1E16 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
    transition: var(--transition) !important;
}
[data-testid="stChatInputContainer"]:focus-within {
    border-color: var(--isu-red) !important;
    box-shadow: 0 0 0 3px var(--isu-red-glow), 0 4px 20px rgba(0,0,0,0.3) !important;
}
[data-testid="stChatInputTextArea"] {
    background: transparent !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
}
[data-testid="stChatInputTextArea"]::placeholder { color: var(--text-muted) !important; }
/* Send button */
[data-testid="stChatInputSubmitButton"] button {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: var(--text-secondary) !important;
    border-radius: 50% !important;
}
[data-testid="stChatInputSubmitButton"] button:hover {
    background: var(--isu-red) !important;
    color: white !important;
}

/* ─── TEXT INPUTS ───────────────────────────────────── */
.stTextInput > div > div,
.stTextArea > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-md) !important;
}
.stTextInput input, .stTextArea textarea {
    background: transparent !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    padding: 14px 18px !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: var(--text-muted) !important; }
.stTextInput > div > div:focus-within,
.stTextArea > div > div:focus-within {
    border-color: var(--isu-red) !important;
    box-shadow: 0 0 0 3px var(--isu-red-glow) !important;
}
.stTextInput label, .stTextArea label {
    color: var(--text-secondary) !important; font-weight: 600 !important;
    font-size: 0.82rem !important; letter-spacing: 0.5px !important;
}

/* ─── SOURCE CARDS ──────────────────────────────────── */
.src {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-left: 4px solid var(--isu-red);
    border-radius: var(--radius-sm);
    padding: 16px 20px; margin: 10px 0;
    font-size: 0.88rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    transition: var(--transition);
}
.src:hover {
    transform: translateX(6px);
    background: var(--bg-card-hover);
    box-shadow: var(--shadow-glow-red);
}
.src a { color: var(--text-primary) !important; font-weight: 600; text-decoration: none; display: block; margin-bottom: 6px; }
.src a:hover { color: var(--isu-gold) !important; }
.src small { color: var(--text-secondary) !important; display: block; line-height: 1.5; }
.badge {
    display: inline-flex; align-items: center;
    background: rgba(253, 230, 138, 0.15); color: var(--isu-gold);
    border-radius: 20px; padding: 3px 12px; font-size: 0.72rem;
    font-weight: 700; margin-left: 10px; vertical-align: middle;
    border: 1px solid rgba(253,230,138,0.25);
}

/* ─── EXPANDERS ─────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important; 
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-md) !important; 
    overflow: hidden !important;
}
[data-testid="stExpander"] summary { 
    background: var(--bg-elevated) !important; 
    padding: 14px 20px !important;
}
[data-testid="stExpander"] summary p { 
    color: var(--isu-gold) !important; 
    font-weight: 600 !important; 
    font-size: 0.9rem !important; 
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: var(--bg-card) !important;
}

/* ─── MISC ──────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid var(--border-color) !important; margin: 24px 0 !important; }
[data-testid="stToggle"] span { color: var(--text-primary) !important; font-weight: 500 !important; }
[data-testid="stAudioInput"] { background: var(--bg-card) !important; border: 1px solid var(--border-color) !important; border-radius: var(--radius-md) !important; }
[data-testid="stSpinner"] p { color: var(--isu-gold) !important; }

/* ─── MARKDOWN HEADINGS ─────────────────────────────── */
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3 {
    color: var(--isu-gold) !important;
    border-bottom: 1px solid var(--border-color) !important;
    padding-bottom: 8px !important;
}

/* ─── SIDEBAR CHAT HISTORY ──────────────────────────── */
.chat-history-item {
    padding: 7px 20px;
    color: var(--text-secondary);
    font-size: 0.82rem;
    transition: var(--transition);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.chat-history-item:hover { color: var(--text-primary); }
.sidebar-section-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--text-primary);
    padding: 14px 20px 6px;
}
.sidebar-user {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 20px 18px;
    border-top: 1px solid rgba(255,240,200,0.1);
    background: var(--bg-sidebar);
    position: fixed;
    bottom: 0;
    width: 220px;
    box-sizing: border-box;
    z-index: 999;
}
.sidebar-user .avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FDE68A, #C99A1A);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 800; color: #4A3800;
    flex-shrink: 0;
    border: 2px solid rgba(253,230,138,0.3);
}
.sidebar-user .name { font-size: 0.85rem; color: var(--text-primary) !important; font-weight: 500; flex: 1; }
.sidebar-user .gear { color: var(--text-muted); font-size: 0.9rem; cursor: pointer; }

/* ─── DECORATIVE STAR ───────────────────────────────── */
.deco-star {
    position: fixed;
    bottom: 24px;
    right: 24px;
    font-size: 3rem;
    color: var(--isu-gold);
    opacity: 0.7;
    filter: drop-shadow(0 0 12px rgba(241,190,72,0.4));
    animation: starRotate 20s linear infinite;
    pointer-events: none;
    z-index: 999;
}

/* ─── SCROLLBAR ─────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2A2820; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #3A3828; }

::selection { background: rgba(200,16,46,0.3); color: white; }
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
for k, v in {"messages": [], "history": [], "pending_q": None, "chat_titles": []}.items():
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

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # ── Logo flush to top ─────────────────────────────────────────────────────
    st.markdown('<style>[data-testid="stSidebar"] section:first-child{padding-top:0!important}</style>', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
    else:
        st.markdown(
            '<div style="text-align:center;padding:20px 16px 8px;background:#C8102E;">'
            '<span style="font-size:1.8rem;font-weight:900;color:#FDE68A;">🌪️</span>'
            '<br><span style="font-size:1rem;font-weight:900;color:white;letter-spacing:1px;">CyGPT</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:1px;background:rgba(255,240,200,0.08);margin:0 0 4px;"></div>', unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────────────────
    page = st.radio(
        "Navigation",
        ["💬  Chat", "🎓  Degree Planner", "⚠️  Conflict Checker", "⚖️  Compare Majors"],
        label_visibility="collapsed",
    )

    st.markdown('<div style="height:1px;background:rgba(255,240,200,0.08);margin:8px 0;"></div>', unsafe_allow_html=True)

    # ── New Chat button ───────────────────────────────────────────────────────
    if st.button("＋  New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history  = []
        st.rerun()

    # ── Chat history ──────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-label">Recent chats</div>', unsafe_allow_html=True)

    user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    if user_msgs:
        for msg in reversed(user_msgs[-5:]):
            truncated = msg[:36] + "…" if len(msg) > 36 else msg
            st.markdown(f'<div class="chat-history-item">💬 {truncated}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="chat-history-item" style="color:#4A4038;font-style:italic;">No chats yet</div>',
            unsafe_allow_html=True,
        )

    # ── User profile — pinned at bottom ──────────────────────────────────────
    st.markdown("""
    <div class="sidebar-user">
      <span class="name">👤 User</span>
    </div>
    """, unsafe_allow_html=True)

# Handle "New Chat" navigation
# (New Chat handled via button in sidebar)

# ══════════════════════════════════════════════════════════════════════════════
#  CHAT PAGE
# ══════════════════════════════════════════════════════════════════════════════
if page == "💬  Chat":
    # Indexed badge (top right)
    st.markdown(
        f'<div class="index-badge">{len(chunks):,} chunks indexed</div>',
        unsafe_allow_html=True,
    )

    # Hero banner
    st.markdown(f"""
    <div class="hero">
      <h1>🌪️ CyGPT</h1>
      <p>Iowa State University Academic Assistant &nbsp;-&nbsp;
      Searching <span class="gold">{len(chunks):,} indexed chunks</span>
      from the ISU catalog, PDFs, and course pages.</p>
    </div>""", unsafe_allow_html=True)

    # Settings row
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

    # Starter prompts
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

    # Chat history display
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

    # Decorative gold star (bottom right)
    st.markdown('<div class="deco-star">✦</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  DEGREE PLANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎓  Degree Planner":
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

# ══════════════════════════════════════════════════════════════════════════════
#  CONFLICT CHECKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚠️  Conflict Checker":
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

# ══════════════════════════════════════════════════════════════════════════════
#  COMPARE MAJORS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚖️  Compare Majors":
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


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT INPUT — always visible at bottom for chat page
# ══════════════════════════════════════════════════════════════════════════════
if page == "💬  Chat":
    question = st.session_state.pop("pending_q", None) or \
               st.chat_input("Ask about courses, majors, requirements, prerequisites…")

    if question:
        # Save to chat titles for sidebar history
        if question not in [t for t in st.session_state.get("chat_titles", [])]:
            st.session_state.setdefault("chat_titles", []).append(question[:50])

        st.session_state.messages.append({"role": "user", "content": question})
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