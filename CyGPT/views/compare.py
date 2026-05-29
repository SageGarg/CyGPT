from __future__ import annotations
import streamlit as st
from src.retriever import retrieve_for_comparison
from src.features import stream_comparison
from ui.components import render_sources


def render(chunks, faiss_index, bm25) -> None:
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
                hits = retrieve_for_comparison(
                    major_a.strip(), major_b.strip(), faiss_index, bm25, chunks)
            st.divider()
            with st.chat_message("assistant"):
                ph, result = st.empty(), ""
                for tok in stream_comparison(major_a.strip(), major_b.strip(), hits):
                    result += tok; ph.markdown(result + "▌")
                ph.markdown(result)
                if hits:
                    with st.expander(f"📚 {len(hits)} sources used"):
                        render_sources(hits)
