import streamlit as st
from documind.core import DocumentAssistant, ollama_status

st.set_page_config(page_title="DocuMind AI", page_icon="📚", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.hero {padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(115deg,#172554,#4338ca); color:white; margin-bottom:1rem;}
.hero h1 {color:white; margin:0;} .hero p {color:#e0e7ff; margin:.4rem 0 0;}
.small-muted {color:#64748b;font-size:.9rem}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>📚 DocuMind AI</h1><p>Read less. Understand more. Learn smarter — chat with your PDFs.</p></div>', unsafe_allow_html=True)

if "assistant" not in st.session_state:
    st.session_state.assistant = DocumentAssistant()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "docs_loaded" not in st.session_state:
    st.session_state.docs_loaded = False

assistant = st.session_state.assistant
with st.sidebar:
    st.header("⚙️ Settings")
    model = st.text_input("Ollama model", value="llama3.2", help="Install a model locally with: ollama pull llama3.2")
    top_k = st.slider("Retrieved passages", 2, 8, 4)
    st.divider()
    online, detail = ollama_status()
    st.write("**Generation engine**")
    st.success(detail) if online else st.warning(detail)
    st.caption("If Ollama is unavailable, DocuMind uses a built-in extractive fallback for answers, summaries and flashcards.")
    if st.button("Clear current session", use_container_width=True):
        st.session_state.assistant = DocumentAssistant()
        st.session_state.messages = []
        st.session_state.docs_loaded = False
        st.rerun()

tab_chat, tab_summary, tab_cards, tab_library = st.tabs(["💬 Ask your PDFs", "📝 Executive summary", "🗂️ Flashcards", "📂 Document library"])

with tab_library:
    st.subheader("Upload PDF documents")
    uploads = st.file_uploader("Choose one or more PDF files", type=["pdf"], accept_multiple_files=True)
    if st.button("Process documents", type="primary", disabled=not uploads):
        with st.spinner("Extracting text and building the searchable index..."):
            try:
                results = assistant.add_pdfs(uploads)
                st.session_state.docs_loaded = True
                st.session_state.messages = []
                for r in results:
                    if r["pages"] == 0:
                        st.warning(f'{r["name"]}: no extractable text found. It may be a scanned PDF; OCR is not enabled in this starter build.')
                    else:
                        st.success(f'{r["name"]}: processed {r["pages"]} pages into {r["chunks"]} searchable passages.')
            except Exception as e:
                st.error(f"Could not process PDF: {e}")
    stats = assistant.stats()
    c1,c2,c3 = st.columns(3)
    c1.metric("Documents", stats["documents"])
    c2.metric("Pages", stats["pages"])
    c3.metric("Passages", stats["chunks"])
    if stats["files"]:
        st.write("**Currently indexed**")
        for name in stats["files"]:
            st.write("📄", name)

with tab_chat:
    st.subheader("Ask questions in plain English")
    if not assistant.has_documents():
        st.info("Upload and process one or more PDFs in the Document library tab to get started.")
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander("View source passages"):
                        for s in msg["sources"]:
                            st.caption(f'{s["file"]} · page {s["page"]} · relevance {s["score"]:.3f}')
                            st.write(s["text"])
        prompt = st.chat_input("Ask something about your uploaded documents...")
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Searching documents and preparing an answer..."):
                    result = assistant.answer(prompt, model=model, top_k=top_k)
                st.markdown(result["answer"])
                if result["sources"]:
                    with st.expander("View source passages", expanded=False):
                        for s in result["sources"]:
                            st.caption(f'{s["file"]} · page {s["page"]} · relevance {s["score"]:.3f}')
                            st.write(s["text"])
            st.session_state.messages.append({"role":"assistant","content":result["answer"],"sources":result["sources"]})

with tab_summary:
    st.subheader("Executive summary")
    if not assistant.has_documents():
        st.info("Process a PDF first.")
    else:
        choices = ["All documents"] + assistant.document_names()
        selected = st.selectbox("Summarize", choices)
        length = st.select_slider("Summary length", options=["Brief","Standard","Detailed"], value="Standard")
        if st.button("Generate summary", type="primary"):
            with st.spinner("Preparing summary..."):
                summary = assistant.summarize(None if selected == "All documents" else selected, length, model)
            st.markdown(summary)
            st.download_button("Download summary (.txt)", summary, file_name="documind_summary.txt", mime="text/plain")

with tab_cards:
    st.subheader("Study flashcards")
    if not assistant.has_documents():
        st.info("Process a PDF first.")
    else:
        choices = ["All documents"] + assistant.document_names()
        selected = st.selectbox("Generate cards from", choices, key="cards_doc")
        count = st.slider("Number of flashcards", 3, 15, 8)
        if st.button("Generate flashcards", type="primary"):
            with st.spinner("Creating flashcards..."):
                cards = assistant.flashcards(None if selected == "All documents" else selected, count, model)
            st.session_state.flashcards = cards
        for i, card in enumerate(st.session_state.get("flashcards", []), 1):
            with st.expander(f"Card {i}: {card['question']}"):
                st.write(card["answer"])
        if st.session_state.get("flashcards"):
            payload = "\n\n".join(f"Q: {c['question']}\nA: {c['answer']}" for c in st.session_state.flashcards)
            st.download_button("Download flashcards (.txt)", payload, file_name="documind_flashcards.txt", mime="text/plain")

st.markdown("---")
st.markdown('<p class="small-muted">DocuMind AI · RAG-powered PDF assistant · Answers are grounded in retrieved document passages; verify important information against the source.</p>', unsafe_allow_html=True)
