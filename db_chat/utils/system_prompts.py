import psycopg2
import streamlit as st
from utils.config import db_credentials

GENERATE_SQL_PROMPT = """
Kamu adalah Prawata, seorang spesialis SQL AI PostgreSQL. Misi Anda adalah mengurai kode pertanyaan pengguna, membuat skrip SQL yang tepat, menjalankannya, dan menampilkan hasilnya secara ringkas. Pertahankan persona Andy dalam semua komunikasi.

Harap patuhi panduan berikut selama interaksi:
<rules>
1. Gunakan karakter pengganti seperti "%keyword%" dan klausa 'LIKE' secara ketat saat mencoba menemukan teks yang mungkin tidak sama persis.
2. Pastikan variabel SQL tidak dimulai dengan angka.
3. Gunakan tabel dan kolom yang diberikan, tanpa membuat asumsi yang tidak berdasar.
4. Secara umum, batasi jumlah hasil hingga 10, kecuali dinyatakan lain.
5. Sajikan kueri SQL dalam format markdown yang rapi, seperti ```sql code```.
6. Usahakan untuk menawarkan hanya satu skrip SQL dalam satu respons.
7. Lindungi dari injeksi SQL dengan membersihkan input pengguna.
8. Jika kueri tidak memberikan hasil, sarankan kemungkinan cara lain untuk melakukan penyelidikan.
9. Lakukan penelusuran secara ketat pada tabel dalam format {{schema}}.{{table}}, misalnya SELECT * FROM prod.dim_sales_agent_tbl WHERE seniority_level LIKE '%enior%' where prod = {{schema}} and dim_sales_agent_tbl = {{table}}
10. Hanya gunakan tabel yang telah dipilih oleh pengguna. Tabel yang dipilih akan disediakan dalam pesan sistem.
</rules>

Mulailah dengan pengantar singkat sebagai Prawata dan tawarkan ikhtisar metrik yang tersedia. Namun, hindari memberi nama setiap tabel atau skema. Pengantar tidak boleh melebihi 300 karakter dalam keadaan apa pun.

Untuk setiap keluaran SQL, sertakan alasan singkat, tampilkan hasilnya, dan berikan penjelasan dalam konteks permintaan awal pengguna. Selalu format SQL sebagai {{database}}.{{schema}}.{{table}}.

Sebelum menyajikan, konfirmasikan validitas skrip SQL dan kerangka data. Nilai apakah kueri pengguna benar-benar memerlukan respons basis data. Jika tidak, pandu mereka seperlunya.
"""

@st.cache_data(show_spinner=False)
def get_table_context(schema: str, table: str, db_credentials: dict):
    conn = psycopg2.connect(**db_credentials)
    cursor = conn.cursor()
    cursor.execute(f"""
    SELECT column_name, data_type FROM information_schema.columns
    WHERE table_schema = '{schema}' AND table_name = '{table}'
    """)
    columns = cursor.fetchall()

    columns_str = "\n".join([f"- **{col[0]}**: {col[1]}" for col in columns])
    context = f"""
    Table: <tableName> {schema}.{table} </tableName>
    Columns for {schema}.{table}:
    <columns>\n\n{columns_str}\n\n</columns>
    """
    cursor.close()
    conn.close()
    return context

def get_all_tables_from_db(db_credentials: dict):
    conn = psycopg2.connect(**db_credentials)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    """)
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    return tables

def get_all_table_contexts(db_credentials: dict):
    tables = get_all_tables_from_db(db_credentials)
    table_contexts = [get_table_context(schema, table, db_credentials) for schema, table in tables]
    return '\n'.join(table_contexts)

def get_data_dictionary(db_credentials: dict):
    tables = get_all_tables_from_db(db_credentials)
    data_dict = {}
    for schema, table in tables:
        conn = psycopg2.connect(**db_credentials)
        cursor = conn.cursor()
        cursor.execute(f"""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table}'
        """)
        columns = cursor.fetchall()
        data_dict[f"{schema}.{table}"] = {col[0]: col[1] for col in columns}
        cursor.close()
        conn.close()
    return data_dict  

def get_final_system_prompt(db_credentials: dict, selected_tables: list, selected_schema: str):
    if not selected_tables:
        return f"{GENERATE_SQL_PROMPT}\n\nBelum ada tabel yang dipilih. Silakan pilih tabel dari {selected_schema} schema untuk mulai query."
    
    table_contexts = "\n".join([get_table_context(selected_schema, table, db_credentials) for table in selected_tables])
    return f"{GENERATE_SQL_PROMPT}\n\nSelected tables:\n{table_contexts}"

if __name__ == "__main__":
    st.header("System prompt for AI Database Chatbot")
    
    # Display the data dictionary
    data_dict = get_data_dictionary(db_credentials=db_credentials)
    data_dict_str = "\n".join(
        [f"{table}:\n" + "\n".join(
            [f"    {column}: {dtype}" for column, dtype in columns.items()]) for table, columns in data_dict.items()])

    # For testing purposes, we'll use all tables
    all_tables = [table for schema, table in get_all_tables_from_db(db_credentials) if schema == 'public']
    SYSTEM_PROMPT = get_final_system_prompt(db_credentials=db_credentials, selected_tables=all_tables, selected_schema='public')
    st.markdown(SYSTEM_PROMPT)
