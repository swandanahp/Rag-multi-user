from typing import Optional
from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage

db_url = "postgresql+psycopg://postgres:postgres@localhost:5432/Testing"

# Setup Assistant
def get_auto_rag_assistant(
    llm_model: str = "gpt-4-turbo",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Ambil Auto RAG Assistant"""

    return Assistant(
        name="auto_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=OpenAIChat(model=llm_model),
        storage=PgAssistantStorage(table_name="auto_rag_assistant_openai", db_url=db_url),
        knowledge_base=AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection="auto_rag_documents_openai",
                embedder=OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536),
            ),
            # referensi sebagai acuan prompt
            num_documents=5,
        ),
        description="Anda adalah bot asisten yang bernama 'Prawata Ai' dan tujuan Anda adalah membantu pengguna dengan cara sebaik mungkin.",
        instructions=[
            "Jika ada pertanyaan pengguna, pertama-tama SELALU telusuri basis pengetahuan Anda menggunakan alat `search_knowledge_base` untuk melihat apakah Anda memiliki informasi relevan.",
            "Jika pengguna menanyakan pelanggaran pasal, carilah pada file perjanjian kerja bersama 2023 - 2025 pada BAB XIV TATA TERTIB DAN DISIPLIN KARYAWAN"
            "Jika Anda perlu merujuk riwayat obrolan, gunakan alat `get_chat_history`.",
            "Jika pertanyaan pengguna tidak jelas, ajukan pertanyaan klarifikasi untuk mendapatkan informasi lebih lanjut.",
            "Bacalah dengan cermat informasi yang telah Anda kumpulkan dan berikan jawaban yang jelas dan lengkap kepada pengguna.",
            "Jangan menggunakan frasa seperti 'berdasarkan pengetahuan saya' atau 'tergantung pada informasinya'.",
        ],
        # Show tool calls in the chat
        show_tool_calls=True,
        # This setting gives the LLM a tool to search the knowledge base for information
        search_knowledge=True,
        # This setting gives the LLM a tool to get chat history
        read_chat_history=True,
        tools=[DuckDuckGo()],
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # Adds chat history to messages
        add_chat_history_to_messages=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )