"""
Backend API (JSON) cho RAG trên Luật An ninh mạng 116/2025.

Chạy:
    uvicorn api:app --reload
    # mở http://127.0.0.1:8000/docs để thử (Swagger UI)

Endpoints:
    GET  /            -> thông tin & trạng thái
    GET  /chapters    -> danh sách 8 chương
    POST /search      -> tìm các đoạn liên quan (JSON)
    POST /ask         -> hỏi đáp RAG, trả lời + nguồn (JSON)

KHÔNG sửa package `src/` — chỉ import và dùng lại.
"""
from __future__ import annotations

import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src import (
    Document,
    EmbeddingStore,
    KnowledgeBaseAgent,
    FixedSizeChunker,
    RecursiveChunker,
    SentenceChunker,
    ArticleChunker,
    ChapterChunker,
    ClauseChunker,
    MarkdownHeaderChunker,
    ParagraphChunker,
    MockEmbedder,
    OpenAIEmbedder,
)

load_dotenv()

DATA_DIR = Path("data")
CHUNK_SIZE = 500
DEFAULT_CHUNKING = "recursive"
LOG_FILE = Path("qa_log.jsonl")  # mỗi dòng là 1 bản ghi JSON (câu hỏi + trả lời + score)


# Các chiến lược chunking có thể chọn qua tham số `chunking`.
# 3 cái cũ (chung) + 5 cái mới (phù hợp văn bản luật).
CHUNKERS = {
    "recursive": lambda: RecursiveChunker(chunk_size=CHUNK_SIZE),
    "fixed": lambda: FixedSizeChunker(chunk_size=CHUNK_SIZE, overlap=50),
    "sentence": lambda: SentenceChunker(max_sentences_per_chunk=4),
    "dieu": lambda: ArticleChunker(max_size=1500),          # chia theo Điều
    "chuong": lambda: ChapterChunker(max_size=4000),        # chia theo Chương
    "khoan": lambda: ClauseChunker(max_size=800),           # chia theo Khoản
    "header": lambda: MarkdownHeaderChunker(max_size=1500),  # chia theo heading markdown
    "paragraph": lambda: ParagraphChunker(max_size=600),    # chia theo đoạn
}


def append_log(record: dict) -> None:
    """Ghi nối thêm 1 bản ghi JSON vào qa_log.jsonl."""
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_log(limit: int = 20) -> list[dict]:
    """Đọc các bản ghi gần nhất từ qa_log.jsonl."""
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(ln) for ln in lines if ln.strip()][-limit:]

# ----- chọn embedder & LLM (giống main.py, fallback an toàn) -----------------

def build_llm():
    """Trả về llm_fn: gọi OpenAI chat thật nếu được, không thì echo demo."""
    if os.getenv("EMBEDDING_PROVIDER", "").strip().lower() == "openai":
        try:
            from openai import OpenAI

            client = OpenAI()
            model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

            def llm(prompt: str) -> str:
                resp = client.chat.completions.create(
                    model=model,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message.content.strip()

            return llm
        except Exception:
            pass
    return lambda prompt: "[demo LLM] " + prompt[:200]


# ----- vector store: in-memory (EmbeddingStore) hoặc ChromaDB ----------------

STATE: dict = {}
STORE_TYPES = ("memory", "chroma")
DEFAULT_STORE = "memory"


def list_chapters() -> list[dict]:
    """Danh sách chương đọc từ file (độc lập với loại store)."""
    out = []
    for path in sorted(DATA_DIR.glob("luat116_ch*.md")):
        match = re.search(r"_ch(\d+)$", path.stem)
        out.append({"doc_id": path.stem, "chuong": str(int(match.group(1))) if match else ""})
    return out


VALID_CHUONGS = {c["chuong"] for c in list_chapters()}


def chroma_available() -> bool:
    try:
        import chromadb  # noqa: F401
        return True
    except Exception:
        return False


class ChromaStore:
    """Vector store dùng ChromaDB thật (ANN + metadata filter), không gian cosine.

    Cùng interface với EmbeddingStore: add_documents / search / search_with_filter /
    get_collection_size / delete_document — nên các endpoint dùng được ngay.
    """

    def __init__(self, collection_name: str, embedding_fn) -> None:
        import chromadb

        self._embedding_fn = embedding_fn
        self._client = chromadb.EphemeralClient()
        try:
            self._client.delete_collection(collection_name)  # dựng mới mỗi lần
        except Exception:
            pass
        self._col = self._client.create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._next = 0

    def add_documents(self, docs: list[Document]) -> None:
        if not docs:
            return
        contents = [d.content for d in docs]
        embed_batch = getattr(self._embedding_fn, "embed_batch", None)
        embeddings = embed_batch(contents) if embed_batch else [self._embedding_fn(c) for c in contents]
        ids, metas = [], []
        for d in docs:
            meta = dict(d.metadata or {})
            meta.setdefault("doc_id", d.id)
            ids.append(f"{d.id}#{self._next}")
            self._next += 1
            metas.append(meta)
        self._col.add(ids=ids, embeddings=embeddings, documents=contents, metadatas=metas)

    def get_collection_size(self) -> int:
        return self._col.count()

    def search_with_filter(self, query, top_k=3, metadata_filter=None):
        kwargs = {"query_embeddings": [self._embedding_fn(query)], "n_results": top_k}
        if metadata_filter:
            kwargs["where"] = metadata_filter
        res = self._col.query(**kwargs)
        ids, docs = res["ids"][0], res["documents"][0]
        metas, dists = res["metadatas"][0], res["distances"][0]
        return [
            {
                "id": ids[i], "doc_id": metas[i].get("doc_id"),
                "content": docs[i], "metadata": metas[i],
                "score": 1.0 - dists[i],  # cosine distance -> similarity
            }
            for i in range(len(ids))
        ]

    def search(self, query, top_k=3):
        return self.search_with_filter(query, top_k, None)

    def delete_document(self, doc_id: str) -> bool:
        before = self._col.count()
        self._col.delete(where={"doc_id": doc_id})
        return self._col.count() < before


def build_store(embedder, chunker, store_type: str = "memory", collection: str = "luat116"):
    if store_type == "chroma":
        store = ChromaStore(collection, embedder)
    else:
        store = EmbeddingStore(collection_name=collection, embedding_fn=embedder)
    docs: list[Document] = []
    for path in sorted(DATA_DIR.glob("luat116_ch*.md")):
        match = re.search(r"_ch(\d+)$", path.stem)
        chuong = str(int(match.group(1))) if match else ""
        for i, chunk in enumerate(chunker.chunk(path.read_text(encoding="utf-8"))):
            docs.append(Document(
                id=f"{path.stem}#{i}",
                content=chunk,
                metadata={"source": path.name, "doc_id": path.stem, "chuong": chuong, "lang": "vi"},
            ))
    store.add_documents(docs)
    return store


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedders: dict = {"mock": MockEmbedder()}
    try:
        embedders["openai"] = OpenAIEmbedder()  # chỉ thêm nếu có API key
    except Exception:
        pass

    STATE["embedders"] = embedders
    STATE["llm"] = build_llm()
    STATE["stores"] = {}   # cache lazy: (backend, chunking, store) -> store
    STATE["agents"] = {}   # cache lazy: (backend, chunking, store) -> agent
    preferred = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    STATE["default"] = preferred if preferred in embedders else "mock"

    get_store(STATE["default"], DEFAULT_CHUNKING, DEFAULT_STORE)  # dựng sẵn combo mặc định
    yield
    STATE.clear()


def get_store(backend: str | None, chunking: str | None, store_type: str | None = None):
    """Lấy (hoặc dựng + cache) store cho (backend, chunking, store_type). Fallback nếu lạ."""
    name = (backend or STATE["default"]).strip().lower()
    if name not in STATE["embedders"]:
        name = STATE["default"]
    ck = (chunking or DEFAULT_CHUNKING).strip().lower()
    if ck not in CHUNKERS:
        ck = DEFAULT_CHUNKING
    st = (store_type or DEFAULT_STORE).strip().lower()
    if st not in STORE_TYPES or (st == "chroma" and not chroma_available()):
        st = DEFAULT_STORE

    key = (name, ck, st)
    if key not in STATE["stores"]:
        store = build_store(STATE["embedders"][name], CHUNKERS[ck](), st, collection=f"luat_{name}_{ck}")
        STATE["stores"][key] = store
        STATE["agents"][key] = KnowledgeBaseAgent(store=store, llm_fn=STATE["llm"])
    return name, ck, st, STATE["stores"][key], STATE["agents"][key]


app = FastAPI(title="RAG Luật An ninh mạng 116/2025", version="1.0", lifespan=lifespan)

# Cho phép frontend (website) ở domain khác gọi API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- schema request/response (Pydantic -> JSON tự động) --------------------

class SearchRequest(BaseModel):
    query: str = Field(..., examples=["Lực lượng bảo vệ an ninh mạng gồm những gì?"])
    top_k: int = Field(3, ge=1, le=20)
    chuong: str | None = Field(None, description="Lọc theo chương, ví dụ '6'")
    backend: str | None = Field(None, description="'openai' hoặc 'mock' (mặc định theo .env)")
    chunking: str | None = Field(None, description="recursive|fixed|sentence|dieu|chuong|khoan|header|paragraph (mặc định recursive)")
    store: str | None = Field(None, description="'memory' hoặc 'chroma' (mặc định memory)")


class SearchHit(BaseModel):
    rank: int
    score: float
    source: str
    chuong: str
    dieu: str = ""        # ví dụ "Điều 30" — trích từ nội dung chunk (bám nguồn)
    content: str


class Citation(BaseModel):
    """Một trích dẫn nguồn gọn để frontend hiển thị grounding."""
    rank: int
    source: str
    chuong: str
    dieu: str
    score: float
    label: str            # ví dụ "Điều 30 · Chương 6 (luat116_ch06.md)"


class SearchResponse(BaseModel):
    query: str
    backend: str
    chunking: str
    store: str
    count: int
    results: list[SearchHit]


class PreviewHit(BaseModel):
    rank: int
    score: float
    source: str
    content: str  # nội dung đầy đủ của chunk


class SearchTextResponse(BaseModel):
    query: str
    backend: str
    chunking: str
    store: str
    count: int
    results: list[PreviewHit]


class AskRequest(BaseModel):
    question: str = Field(..., examples=["An ninh mạng được định nghĩa như thế nào?"])
    top_k: int = Field(3, ge=1, le=20)
    chuong: str | None = None
    backend: str | None = Field(None, description="'openai' hoặc 'mock' (mặc định theo .env)")
    chunking: str | None = Field(None, description="recursive|fixed|sentence|dieu|chuong|khoan|header|paragraph (mặc định recursive)")
    store: str | None = Field(None, description="'memory' hoặc 'chroma' (mặc định memory)")
    threshold: float | None = Field(None, ge=0.0, le=1.0, description="Ngưỡng tin cậy (0-1, mặc định 0.35)")


class AskResponse(BaseModel):
    question: str
    backend: str
    chunking: str
    store: str
    answer: str
    top_score: float
    grounded: bool            # top_score có vượt ngưỡng tin cậy không
    citations: list[Citation]  # trích dẫn nguồn gọn (bám nguồn)
    sources: list[SearchHit]


class LogEntry(BaseModel):
    time: str
    question: str
    backend: str = ""
    chunking: str = ""
    store: str = ""
    answer: str
    top_score: float
    grounded: bool = True
    citations: list[Citation] = []
    sources: list[SearchHit]


# ----- endpoints -------------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "RAG Luật An ninh mạng 116/2025",
        "available_backends": list(STATE.get("embedders", {}).keys()),
        "default_backend": STATE.get("default"),
        "available_chunkings": list(CHUNKERS.keys()),
        "default_chunking": DEFAULT_CHUNKING,
        "available_stores": [s for s in STORE_TYPES if s != "chroma" or chroma_available()],
        "default_store": DEFAULT_STORE,
        "built": [f"{b}/{c}/{s}" for (b, c, s) in STATE.get("stores", {})],
        "endpoints": ["/chapters", "/search", "/search/text", "/ask", "/history", "/docs"],
    }


@app.get("/chapters")
def chapters():
    chs = list_chapters()
    return {"count": len(chs), "chapters": chs}


GROUNDED_THRESHOLD = 0.35  # top_score dưới ngưỡng này coi như retrieval yếu


def extract_dieu(content: str) -> str:
    """Trích 'Điều N' đầu tiên trong chunk (để bám nguồn). Rỗng nếu không có."""
    match = re.search(r"Điều\s+\d+", content)
    return match.group(0) if match else ""


def strip_markdown(text: str) -> str:
    """Bỏ ký hiệu markdown (#, **, *) cho text thuần, vẫn giữ xuống dòng."""
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)   # bỏ heading ###
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)        # **đậm** -> đậm
    text = re.sub(r"\*([^*]+)\*", r"\1", text)            # *nghiêng* -> nghiêng
    return text.strip()


def normalize_chuong(value: str | None) -> str | None:
    """Chuẩn hoá & kiểm tra chuong. Trả None (bỏ lọc) nếu không phải chương hợp lệ,
    để placeholder 'string' của Swagger hay 'I'/'06' không làm rỗng kết quả."""
    if not value or not value.strip():
        return None
    v = value.strip()
    if v.isdigit():
        v = str(int(v))  # "06" -> "6"
    return v if v in VALID_CHUONGS else None


def _hits(results) -> list[SearchHit]:
    return [
        SearchHit(
            rank=i + 1,
            score=round(r["score"], 4),
            source=r["metadata"].get("source", ""),
            chuong=r["metadata"].get("chuong", ""),
            dieu=extract_dieu(r["content"]),
            content=r["content"],
        )
        for i, r in enumerate(results)
    ]


def _citations(hits: list[SearchHit]) -> list[Citation]:
    cites = []
    for h in hits:
        parts = [p for p in [h.dieu, f"Chương {h.chuong}" if h.chuong else "", f"({h.source})"] if p]
        cites.append(Citation(
            rank=h.rank, source=h.source, chuong=h.chuong, dieu=h.dieu,
            score=h.score, label=" · ".join(parts),
        ))
    return cites


@app.get("/search/text", response_model=SearchTextResponse)
def search_text(q: str, top_k: int = 3, chuong: str | None = None, backend: str | None = None, chunking: str | None = None, store: str | None = None):
    """Trả kết quả search dạng JSON: count + mỗi top_k {score, source, content}."""
    name, ck, st, vstore, _ = get_store(backend, chunking, store)
    chuong = normalize_chuong(chuong)
    filt = {"chuong": chuong} if chuong else None
    results = vstore.search_with_filter(q, top_k=top_k, metadata_filter=filt)

    items = [
        PreviewHit(
            rank=i + 1,
            score=round(r["score"], 4),
            source=f"data\\{r['metadata'].get('source', '')}",
            content=strip_markdown(r["content"]),  # đầy đủ, đã bỏ markdown
        )
        for i, r in enumerate(results)
    ]
    return SearchTextResponse(query=q, backend=name, chunking=ck, store=st, count=len(items), results=items)


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    name, ck, st, vstore, _ = get_store(req.backend, req.chunking, req.store)
    chuong = normalize_chuong(req.chuong)
    filt = {"chuong": chuong} if chuong else None
    results = vstore.search_with_filter(req.query, top_k=req.top_k, metadata_filter=filt)
    hits = _hits(results)
    return SearchResponse(query=req.query, backend=name, chunking=ck, store=st, count=len(hits), results=hits)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    name, ck, st, vstore, agent = get_store(req.backend, req.chunking, req.store)
    chuong = normalize_chuong(req.chuong)
    filt = {"chuong": chuong} if chuong else None
    store = vstore

    # Retrieve MỘT LẦN — answer và sources dùng chung kết quả này (nhất quán).
    results = store.search_with_filter(req.question, top_k=req.top_k, metadata_filter=filt)
    hits = _hits(results)

    if results:
        context = "\n\n".join(r["content"] for r in results)
        prompt = (
            "You are a helpful assistant. Answer the question using only the "
            "context below. If the context is insufficient, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {req.question}\n\n"
            "Answer:"
        )
        answer = agent.llm_fn(prompt)
    else:
        answer = "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu để trả lời câu hỏi này."

    top_score = hits[0].score if hits else 0.0
    citations = _citations(hits)
    threshold = req.threshold if req.threshold is not None else GROUNDED_THRESHOLD
    grounded = top_score >= threshold

    response = AskResponse(
        question=req.question, backend=name, chunking=ck, store=st, answer=answer, top_score=top_score,
        grounded=grounded, citations=citations, sources=hits,
    )
    # Lưu lại câu trả lời kèm score + trích dẫn nguồn vào qa_log.jsonl
    append_log({
        "time": datetime.now().isoformat(timespec="seconds"),
        "question": req.question,
        "backend": name,
        "chunking": ck,
        "store": st,
        "answer": answer,
        "top_score": top_score,
        "grounded": grounded,
        "citations": [c.model_dump() for c in citations],
        "sources": [h.model_dump() for h in hits],
    })
    return response


@app.get("/history", response_model=list[LogEntry])
def history(limit: int = 20):
    """Xem lại các câu hỏi-trả lời đã lưu (kèm score), mới nhất ở cuối."""
    return read_log(limit)
