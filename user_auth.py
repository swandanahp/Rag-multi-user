import streamlit as st
import bcrypt
import psycopg2
from psycopg2 import sql
from db_config import get_connection

# Function to handle login

def login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    query = sql.SQL("""
        SELECT id, username, password_hash, role
        FROM users
        WHERE username = %s
    """)
    cursor.execute(query, (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(password.encode(), user[2].encode()):
        st.session_state['username'] = user[1]
        st.session_state['role'] = user[3]
        st.session_state['logged_in'] = True
        return user[0]  # Return user_id
    return None

# Function to handle logout
def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None

# Function to check authentication status
def is_authenticated():
    return st.session_state.get('logged_in', False)

# Function to check admin role
def is_admin():
    return st.session_state.get('role') == 'admin'

