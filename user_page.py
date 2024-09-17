import streamlit as st
from phi.assistant import Assistant
from phi.utils.log import logger
from db_config import get_connection


def show_user_page():
    st.header("Prawata Ai")
    st.subheader("Pegadaian Risk Assessment With Artificial Technology for Auditor")
    auto_rag_assistant: Assistant = st.session_state["auto_rag_assistant"]

    # Create a new run ID for this session and save it to the database
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_chat_sessions (user_id, run_id)
                VALUES ((SELECT id FROM users WHERE username = %s), %s)
                RETURNING id;
                """,
                (st.session_state['username'], str(st.session_state["auto_rag_assistant_run_id"]))
            )
            conn.commit()

    assistant_chat_history = auto_rag_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Halo, ada yang bisa saya bantu?"}]

    if prompt := st.chat_input():
        st.session_state["messages"].append({"role": "user", "content": prompt})

    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            resp_container = st.empty()
            response = ""
            for delta in auto_rag_assistant.run(question):
                response += delta
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

