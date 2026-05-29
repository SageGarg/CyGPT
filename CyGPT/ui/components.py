from __future__ import annotations
import streamlit as st
from src.indexer import Chunk


def render_sources(sources: list[Chunk]) -> None:
    for i, c in enumerate(sources, 1):
        st.markdown(
            f'<div class="src"><strong>Source {i}</strong>'
            f'<span class="badge">score {c.score:.1f}</span><br>'
            f'<a href="{c.url}" target="_blank">{c.url}</a>'
            f'<small>{c.text[:240]}…</small></div>',
            unsafe_allow_html=True,
        )
