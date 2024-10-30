import tiktoken
import streamlit as st
from db_chat.utils.config import AI_MODEL
from db_chat.utils.api_functions import send_api_request_to_openai_api, execute_function_call

def run_chat_sequence(messages, functions, selected_tables, selected_schema):
    if "live_chat_history" not in st.session_state:
        st.session_state["live_chat_history"] = [{"role": "assistant", "content": "Halo saya Prawata, ada yang bisa dibantu?"}]

    internal_chat_history = st.session_state["live_chat_history"].copy()

    # Add selected tables information to the messages
    tables_info = f"Selected schema: {selected_schema}\nSelected tables: {', '.join(selected_tables)}"
    messages.append({"role": "system", "content": tables_info})

    chat_response = send_api_request_to_openai_api(messages, functions)
    assistant_message = chat_response.json()["choices"][0]["message"]
    
    if assistant_message["role"] == "assistant":
        internal_chat_history.append(assistant_message)

    if assistant_message.get("function_call"):
        results = execute_function_call(assistant_message, selected_tables, selected_schema)
        internal_chat_history.append({"role": "function", "name": assistant_message["function_call"]["name"], "content": results})
        internal_chat_history.append({"role": "user", "content": "Anda adalah analis data - berikan penjelasan yang dipersonalisasi/disesuaikan tentang arti hasil yang diberikan dan kaitkan dengan konteks pertanyaan pengguna menggunakan kata-kata yang jelas dan ringkas dengan cara yang mudah dipahami pengguna. Atau jawab pertanyaan yang diberikan oleh pengguna dengan cara yang membantu - apa pun itu, pastikan respons Anda bersifat manusiawi dan terkait dengan masukan awal pengguna."})
        chat_response = send_api_request_to_openai_api(internal_chat_history, functions)
        assistant_message = chat_response.json()["choices"][0]["message"]
        if assistant_message["role"] == "assistant":
            st.session_state["live_chat_history"].append(assistant_message)

    return st.session_state["live_chat_history"][-1]

def clear_chat_history():
    """ Clear the chat history stored in the Streamlit session state """
    del st.session_state["live_chat_history"]
    del st.session_state["full_chat_history"]
    del st.session_state["api_chat_history"]

def count_tokens(text):
    """ Count the total tokens used in a text string """
    if not isinstance(text, str):  
        return 0 
    encoding = tiktoken.encoding_for_model(AI_MODEL)
    total_tokens_in_text_string = len(encoding.encode(text))
    
    return total_tokens_in_text_string

def prepare_sidebar_data(database_schema_dict):
    """ Add a sidebar for visualizing the database schema objects  """
    sidebar_data = {}
    for table in database_schema_dict:
        schema_name = table["schema_name"]
        table_name = table["table_name"]
        columns = table["column_names"]

        if schema_name not in sidebar_data:
            sidebar_data[schema_name] = {}

        sidebar_data[schema_name][table_name] = columns
    return sidebar_data

def get_final_system_prompt(db_credentials, selected_tables, selected_schema):
    return f"""You are a database assistant for the PostgreSQL database named {db_credentials['database']}.
    You are working with the schema: {selected_schema} and tables: {', '.join(selected_tables)}.
    Provide clear and concise responses to user queries about the database structure and content."""
