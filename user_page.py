import streamlit as st
from phi.assistant import Assistant
from phi.utils.log import logger
import json
from db_config import get_connection, DB_NAME, DB_USER, DB_HOST, DB_PORT
from openai import OpenAI
import psycopg2
import os
import time
from assistant import get_auto_rag_assistant
from db_chat.utils.chat_functions import run_chat_sequence, get_final_system_prompt, prepare_sidebar_data
from db_chat.utils.database_functions import get_database_info, get_schema_names, ask_postgres_database

# Initialize OpenAI client
client = OpenAI()

# Constants
MAX_TOKENS_ALLOWED = 4000
MAX_MESSAGES_TO_OPENAI = 10
TOKEN_BUFFER = 200

# Database credentials from db_config.py
db_credentials = {
    "host": DB_HOST,
    "database": DB_NAME,
    "user": DB_USER,
    "port": DB_PORT
}

def load_chat_from_db(user_id: str, run_id: str, chat_type: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT messages FROM user_chat_sessions WHERE user_id = %s AND run_id = %s AND %s = ANY(chat_type)",
        (user_id, run_id, chat_type)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return json.loads(result[0]) if result else None

def save_chat_to_db(user_id: str, run_id: str, messages: list, chat_type: str):
    conn = get_connection()
    cursor = conn.cursor()
    messages_json = json.dumps(messages)
    cursor.execute(
        """
        INSERT INTO user_chat_sessions (user_id, run_id, messages, chat_type)
        VALUES (%s, %s, %s, ARRAY[%s])
        ON CONFLICT (user_id, run_id)
        DO UPDATE SET messages = %s, chat_type = array_append(user_chat_sessions.chat_type, %s)
        """,
        (user_id, run_id, messages_json, chat_type, messages_json, chat_type)
    )
    conn.commit()
    cursor.close()
    conn.close()

def clear_chat_history():
    if "document_chat_history" in st.session_state:
        st.session_state["document_chat_history"] = []
    if "db_chat_history" in st.session_state:
        st.session_state["db_chat_history"] = []

def count_tokens(text):
    return len(text.split())

def save_conversation(chat_history, chat_type):
    os.makedirs("conversations", exist_ok=True)
    filename = f"conversations/{chat_type}_conversation_{st.session_state.get('user_id', 'anonymous')}_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        for message in chat_history:
            f.write(f"{message['role']}: {message['content']}\n\n")
    return filename

def show_document_chat():
    auto_rag_assistant: Assistant = get_auto_rag_assistant(
        user_id=str(st.session_state.get("user_id")),  # Convert user_id to string
        run_id=st.session_state.get("document_chat_run_id")
    )

    if "document_chat_run_id" not in st.session_state:
        st.session_state["document_chat_run_id"] = auto_rag_assistant.create_run()

    if "document_chat_history" not in st.session_state:
        st.session_state["document_chat_history"] = [{"role": "assistant", "content": "Halo, ada yang bisa saya bantu?"}]

    for message in st.session_state["document_chat_history"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input():
        st.session_state["document_chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            response = ""
            for chunk in auto_rag_assistant.run(prompt):
                response += chunk
                st.write(response)

        st.session_state["document_chat_history"].append({"role": "assistant", "content": response})
        save_chat_to_db(str(st.session_state["user_id"]), st.session_state["document_chat_run_id"], st.session_state["document_chat_history"], "document")

def show_database_chat():
    st.title("🤖 Penelusuran Database Auditor")

    # Get database schema information
    conn = get_connection()
    schemas = get_schema_names(conn)
    database_schema_dict = get_database_info(conn, schemas)
    conn.close()

    # Prepare data for the sidebar dropdowns
    sidebar_data = prepare_sidebar_data(database_schema_dict)

    # Dropdown for schema selection
    selected_schema = st.sidebar.selectbox("📂 Pilih schema", list(sidebar_data.keys()))

    # Multiselect for table selection based on chosen Schema
    selected_tables = st.sidebar.multiselect("📜 Pilih tabel", list(sidebar_data[selected_schema].keys()))

    # Display selected tables
    if selected_tables:
        st.sidebar.subheader("Tabel Terpilih:")
        for table in selected_tables:
            st.sidebar.write(f"📌 {table}")

    # Initialize session state for database chat
    if "db_chat_history" not in st.session_state:
        st.session_state["db_chat_history"] = [{"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials, selected_tables=selected_tables, selected_schema=selected_schema)}]

    user_id = str(st.session_state["user_id"])  # Convert user_id to string
    run_id = st.session_state.get("db_chat_run_id", "default_db_run")

    # Load chat history from database
    db_chat_history = load_chat_from_db(user_id, run_id, "database")
    if db_chat_history:
        st.session_state["db_chat_history"] = db_chat_history

    # Chat input and processing
    if (prompt := st.chat_input("apa yang anda ingin tahu?")) is not None:
        st.session_state.db_chat_history.append({"role": "user", "content": prompt})
        save_chat_to_db(user_id, run_id, st.session_state["db_chat_history"], "database")

        total_tokens = sum(count_tokens(message["content"]) for message in st.session_state["db_chat_history"])
        while total_tokens + count_tokens(prompt) + TOKEN_BUFFER > MAX_TOKENS_ALLOWED:
            removed_message = st.session_state["db_chat_history"].pop(1)  # Keep the system message
            total_tokens -= count_tokens(removed_message["content"])

    # Display chat messages
    for message in st.session_state["db_chat_history"][1:]:
        if message["role"] == "user":
            st.chat_message("user", avatar='🧑‍💻').write(message["content"])
        elif message["role"] == "assistant":
            st.chat_message("assistant", avatar='🤖').write(message["content"])

    # Generate and display AI response
    if st.session_state["db_chat_history"] and st.session_state["db_chat_history"][-1]["role"] != "assistant":
        with st.spinner("⌛Connecting to AI model..."):
            recent_messages = st.session_state["db_chat_history"][-MAX_MESSAGES_TO_OPENAI:]
            new_message = run_chat_sequence(recent_messages, [], selected_tables, selected_schema)

            st.session_state["db_chat_history"].append(new_message)
            save_chat_to_db(user_id, run_id, st.session_state["db_chat_history"], "database")

            st.chat_message("assistant", avatar='🤖').write(new_message["content"])

        # Display token usage
        max_tokens = MAX_TOKENS_ALLOWED
        current_tokens = sum(count_tokens(message["content"]) for message in st.session_state["db_chat_history"])
        progress = min(1.0, max(0.0, current_tokens / max_tokens))
        st.progress(progress)
        st.write(f"Tokens Used: {current_tokens}/{max_tokens}")
        if current_tokens > max_tokens:
            st.warning("Note: Karena batasan karakter, beberapa pesan lama mungkin tidak dipertimbangkan dalam percakapan yang sedang berlangsung dengan AI.")

    # Add save conversation button
    if st.sidebar.button("Simpan Chat💾"):
        saved_file_path = save_conversation(st.session_state["db_chat_history"], "database")
        st.sidebar.success(f"Percakapan disimpan di: {saved_file_path}")
        st.sidebar.markdown(f"Percakapan telah disimpan! [Open File]({saved_file_path})")

    # Add clear conversation button
    if st.sidebar.button("Bersihkan Chat🗑️"):
        save_conversation(st.session_state["db_chat_history"], "database")
        clear_chat_history()
        st.rerun()

def show_user_page():
    st.header("Prawata Ai")
    st.subheader("Pegadaian Risk Assessment With Artificial Technology for Auditor")
    
    # Add sidebar for menu selection
    menu_selection = st.sidebar.radio("Select Chat Type", ["Document Chat", "Database Chat"])
    
    if menu_selection == "Document Chat":
        show_document_chat()
    elif menu_selection == "Database Chat":
        show_database_chat()
