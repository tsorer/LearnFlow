import os

import streamlit as st
from dotenv import load_dotenv

import rag

load_dotenv()
rag.configure()

st.set_page_config(page_title="LearnFlow POC", page_icon="📚", layout="wide")
st.title("📚 LearnFlow POC")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Korpus")

    count = rag.doc_count()
    st.metric("Chunks im Index", count)

    files = st.file_uploader(
        "Dokumente hochladen (PDF · DOCX · MD)",
        type=["pdf", "docx", "md"],
        accept_multiple_files=True,
    )
    if files and st.button("Einlesen", type="primary"):
        with st.spinner("Dokumente werden verarbeitet…"):
            n = rag.ingest(files)
        st.success(f"{n} Chunks eingelesen.")
        st.rerun()

    st.divider()

    threshold = st.slider(
        "Konfidenz-Schwellenwert",
        min_value=0.3, max_value=0.95, value=0.6, step=0.05,
        help="Unter diesem Wert: 'Eingeschränkt belegt'. Unter 70 % davon: Antwort unterdrückt.",
    )

    if st.button("Chat zurücksetzen"):
        st.session_state.messages = []
        st.rerun()

# ── Chat history ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"📄 Quellen ({len(msg['sources'])})"):
                for s in msg["sources"]:
                    st.markdown(f"**{s['filename']}** · Seite {s['page']} · Score `{s['score']}`")
                    st.caption(s["excerpt"])
        if msg.get("confidence") is not None:
            st.caption(f"Konfidenz: `{msg['confidence']:.2f}`")

# ── Input ─────────────────────────────────────────────────────────────────────
question = st.chat_input(
    "Frage stellen…",
    disabled=(count == 0),
)

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Suche im Korpus…"):
            resp = rag.ask(question, threshold)

        if resp.is_partial:
            st.warning("⚠️ Eingeschränkt belegt — Konfidenz unter Schwellenwert")

        st.markdown(resp.answer)
        st.caption(f"Konfidenz: `{resp.confidence:.2f}`")

        if resp.sources:
            with st.expander(f"📄 Quellen ({len(resp.sources)})"):
                for s in resp.sources:
                    st.markdown(f"**{s.filename}** · Seite {s.page} · Score `{s.score}`")
                    st.caption(s.excerpt)

    st.session_state.messages.append({
        "role": "assistant",
        "content": resp.answer,
        "confidence": resp.confidence,
        "sources": [
            {"filename": s.filename, "page": s.page, "score": s.score, "excerpt": s.excerpt}
            for s in resp.sources
        ],
    })
