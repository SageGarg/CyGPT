from __future__ import annotations
from pathlib import Path
import streamlit as st

LOGO_PATH = Path(__file__).parent.parent / "static" / "logo.png"

_PAGES = ["💬  Chat", "🎓  Degree Planner", "⚠️  Conflict Checker", "⚖️  Compare Majors"]


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
            st.rerun()

        st.markdown('<div class="sidebar-section-label">Recent chats</div>', unsafe_allow_html=True)
        user_msgs = [m["content"] for m in st.session_state.get("messages", []) if m["role"] == "user"]
        if user_msgs:
            for msg in reversed(user_msgs[-5:]):
                truncated = msg[:36] + "…" if len(msg) > 36 else msg
                st.markdown(f'<div class="chat-history-item">💬 {truncated}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="chat-history-item" style="color:#4A4038;font-style:italic;">No chats yet</div>',
                unsafe_allow_html=True,
            )

        display  = st.session_state.get("display_name", "User")
        initials = "".join(w[0].upper() for w in display.split()[:2])
        st.markdown(f"""
        <div class="sidebar-user">
          <div class="avatar">{initials}</div>
          <span class="name">{display}</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out", key="_logout_btn"):
            for k in ["logged_in", "username", "display_name", "messages", "history",
                      "pending_q", "chat_titles", "_login_err", "_signup_err", "_signup_ok"]:
                st.session_state.pop(k, None)
            st.rerun()

    return page
