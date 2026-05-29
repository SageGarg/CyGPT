from __future__ import annotations
import streamlit as st
from src.retriever import retrieve
from src.features import stream_conflict_check
from ui.components import render_sources


def render(chunks, faiss_index, bm25) -> None:
    st.markdown("""
    <div class="hero">
      <h1>⚠️ Pre Req Checker</h1>
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
