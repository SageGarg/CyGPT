from __future__ import annotations
import streamlit as st
from src.retriever import retrieve
from src.features import stream_degree_plan
from ui.components import render_sources


def render(chunks, faiss_index, bm25) -> None:
    if "planner_degree_type" not in st.session_state:
        st.session_state.planner_degree_type = None

    degree_type = st.session_state.planner_degree_type

    if degree_type is None:
        st.markdown("""
        <div class="hero">
          <h1>🎓 Degree Planner</h1>
          <p>Select a degree level to build your customized semester-by-semester plan pulled directly from the official ISU catalog.</p>
        </div>""", unsafe_allow_html=True)

        st.write("### What type of degree plan would you like to build?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎓  Undergraduate Plan\n(4-Year Schedule)", key="btn_undergrad", use_container_width=True):
                st.session_state.planner_degree_type = "Undergrad"
                st.rerun()
            if st.button("🔬  PhD Plan\n(Milestones & Research)", key="btn_phd", use_container_width=True):
                st.session_state.planner_degree_type = "PhD"
                st.rerun()
        with col2:
            if st.button("🎓  Graduate / Master's Plan\n(2-Year Schedule)", key="btn_masters", use_container_width=True):
                st.session_state.planner_degree_type = "Masters"
                st.rerun()
            if st.button("📜  Certificate Plan\n(Concentrated Curriculum)", key="btn_cert", use_container_width=True):
                st.session_state.planner_degree_type = "Certificate"
                st.rerun()
    else:
        # Determine labels, titles, and placeholders based on selected degree type
        if degree_type == "Undergrad":
            title = "🎓 Undergraduate Degree Planner"
            desc = "Get a detailed 4-year semester-by-semester sequence for any ISU undergraduate major."
            label = "Major Name"
            placeholder = "e.g. Computer Science, B.S."
            query_suffix = "four year plan undergraduate degree course sequence credits requirements"
        elif degree_type == "Masters":
            title = "🎓 Master's Degree Planner"
            desc = "Get a detailed 2-year semester-by-semester graduate curriculum for any ISU Master's program."
            label = "Graduate Program"
            placeholder = "e.g. Computer Science, M.S."
            query_suffix = "graduate master's degree plan curriculum requirements course sequence"
        elif degree_type == "PhD":
            title = "🔬 PhD Planner"
            desc = "Generate doctoral milestones, seminar courses, research requirements, and defense timelines."
            label = "Doctoral Program"
            placeholder = "e.g. Computer Science, Ph.D."
            query_suffix = "doctoral phd degree requirements program of study milestones curriculum"
        else: # Certificate
            title = "📜 Certificate Planner"
            desc = "Get coursework requirements and curriculum guidelines for any ISU certificate program."
            label = "Certificate Program"
            placeholder = "e.g. Applied Artificial Intelligence Certificate"
            query_suffix = "certificate requirements courses curriculum credits"

        st.markdown(f"""
        <div class="hero">
          <h1>{title}</h1>
          <p>{desc}</p>
        </div>""", unsafe_allow_html=True)

        col_input, col_action = st.columns([4, 1.2])
        with col_input:
            major_input = st.text_input(label, placeholder=placeholder, key="planner_major")
        with col_action:
            st.write("")
            st.write("")
            c_go, c_back = st.columns(2)
            with c_go:
                go = st.button("Generate", type="primary", use_container_width=True, key="planner_go")
            with c_back:
                if st.button("Back", use_container_width=True, key="planner_back"):
                    st.session_state.planner_degree_type = None
                    st.rerun()

        if go and major_input.strip():
            with st.spinner(f"Finding {major_input} requirements…"):
                hits = retrieve(
                    f"{major_input} {query_suffix}",
                    faiss_index, bm25, chunks, expand=True)
            st.divider()
            with st.chat_message("assistant"):
                ph, result = st.empty(), ""
                for tok in stream_degree_plan(major_input.strip(), degree_type, hits):
                    result += tok; ph.markdown(result + "▌")
                ph.markdown(result)
                if hits:
                    with st.expander(f"📚 {len(hits)} sources used"):
                        render_sources(hits)
        elif go:
            st.warning(f"Please enter a {label.lower()}.")
