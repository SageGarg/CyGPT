from __future__ import annotations
import streamlit as st
from src.retriever import retrieve
from src.features import stream_degree_plan
from ui.components import render_sources


def render(chunks, faiss_index, bm25) -> None:
    st.markdown("""
    <div class="hero">
      <h1>🎓 Degree Planner</h1>
      <p>Enter any ISU major and get a full 4-year semester-by-semester plan
      pulled directly from the catalog.</p>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([5, 1])
    with c1:
        major_input = st.text_input("Major name",
            placeholder="e.g. Computer Science, B.S.", key="planner_major")
    with c2:
        st.write("")
        st.write("")
        go = st.button("Generate", type="primary", width="stretch", key="planner_go")

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
