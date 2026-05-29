from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.indexer import load_index
from ui.styles import inject_styles
from ui.auth_page import show as show_auth
from ui.sidebar import render as render_sidebar
import views.chat as chat_page
import views.planner as planner_page
import views.prereq as prereq_page
import views.compare as compare_page

st.set_page_config(
    page_title="CyGPT | ISU Academic Assistant",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()

if not st.session_state.get("logged_in"):
    show_auth()

@st.cache_resource(show_spinner="📚 Loading index…")
def _load():
    return load_index()

try:
    faiss_index, bm25, chunks = _load()
except FileNotFoundError:
    st.error("No index found. Run `python ingest.py` first.")
    st.stop()

for k, v in {"messages": [], "history": [], "pending_q": None, "conversation_id": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

page = render_sidebar()

{
    "💬  Chat":           chat_page,
    "🎓  Degree Planner": planner_page,
    "⚠️  Pre Req Checker": prereq_page,
    "⚖️  Compare Majors":  compare_page,
}[page].render(chunks, faiss_index, bm25)
