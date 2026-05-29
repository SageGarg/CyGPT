from __future__ import annotations
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ─── VARIABLES ─────────────────────────────────────── */
:root {
    --isu-red:       #C8102E;
    --isu-red-glow:  rgba(200, 16, 46, 0.35);
    --isu-dark-red:  #9B0020;
    --isu-gold:      #FDE68A;
    --isu-gold-mid:  #F1BE48;
    --isu-gold-dark: #C99A1A;
    --isu-gold-glow: rgba(253, 230, 138, 0.25);
    --bg-dark:       #12120F;
    --bg-card:       #1C1C17;
    --bg-card-hover: #242419;
    --bg-elevated:   #2A2A22;
    --bg-sidebar:    #0E0E0B;
    --text-primary:  #F5F0E8;
    --text-secondary:#A89F8C;
    --text-muted:    #6B6355;
    --border-color:  rgba(255,240,200,0.07);
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
[data-testid="stDecoration"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarNav"] + div {
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
[data-testid="stSidebar"] .sidebar-user-wrap { margin-top: auto !important; }

[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    color: var(--text-secondary) !important;
    background: transparent !important;
}

/* ─── SIDEBAR RADIO ─────────────────────────────────── */
[data-testid="stSidebar"] .stRadio > div { gap: 0 !important; }
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
[data-testid="stSidebar"] .stRadio > div > label > div:first-child { display: none !important; }
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
[data-testid="stSidebar"] .stRadio > label { display: none !important; }

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

/* ─── SIDEBAR MISC ─────────────────────────────────── */
[data-testid="stSidebar"] hr {
    border: none !important;
    border-top: 1px solid var(--border-color) !important;
    margin: 12px 16px !important;
}
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
.hero h1 { margin: 0 0 10px 0; font-size: 1.8rem; font-weight: 900; color: white !important; display: flex; align-items: center; gap: 12px; }
.hero p  { margin: 0; font-size: 0.95rem; line-height: 1.6; color: rgba(255,255,255,0.85) !important; max-width: 700px; }
.hero .gold { color: var(--isu-gold) !important; font-weight: 700; }

/* ─── BADGES / LABELS ───────────────────────────────── */
.index-badge { text-align: right; margin-bottom: 8px; font-size: 0.8rem; color: var(--text-muted); font-weight: 500; }
.sec-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 2.5px; color: var(--text-muted); margin: 24px 0 14px; padding-left: 4px; }

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
    color: white !important; border: none !important; font-weight: 700 !important;
    padding: 14px 32px !important; border-radius: var(--radius-md) !important;
    box-shadow: 0 4px 20px var(--isu-red-glow) !important; font-size: 1rem !important;
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
[data-testid="stChatMessage"] span { color: var(--text-primary) !important; font-size: 1rem !important; line-height: 1.7 !important; }
[data-testid="stChatMessage"] strong { color: var(--isu-gold) !important; }
[data-testid="stChatMessage"] code { background: rgba(253,230,138,0.12) !important; color: var(--isu-gold) !important; padding: 2px 6px !important; border-radius: 4px !important; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    border-left: 4px solid var(--isu-gold) !important;
    background: linear-gradient(135deg, var(--bg-card) 0%, rgba(241,190,72,0.03) 100%) !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    border-left: 4px solid var(--isu-red) !important;
    background: linear-gradient(135deg, var(--bg-card) 0%, rgba(200,16,46,0.03) 100%) !important;
}
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3 { color: var(--isu-gold) !important; border-bottom: 1px solid var(--border-color) !important; padding-bottom: 8px !important; }

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
[data-testid="stChatInputTextArea"] { background: transparent !important; color: var(--text-primary) !important; font-family: 'Inter', sans-serif !important; font-size: 0.95rem !important; }
[data-testid="stChatInputTextArea"]::placeholder { color: var(--text-muted) !important; }
[data-testid="stChatInputSubmitButton"] button { background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.15) !important; color: var(--text-secondary) !important; border-radius: 50% !important; }
[data-testid="stChatInputSubmitButton"] button:hover { background: var(--isu-red) !important; color: white !important; }

/* ─── TEXT INPUTS ───────────────────────────────────── */
.stTextInput > div > div,
.stTextArea > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-md) !important;
}
.stTextInput input, .stTextArea textarea { background: transparent !important; color: var(--text-primary) !important; font-family: 'Inter', sans-serif !important; padding: 14px 18px !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: var(--text-muted) !important; }
.stTextInput > div > div:focus-within,
.stTextArea > div > div:focus-within { border-color: var(--isu-red) !important; box-shadow: 0 0 0 3px var(--isu-red-glow) !important; }
.stTextInput label, .stTextArea label { color: var(--text-secondary) !important; font-weight: 600 !important; font-size: 0.82rem !important; letter-spacing: 0.5px !important; }

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
.src:hover { transform: translateX(6px); background: var(--bg-card-hover); box-shadow: var(--shadow-glow-red); }
.src a { color: var(--text-primary) !important; font-weight: 600; text-decoration: none; display: block; margin-bottom: 6px; }
.src a:hover { color: var(--isu-gold) !important; }
.src small { color: var(--text-secondary) !important; display: block; line-height: 1.5; }
.badge { display: inline-flex; align-items: center; background: rgba(253,230,138,0.15); color: var(--isu-gold); border-radius: 20px; padding: 3px 12px; font-size: 0.72rem; font-weight: 700; margin-left: 10px; vertical-align: middle; border: 1px solid rgba(253,230,138,0.25); }

/* ─── EXPANDERS ─────────────────────────────────────── */
[data-testid="stExpander"] { background: var(--bg-card) !important; border: 1px solid var(--border-color) !important; border-radius: var(--radius-md) !important; overflow: hidden !important; }
[data-testid="stExpander"] summary { background: var(--bg-elevated) !important; padding: 14px 20px !important; }
[data-testid="stExpander"] summary p { color: var(--isu-gold) !important; font-weight: 600 !important; font-size: 0.9rem !important; }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] { background: var(--bg-card) !important; }

/* ─── SIDEBAR USER / HISTORY ────────────────────────── */
.chat-history-item { padding: 7px 20px; color: var(--text-secondary); font-size: 0.82rem; transition: var(--transition); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-history-item:hover { color: var(--text-primary); }
.sidebar-section-label { font-size: 0.72rem; font-weight: 700; color: var(--text-primary); padding: 14px 20px 6px; }
.sidebar-user { display: flex; align-items: center; gap: 10px; padding: 14px 20px 18px; border-top: 1px solid rgba(255,240,200,0.1); background: var(--bg-sidebar); position: fixed; bottom: 0; width: 220px; box-sizing: border-box; z-index: 999; }
.sidebar-user .avatar { width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #FDE68A, #C99A1A); display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 800; color: #4A3800; flex-shrink: 0; border: 2px solid rgba(253,230,138,0.3); }
.sidebar-user .name { font-size: 0.85rem; color: var(--text-primary) !important; font-weight: 500; flex: 1; }

/* ─── AUTH PAGE ─────────────────────────────────────── */
.auth-wrap { max-width: 440px; margin: 7vh auto 0; background: #1C1C17; border: 1px solid rgba(200,16,46,0.3); border-radius: 20px; padding: 44px 40px 36px; box-shadow: 0 8px 48px rgba(200,16,46,0.15); }
.auth-logo  { text-align:center; font-size:2.6rem; margin-bottom:4px; }
.auth-title { text-align:center; font-size:1.5rem; font-weight:900; color:#F5F0E8; margin-bottom:2px; }
.auth-sub   { text-align:center; font-size:0.82rem; color:#A89F8C; margin-bottom:30px; }
.auth-msg-error { background: rgba(200,16,46,0.15); border:1px solid rgba(200,16,46,0.4); border-radius:10px; padding:10px 16px; color:#FF8080; font-size:0.85rem; margin-bottom:14px; text-align:center; }
.auth-msg-ok    { background: rgba(34,197,94,0.12); border:1px solid rgba(34,197,94,0.35); border-radius:10px; padding:10px 16px; color:#6EE7B7; font-size:0.85rem; margin-bottom:14px; text-align:center; }
.auth-hint { font-size:0.78rem; color:#6B6355; margin-top:6px; padding-left:2px; }

/* ─── MISC ──────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid var(--border-color) !important; margin: 24px 0 !important; }
[data-testid="stToggle"] span { color: var(--text-primary) !important; font-weight: 500 !important; }
[data-testid="stAudioInput"] { background: var(--bg-card) !important; border: 1px solid var(--border-color) !important; border-radius: var(--radius-md) !important; }
[data-testid="stSpinner"] p { color: var(--isu-gold) !important; }
.deco-star { position: fixed; bottom: 24px; right: 24px; font-size: 3rem; color: var(--isu-gold); opacity: 0.7; filter: drop-shadow(0 0 12px rgba(241,190,72,0.4)); animation: starRotate 20s linear infinite; pointer-events: none; z-index: 999; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2A2820; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #3A3828; }
::selection { background: rgba(200,16,46,0.3); color: white; }
</style>
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
