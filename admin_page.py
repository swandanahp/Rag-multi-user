import streamlit as st
from typing import List
from phi.assistant import Assistant
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.utils.log import logger

from assistant import get_auto_rag_assistant  # type: ignore


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["auto_rag_assistant"] = None
    st.session_state["auto_rag_assistant_run_id"] = None
    if "url_scrape_key" in st.session_state:
        st.session_state["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state:
        st.session_state["file_uploader_key"] += 1
    st.rerun()


def show_admin_page():
    st.header("Prawata Ai Admin")
    st.subheader("Manage Documents dan Test AI Model")
    llm_model = st.sidebar.selectbox(
        "Pilih model", options=["gpt-4-turbo", "gpt-3.5-turbo"]
    )
    if "llm_model" not in st.session_state:
        st.session_state["llm_model"] = llm_model
    elif st.session_state["llm_model"] != llm_model:
        st.session_state["llm_model"] = llm_model
        restart_assistant()

    auto_rag_assistant: Assistant
    if (
        "auto_rag_assistant" not in st.session_state
        or st.session_state["auto_rag_assistant"] is None
    ):
        logger.info(f"---*--- Creating {llm_model} Assistant ---*---")
        auto_rag_assistant = get_auto_rag_assistant(llm_model=llm_model)
        st.session_state["auto_rag_assistant"] = auto_rag_assistant
    else:
        auto_rag_assistant = st.session_state["auto_rag_assistant"]

    try:
        st.session_state["auto_rag_assistant_run_id"] = (
            auto_rag_assistant.create_run()
        )
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    # Load knowledge base
    if auto_rag_assistant.knowledge_base:
        if "url_scrape_key" not in st.session_state:
            st.session_state["url_scrape_key"] = 0

        input_url = st.sidebar.text_input(
            "Tambah URL ke Knowledge Base",
            type="default",
            key=st.session_state["url_scrape_key"],
        )
        add_url_button = st.sidebar.button("Tambah URL")
        if add_url_button:
            if input_url is not None:
                alert = st.sidebar.info("Memroses URLs...", icon="ℹ️")
                if f"{input_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader(max_links=2, max_depth=1)
                    web_documents: List[Document] = scraper.read(input_url)
                    if web_documents:
                        auto_rag_assistant.knowledge_base.load_documents(
                            web_documents, upsert=True
                        )
                    else:
                        st.sidebar.error("Tidak dapat membaca website")
                    st.session_state[f"{input_url}_uploaded"] = True
                alert.empty()

        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 100

        uploaded_file = st.sidebar.file_uploader(
            "Tambah a PDF :page_facing_up:",
            type="pdf",
            key=st.session_state["file_uploader_key"],
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Memroses PDF...", icon="🧠")
            auto_rag_name = uploaded_file.name.split(".")[0]
            if f"{auto_rag_name}_uploaded" not in st.session_state:
                reader = PDFReader()
                auto_rag_documents: List[Document] = reader.read(uploaded_file)
                if auto_rag_documents:
                    auto_rag_assistant.knowledge_base.load_documents(
                        auto_rag_documents, upsert=True
                    )
                else:
                    st.sidebar.error("Tidak dapat membaca PDF")
                st.session_state[f"{auto_rag_name}_uploaded"] = True
            alert.empty()

    if (
        auto_rag_assistant.knowledge_base
        and auto_rag_assistant.knowledge_base.vector_db
    ):
        if st.sidebar.button("Bersihkan Knowledge Base"):
            auto_rag_assistant.knowledge_base.vector_db.clear()
            st.sidebar.success("Knowledge base Terhapus")

    if auto_rag_assistant.storage:
        auto_rag_assistant_run_ids: List[str] = (
            auto_rag_assistant.storage.get_all_run_ids()
        )
        new_auto_rag_assistant_run_id = st.sidebar.selectbox(
            "Run ID", options=auto_rag_assistant_run_ids
        )
        if (
            st.session_state["auto_rag_assistant_run_id"]
            != new_auto_rag_assistant_run_id
        ):
            logger.info(
                f"---*--- Loading {llm_model} run: {new_auto_rag_assistant_run_id} ---*---"
            )
            st.session_state["auto_rag_assistant"] = get_auto_rag_assistant(
                llm_model=llm_model, run_id=new_auto_rag_assistant_run_id
            )
            st.rerun()

    if st.sidebar.button("Chat baru"):
        restart_assistant()

    if "embeddings_model_updated" in st.session_state:
        st.sidebar.info(
            "Harap tambahkan dokumen lagi karena model penyematan telah berubah."
        )
        st.session_state["embeddings_model_updated"] = False
