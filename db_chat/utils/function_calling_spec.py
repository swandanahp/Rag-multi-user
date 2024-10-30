from utils.database_functions import database_schema_string

# Specify function descriptions for OpenAI function calling 
functions = [
    {
        "name": "ask_postgres_database",
        "description": "Gunakan fungsi ini untuk menjawab pertanyaan pengguna tentang database. Output harus berupa query SQL yang lengkap.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": f""" Kueri SQL yang mengekstrak informasi yang menjawab pertanyaan pengguna dari database Postgres. Tulis SQL dalam struktur skema berikut:
                            {database_schema_string}. Tuliskan kueri dalam format SQL saja, bukan JSON. Jangan sertakan jeda baris atau karakter apa pun yang tidak dapat dijalankan di Postgres.  
                            """,
                }
            },
            "required": ["query"],
        },
    }
]
