import os
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

# Import custom services
from backend.services import get_store, get_agent, get_gemini_response, embedder
from src.models import Document
from src.chunking import RecursiveChunker, FixedSizeChunker, compute_similarity
from src.pdf_processor import process_text_with_llm

app = FastAPI(title="RAG AI System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str
    top_k: int = 3

class ChatRequest(BaseModel):
    query: str

@app.post("/api/upload")
def upload_document(
    file: UploadFile = File(...),
    chunking_strategy: str = Form("recursive")
):
    content = file.file.read()
    # Decode content
    text = content.decode("utf-8", errors="ignore")
    
    docs = []
    short_name = file.filename.split(".")[0][:10]
    
    if chunking_strategy == "llm":
        chunks_data = process_text_with_llm(text, doc_short_name=short_name, llm_fn=get_gemini_response)
        for item in chunks_data:
            docs.append(Document(
                id=item.get("id", f"{short_name}_{uuid.uuid4().hex[:6]}"),
                content=item.get("document", item.get("content", "")),
                metadata=item.get("metadata", {"source": file.filename})
            ))
    elif chunking_strategy == "fixed":
        chunker = FixedSizeChunker(chunk_size=500, overlap=50)
        chunks = chunker.chunk(text)
        for i, c in enumerate(chunks):
            docs.append(Document(id=f"{short_name}_{i}", content=c, metadata={"source": file.filename}))
    elif chunking_strategy == "sentence":
        from src.chunking import SentenceChunker
        chunker = SentenceChunker(max_sentences_per_chunk=3)
        chunks = chunker.chunk(text)
        for i, c in enumerate(chunks):
            docs.append(Document(id=f"{short_name}_{i}", content=c, metadata={"source": file.filename}))
    else: # recursive
        chunker = RecursiveChunker(chunk_size=500)
        chunks = chunker.chunk(text)
        for i, c in enumerate(chunks):
            docs.append(Document(id=f"{short_name}_{i}", content=c, metadata={"source": file.filename}))
            
    if not docs:
        return {"message": "Không có đoạn văn bản nào được trích xuất.", "chunks_count": 0}
        
    store = get_store()
    try:
        store.add_documents(docs)
    except Exception as e:
        import traceback
        error_msg = str(e)
        print("="*50)
        print("❌ LỖI TRONG QUÁ TRÌNH UPLOAD VÀ CHUNKING:")
        traceback.print_exc()
        print("="*50)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return {"error": True, "message": f"Lỗi giới hạn API (429 Resource Exhausted). Vui lòng đợi 1 phút. Chi tiết: {error_msg}"}
        return {"error": True, "message": f"Lỗi database: {error_msg}"}
        
    return {
        "error": False,
        "message": "Tài liệu đã được tải lên và chunking thành công", 
        "chunks_count": len(docs),
        "strategy": chunking_strategy
    }

@app.get("/api/documents")
def list_documents():
    store = get_store()
    size = store.get_collection_size()
    return {"count": size, "message": f"Có {size} chunks trong Database"}

@app.get("/api/chunks")
def list_all_chunks():
    store = get_store()
    chunks = store.get_all_documents()
    return {"chunks": chunks}

@app.post("/api/search")
def search_documents(req: SearchRequest):
    try:
        store = get_store()
        results = store.search(req.query, top_k=req.top_k)
        
        query_vector = embedder(req.query)
        
        enhanced_results = []
        for res in results:
            doc_vector = embedder(res.get("content", ""))
            cosine_sim = compute_similarity(query_vector, doc_vector)
            res["cosine_similarity"] = cosine_sim
            enhanced_results.append(res)
            
        return {"results": enhanced_results}
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return {"error": True, "message": f"Lỗi giới hạn API (429). Vui lòng đợi chút rồi thử lại."}
        return {"error": True, "message": f"Lỗi Search: {error_msg}"}

@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        agent = get_agent()
        answer = agent.answer(req.query)
        return {"answer": answer}
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return {"answer": f"Lỗi giới hạn API (429). Vui lòng đợi chút rồi thử lại."}
        return {"answer": f"Lỗi Chat: {error_msg}"}
