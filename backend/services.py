import os
from dotenv import load_dotenv

# Load env before importing src modules to ensure keys are available
load_dotenv()

from src.store import EmbeddingStore
from src.embeddings import LocalEmbedder
from src.agent import KnowledgeBaseAgent

# Khởi tạo Embedder (Dùng mô hình Offline để không bị giới hạn 429)
try:
    embedder = LocalEmbedder()
except Exception as e:
    print(f"Warning: LocalEmbedder init failed: {e}. Using MockEmbedder.")
    from src.embeddings import MockEmbedder
    embedder = MockEmbedder()

# Khởi tạo Store
store = EmbeddingStore(collection_name="rag_web_collection", embedding_fn=embedder)

# Hàm LLM cho Agent và Process Text
def get_gemini_response(prompt: str) -> str:
    try:
        from google import genai
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"LLM Error: {str(e)}"

agent = KnowledgeBaseAgent(store=store, llm_fn=get_gemini_response)

def get_store():
    return store

def get_agent():
    return agent
