from __future__ import annotations
from pathlib import Path
import streamlit as st

from src.history import (
    delete_conversation,
    history_from_messages,
    list_conversations,
    load_conversation,
)

LOGO_PATH = Path(__file__).parent.parent / "static" / "logo.png"

_PAGES = ["💬  Chat", "🎓  Degree Planner", "⚠️  Conflict Checker", "⚖️  Compare Majors"]


def _render_recent_chats() -> None:
    """List the signed-in user's saved conversations; load or delete on click."""
    user_id = st.session_state.get("user_id")
    if user_id is None:
        return

    try:
        convos = list_conversations(user_id)
    except Exception as e:  # noqa: BLE001 — degrade gracefully if DB is down
        st.markdown(
            f'<div class="chat-history-item" style="color:#C8102E;">⚠️ {e}</div>',
            unsafe_allow_html=True,
        )
        return

    if not convos:
        st.markdown(
            '<div class="chat-history-item" style="color:#4A4038;font-style:italic;">No chats yet</div>',
            unsafe_allow_html=True,
        )
        return

    active = st.session_state.get("conversation_id")
    for c in convos[:15]:
        cid   = c["id"]
        title = c.get("title") or "New chat"
        title = (title[:30] + "…") if len(title) > 30 else title
        label = ("🟢 " if cid == active else "💬 ") + title

        col_open, col_del = st.columns([5, 1])
        if col_open.button(label, key=f"open_{cid}", width="stretch"):
            msgs = load_conversation(cid)
            st.session_state.messages        = msgs
            st.session_state.history         = history_from_messages(msgs)
            st.session_state.conversation_id = cid
            st.rerun()
        if col_del.button("🗑", key=f"del_{cid}"):
            delete_conversation(cid)
            if cid == active:
                st.session_state.messages        = []
                st.session_state.history         = []
                st.session_state.conversation_id = None
            st.rerun()


def render() -> str:
    with st.sidebar:
        st.markdown(
            '<style>[data-testid="stSidebar"] section:first-child{padding-top:0!important}</style>',
            unsafe_allow_html=True,
        )

        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width="stretch")
        else:
            st.markdown(
                '<div style="text-align:center;padding:20px 16px 8px;background:#C8102E;">'
                '<span style="font-size:1.8rem;font-weight:900;color:#FDE68A;">🌪️</span>'
                '<br><span style="font-size:1rem;font-weight:900;color:white;letter-spacing:1px;">CyGPT</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div style="height:1px;background:rgba(255,240,200,0.08);margin:0 0 4px;"></div>', unsafe_allow_html=True)

        page = st.radio("Navigation", _PAGES, label_visibility="collapsed")

        st.markdown('<div style="height:1px;background:rgba(255,240,200,0.08);margin:8px 0;"></div>', unsafe_allow_html=True)

        if st.button("＋  New Chat", width="stretch"):
            st.session_state.messages = []
            st.session_state.history  = []
            st.session_state.conversation_id = None
            st.rerun()

        st.markdown('<div class="sidebar-section-label">Recent chats</div>', unsafe_allow_html=True)
        _render_recent_chats()

        display  = st.session_state.get("display_name", "User")
        initials = "".join(w[0].upper() for w in display.split()[:2])
        st.markdown(f"""
        <div class="sidebar-user">
          <div class="avatar">{initials}</div>
          <span class="name">{display}</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out", key="_logout_btn"):
            for k in ["logged_in", "username", "display_name", "user_id",
                      "messages", "history", "pending_q", "conversation_id",
                      "chat_titles", "_login_err", "_signup_err", "_signup_ok"]:
                st.session_state.pop(k, None)
            st.rerun()

    return page
