from __future__ import annotations
import streamlit as st
from src.retriever import retrieve
from src.answerer import stream_answer
from src.features import transcribe_audio, parse_followups
from src.history import save_conversation
from ui.components import render_sources


def render(chunks, faiss_index, bm25) -> None:
    st.markdown(
        f'<div class="index-badge">{len(chunks):,} chunks indexed</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <div class="hero">
      <h1>🌪️ CyGPT</h1>
      <p>Iowa State University Academic Assistant &nbsp;-&nbsp;
      Searching <span class="gold">{len(chunks):,} indexed chunks</span>
      from the ISU catalog, PDFs, and course pages.</p>
    </div>""", unsafe_allow_html=True)

    with st.expander("⚙️  Settings & Tools", expanded=False):
        s1, s2, s3 = st.columns([2, 3, 2])
        with s1:
            st.toggle("🔍 Query expansion", value=True,
                help="Rewrites your question 3 ways for better recall")
        with s2:
            audio_data = st.audio_input("🎤 Speak your question", label_visibility="visible")
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
            if st.button("🗑️ Clear conversation", width="stretch"):
                # Start a fresh, unsaved chat — leaves any saved history intact.
                st.session_state.messages = []
                st.session_state.history  = []
                st.session_state.conversation_id = None
                st.rerun()

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
        for col, p in zip([c1, c2, c3, c1, c2, c3], starters):
            with col:
                if st.button(p, key=f"s_{p[:18]}", width="stretch"):
                    st.session_state.pending_q = p
                    st.rerun()
        st.write("")

    for msg_idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                if msg.get("followups"):
                    fc = st.columns(len(msg["followups"]))
                    for fq_idx, (col, fq) in enumerate(zip(fc, msg["followups"])):
                        if col.button(fq, key=f"fq_{msg_idx}_{fq_idx}", width="stretch"):
                            st.session_state.pending_q = fq
                            st.rerun()
                if msg.get("sources"):
                    with st.expander(f"📚 {len(msg['sources'])} sources used"):
                        render_sources(msg["sources"])

    st.markdown('<div class="deco-star">✦</div>', unsafe_allow_html=True)

    question = st.session_state.pop("pending_q", None) or \
               st.chat_input("Ask about courses, majors, requirements, prerequisites…")

    if question:
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
                for fq_idx, (col, fq) in enumerate(zip(fc, followups)):
                    if col.button(fq, key=f"fqn_{fq_idx}_{len(st.session_state.messages)}", width="stretch"):
                        st.session_state.pending_q = fq
                        st.rerun()
            if hits:
                with st.expander(f"📚 {len(hits)} sources used"):
                    render_sources(hits)

        st.session_state.history += [
            {"role": "user",      "content": question},
            {"role": "assistant", "content": full},
        ]
        st.session_state.messages.append({
            "role": "assistant", "content": main_text,
            "followups": followups, "sources": hits,
        })

        # Persist this conversation to Supabase under the signed-in account.
        if st.session_state.get("username"):
            try:
                st.session_state.conversation_id = save_conversation(
                    st.session_state["username"],
                    st.session_state.get("conversation_id"),
                    st.session_state.messages,
                )
            except Exception as e:  # noqa: BLE001 — never let a save break chat
                st.toast(f"Couldn't save chat history: {e}", icon="⚠️")

        st.rerun()
