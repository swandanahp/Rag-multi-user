import nest_asyncio
import streamlit as st
from phi.utils.log import logger
from assistant import get_auto_rag_assistant  # type: ignore
from user_auth import login, logout, is_authenticated, is_admin
from user_page import show_user_page
from admin_page import show_admin_page

nest_asyncio.apply()
st.set_page_config(
    page_title="Prawata Ai",
    page_icon=":robot_face:",
)
st.image("images/logo.png", use_column_width=True)

def main() -> None:
    if not is_authenticated():
        # Login form
        st.sidebar.header("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user_id = login(username, password)
            if user_id:
                st.session_state["user_id"] = user_id
                st.sidebar.success("Login successful")
                st.experimental_rerun()
            else:
                st.sidebar.error("Invalid credentials")
    else:
        # Initialize auto_rag_assistant if not already set
        if "auto_rag_assistant" not in st.session_state:
            st.session_state["auto_rag_assistant"] = get_auto_rag_assistant(llm_model="gpt-4-turbo")

        # Logout button
        if st.sidebar.button("Logout"):
            logout()
            st.experimental_rerun()

        # Role-based navigation
        if is_admin():
            show_admin_page()
        else:
            show_user_page()

main()
