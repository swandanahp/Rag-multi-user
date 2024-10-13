import psycopg2
import psycopg2.extras

DB_NAME = 'Testing'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_HOST = 'localhost'
DB_PORT = '5432'

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def init_db():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        session_token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '1 hour',
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_chat_sessions (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        run_id TEXT NOT NULL,
        messages TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE (user_id, run_id)
    );
    """)

    conn.commit()
    cursor.close()
    conn.close()

