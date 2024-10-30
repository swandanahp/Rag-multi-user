import streamlit as st
from utils.config import db_credentials, MAX_TOKENS_ALLOWED, MAX_MESSAGES_TO_OPENAI, TOKEN_BUFFER
from utils.system_prompts import get_final_system_prompt
from utils.chat_functions import run_chat_sequence, clear_chat_history, count_tokens, prepare_sidebar_data
from utils.database_functions import database_schema_dict
from utils.function_calling_spec import functions
from utils.helper_functions import save_conversation
from assets.dark_theme import dark
from assets.light_theme import light
from assets.made_by_sdw import made_by_sdw

if __name__ == "__main__":

    ########### A. SIDEBAR ###########

    # Prepare data for the sidebar dropdowns
    sidebar_data = prepare_sidebar_data(database_schema_dict)
    st.sidebar.markdown("<div class='made_by'>DIV SPI🔋</div>", unsafe_allow_html=True)

    ### POSTGRES DB OBJECTS VIEWER ###

    st.markdown(made_by_sdw, unsafe_allow_html=True)
    st.sidebar.title("🔍 DB Viewer")

    # Dropdown for schema selection
    selected_schema = st.sidebar.selectbox("📂 Pilih schema", list(sidebar_data.keys()))

    # Multiselect for table selection based on chosen Schema
    selected_tables = st.sidebar.multiselect("📜 Pilih tabel", list(sidebar_data[selected_schema].keys()))

    # Display selected tables
    if selected_tables:
        st.sidebar.subheader("Tabel Terpilih:")
        for table in selected_tables:
            st.sidebar.write(f"📌 {table}")

    ### SAVE CONVERSATION BUTTON ###

    if st.sidebar.button("Simpan Chat💾"):
        saved_file_path = save_conversation(st.session_state["full_chat_history"])
        st.sidebar.success(f"Percakapan disimpan di: {saved_file_path}")
        st.sidebar.markdown(f"Percakapan telah disimpan! [Open File]({saved_file_path})")

    ### CLEAR CONVERSATION BUTTON ###

    if st.sidebar.button("Bersihkan Chat🗑️"):
        save_conversation(st.session_state["full_chat_history"]) 
        clear_chat_history()

    ### TOGGLE THEME BUTTON ###

    current_theme = st.session_state.get("theme", "light")
    st.markdown(f"<body class='{current_theme}'></body>", unsafe_allow_html=True)

    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    if st.sidebar.button("Terang/Gelap🚨"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.experimental_rerun()

    theme_style = dark if st.session_state.theme == "dark" else light
    st.markdown(theme_style, unsafe_allow_html=True)

    ########### B. CHAT INTERFACE ###########

    ### TITLE ###

    st.title("🤖 Penelusuran Database Auditor")

    ### SESSION STATE ###

    if "full_chat_history" not in st.session_state:
        st.session_state["full_chat_history"] = [{"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials, selected_tables=selected_tables, selected_schema=selected_schema)}]

    if "api_chat_history" not in st.session_state:
        st.session_state["api_chat_history"] = [{"role": "system", "content": get_final_system_prompt(db_credentials=db_credentials, selected_tables=selected_tables, selected_schema=selected_schema)}]

    ### CHAT FACILITATION ###

    if (prompt := st.chat_input("apa yang anda ingin tahu?")) is not None:
        st.session_state.full_chat_history.append({"role": "user", "content": prompt})

        total_tokens = sum(count_tokens(message["content"]) for message in st.session_state["api_chat_history"])
        while total_tokens + count_tokens(prompt) + TOKEN_BUFFER > MAX_TOKENS_ALLOWED:
            removed_message = st.session_state["api_chat_history"].pop(0)
            total_tokens -= count_tokens(removed_message["content"])

        st.session_state.api_chat_history.append({"role": "user", "content": prompt})

    for message in st.session_state["full_chat_history"][1:]:
        if message["role"] == "user":
            st.chat_message("user", avatar='🧑‍💻').write(message["content"])
        elif message["role"] == "assistant":
            st.chat_message("assistant", avatar='🤖').write(message["content"])

    if st.session_state["api_chat_history"][-1]["role"] != "assistant":
        with st.spinner("⌛Connecting to AI model..."):
            recent_messages = st.session_state["api_chat_history"][-MAX_MESSAGES_TO_OPENAI:]
            new_message = run_chat_sequence(recent_messages, functions, selected_tables, selected_schema)

            st.session_state["api_chat_history"].append(new_message)
            st.session_state["full_chat_history"].append(new_message)

            st.chat_message("assistant", avatar='🤖').write(new_message["content"])

        max_tokens = MAX_TOKENS_ALLOWED
        current_tokens = sum(count_tokens(message["content"]) for message in st.session_state["full_chat_history"])
        progress = min(1.0, max(0.0, current_tokens / max_tokens))
        st.progress(progress)
        st.write(f"Tokens Used: {current_tokens}/{max_tokens}")
        if current_tokens > max_tokens:
            st.warning("Note: Karena batasan karakter, beberapa pesan lama mungkin tidak dipertimbangkan dalam percakapan yang sedang berlangsung dengan AI.")
