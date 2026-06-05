import os
import json
from dotenv import load_dotenv

# Import các module từ dự án của bạn
from src.store import EmbeddingStore
from src.models import Document
from src.embeddings import OpenAIEmbedder
from src.chunking import compute_similarity

def run_test():
    # Load API key
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY").startswith("điền"):
        print("CẢNH BÁO: Không tìm thấy GEMINI_API_KEY hợp lệ trong môi trường. Sẽ dùng MockEmbedder thay thế.")
        from src.embeddings import MockEmbedder
        embedder = MockEmbedder()
        llm_fn = lambda prompt: '[{"id":"mock_1","document":"Văn bản luật mock","metadata":{"topic":"luat","summary":"mock"}}]'
    else:
        print("Đang sử dụng GeminiEmbedder...")
        from src.embeddings import GeminiEmbedder
        embedder = GeminiEmbedder()
        
        def gemini_llm_call(prompt_text: str) -> str:
            from google import genai
            import os
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt_text
            )
            return response.text
        llm_fn = gemini_llm_call

    print("\n[1] Khởi tạo ChromaDB Store...")
    # Khởi tạo store
    store = EmbeddingStore(collection_name="demo_luat", embedding_fn=embedder)
    
    print("\n[2] Nạp dữ liệu từ 81-btc.md vào database...")
    from src.pdf_processor import process_text_with_llm
    file_path = "data/81-btc.md"
    
    if os.path.exists(file_path):
        print(f"Đang phân tích {file_path} bằng LLM...")
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        # Giới hạn text nếu quá dài để tránh bị nghẽn (demo lấy 3000 ký tự đầu tiên)
        if len(raw_text) > 3000:
            print("File khá dài, chỉ lấy 3000 ký tự đầu tiên để demo API...")
            raw_text = raw_text[:3000]

        chunks_data = process_text_with_llm(raw_text, doc_short_name="81btc", llm_fn=llm_fn)
        
        if chunks_data:
            docs = []
            for item in chunks_data:
                docs.append(Document(
                    id=item.get("id", "unknown_id"),
                    content=item.get("document", ""),
                    metadata=item.get("metadata", {})
                ))
            store.add_documents(docs)
            print(f"Đã nạp thành công {len(docs)} chunks tài liệu.")
        else:
            print("Không trích xuất được chunk nào.")
            return
    else:
        print(f"Không tìm thấy file {file_path}. Hãy kiểm tra lại.")
        return

    # Câu hỏi người dùng liên quan đến nội dung 81-btc
    query = "Quy định về thuế hoặc phí là gì?"
    print(f"\n[3] Câu truy vấn (Query): '{query}'")
    
    # Vector hoá câu query
    query_vector = embedder(query)
    
    # Tìm kiếm trong DB
    top_k = 3
    print(f"\nĐang tìm kiếm Top {top_k} kết quả phù hợp nhất trong ChromaDB...")
    results = store.search(query, top_k=top_k)
    
    print("\n" + "="*50)
    print(" KẾT QUẢ TÌM KIẾM VÀ SO SÁNH VECTƠ (DATA LUẬT)")
    print("="*50)
    
    for i, res in enumerate(results):
        doc_content = res["content"]
        doc_vector = embedder(doc_content)
        cosine_sim = compute_similarity(query_vector, doc_vector)
        
        print(f"\n🏆 Hạng {i+1}:")
        print(f"   • ID: {res['id']}")
        print(f"   • Topic: {res.get('metadata', {}).get('topic')}")
        print(f"   • Tóm tắt: {res.get('metadata', {}).get('summary')}")
        print(f"   • Nội dung trích xuất: {doc_content[:200]}...")
        print("-" * 40)
        print(f"   👉 Điểm hệ thống (L2 -> Score): {res.get('score', 0):.4f}")
        print(f"   👉 Cosine Similarity (tính tay): {cosine_sim:.4f}")
        
    print("\n" + "="*50)

if __name__ == "__main__":
    run_test()
