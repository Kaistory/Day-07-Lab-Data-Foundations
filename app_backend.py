from __future__ import annotations

import asyncio
import os
import sys
import threading
from typing import Any

from aiohttp import web
from dotenv import load_dotenv
from openai import OpenAI

from benchmark_legal import (
    ROOT,
    chunk_documents,
    collection_name,
    make_strategies,
)
from src import EmbeddingStore, OpenAIEmbedder

WEB_DIR = ROOT / "web"
STRATEGIES = ("fixed", "sentence", "recursive", "semantic", "document")
DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


class LegalRAGService:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env", override=False)
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required")

        self.embedding_model = os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            DEFAULT_EMBEDDING_MODEL,
        )
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)
        self.embedder = OpenAIEmbedder(
            model_name=self.embedding_model,
            dimensions=None,
            batch_size=100,
        )
        self.client = OpenAI()
        self._stores: dict[str, EmbeddingStore] = {}
        self._index_status: dict[str, str] = {}
        self._lock = threading.Lock()

    def ensure_store(self, strategy: str) -> EmbeddingStore:
        if strategy not in STRATEGIES:
            raise ValueError(f"Unsupported strategy: {strategy}")

        with self._lock:
            cached = self._stores.get(strategy)
            if cached is not None:
                return cached

            chunker = make_strategies(self.embedder)[strategy]
            documents = chunk_documents(chunker, strategy)
            store = EmbeddingStore(
                collection_name=collection_name(strategy, self.embedding_model),
                embedding_fn=self.embedder,
            )
            existing_size = store.get_collection_size()
            if existing_size == len(documents):
                status = f"reused {existing_size} persisted chunks"
            else:
                if existing_size:
                    store.clear()
                store.add_documents(documents)
                status = f"indexed and persisted {len(documents)} chunks"

            self._stores[strategy] = store
            self._index_status[strategy] = status
            print(
                f"[INDEX] strategy={strategy} collection="
                f"{collection_name(strategy, self.embedding_model)} status={status}",
                flush=True,
            )
            return store

    def ask(
        self,
        question: str,
        strategy: str,
        top_k: int,
        threshold: float,
        document_number: str | None,
        citation: str | None,
    ) -> dict[str, Any]:
        store = self.ensure_store(strategy)
        metadata_filter = None
        if citation:
            metadata_filter = {"citation": citation}
        elif document_number:
            metadata_filter = {"document_number": document_number}

        if metadata_filter:
            retrieved = store.search_with_filter(
                question,
                top_k=top_k,
                metadata_filter=metadata_filter,
            )
        else:
            retrieved = store.search(question, top_k=top_k)

        accepted = [
            result for result in retrieved if float(result["score"]) >= threshold
        ]
        self._print_retrieval(
            question=question,
            strategy=strategy,
            threshold=threshold,
            metadata_filter=metadata_filter,
            results=retrieved,
        )

        serialized = [
            self._serialize_result(result, rank, threshold)
            for rank, result in enumerate(retrieved, start=1)
        ]
        if not accepted:
            return {
                "answer": (
                    "Không tìm thấy bằng chứng đủ mạnh trong bộ dữ liệu với ngưỡng "
                    f"{threshold:.2f}. Hãy giảm threshold, tăng top K hoặc đặt câu hỏi "
                    "cụ thể hơn theo số văn bản và Điều."
                ),
                "status": "insufficient_context",
                "used_count": 0,
                "retrieved_count": len(retrieved),
                "results": serialized,
                "strategy": strategy,
                "threshold": threshold,
                "top_k": top_k,
                "filter": metadata_filter,
                "chat_model": self.chat_model,
                "embedding_model": self.embedding_model,
                "index_status": self._index_status[strategy],
            }

        evidence_blocks = []
        for index, result in enumerate(accepted, start=1):
            metadata = result["metadata"]
            evidence_blocks.append(
                "\n".join(
                    [
                        f"[{index}] Citation: {metadata.get('citation', '-')}",
                        f"Source: {metadata.get('source', '-')}",
                        f"Article: {metadata.get('article', '-') or '-'}",
                        f"Similarity score: {float(result['score']):.6f}",
                        "Content:",
                        result["content"],
                    ]
                )
            )

        prompt = (
            "Bạn là trợ lý tra cứu pháp luật Việt Nam. Chỉ sử dụng bằng chứng được "
            "cung cấp bên dưới. Trả lời trực tiếp bằng tiếng Việt, rõ ràng, không "
            "suy diễn ngoài tài liệu. Mỗi nhận định quan trọng phải gắn citation dạng "
            "[1], [2]. Nếu các nguồn mâu thuẫn hoặc chưa đủ, phải nói rõ giới hạn. "
            "Không đưa ra lời khuyên pháp lý cá nhân hóa.\n\n"
            f"CÂU HỎI:\n{question}\n\n"
            "BẰNG CHỨNG:\n"
            + "\n\n".join(evidence_blocks)
        )
        response = self.client.responses.create(
            model=self.chat_model,
            instructions=(
                "Tổng hợp câu trả lời grounded từ context retrieval. "
                "Ưu tiên câu trả lời ngắn, chính xác, có citation."
            ),
            input=prompt,
            max_output_tokens=700,
        )
        answer = response.output_text.strip()
        return {
            "answer": answer,
            "status": "answered",
            "used_count": len(accepted),
            "retrieved_count": len(retrieved),
            "results": serialized,
            "strategy": strategy,
            "threshold": threshold,
            "top_k": top_k,
            "filter": metadata_filter,
            "chat_model": self.chat_model,
            "embedding_model": self.embedding_model,
            "index_status": self._index_status[strategy],
        }

    @staticmethod
    def _serialize_result(
        result: dict[str, Any],
        rank: int,
        threshold: float,
    ) -> dict[str, Any]:
        metadata = result["metadata"]
        return {
            "rank": rank,
            "score": round(float(result["score"]), 6),
            "accepted": float(result["score"]) >= threshold,
            "source": metadata.get("source", "-"),
            "document_number": metadata.get("document_number", "-"),
            "article": metadata.get("article", "-") or "-",
            "citation": metadata.get("citation", "-") or "-",
            "content": result["content"],
        }

    @staticmethod
    def _print_retrieval(
        question: str,
        strategy: str,
        threshold: float,
        metadata_filter: dict[str, Any] | None,
        results: list[dict[str, Any]],
    ) -> None:
        print("\n" + "#" * 96, flush=True)
        print(f"QUERY: {question}", flush=True)
        print(
            f"STRATEGY: {strategy} | THRESHOLD: {threshold:.2f} | "
            f"FILTER: {metadata_filter or 'none'} | TOP K: {len(results)}",
            flush=True,
        )
        for rank, result in enumerate(results, start=1):
            metadata = result["metadata"]
            decision = (
                "PASS" if float(result["score"]) >= threshold else "REJECT"
            )
            print("\n" + "=" * 96, flush=True)
            print(
                f"TOP {rank} | SCORE: {float(result['score']):.6f} | {decision}",
                flush=True,
            )
            print(f"Source: {metadata.get('source', '-')}", flush=True)
            print(
                f"Document: {metadata.get('document_number', '-')}",
                flush=True,
            )
            print(f"Article: {metadata.get('article', '-') or '-'}", flush=True)
            print(f"Citation: {metadata.get('citation', '-') or '-'}", flush=True)
            print("-" * 96, flush=True)
            print(result["content"], flush=True)
        print("\n" + "#" * 96 + "\n", flush=True)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def config(request: web.Request) -> web.Response:
    service: LegalRAGService = request.app["rag_service"]
    return web.json_response(
        {
            "strategies": list(STRATEGIES),
            "default_strategy": "document",
            "default_top_k": 3,
            "default_threshold": 0.55,
            "chat_model": service.chat_model,
            "embedding_model": service.embedding_model,
        }
    )


async def ask(request: web.Request) -> web.Response:
    service: LegalRAGService = request.app["rag_service"]
    try:
        payload = await request.json()
        question = str(payload.get("question", "")).strip()
        strategy = str(payload.get("strategy", "document")).strip()
        top_k = int(payload.get("top_k", 3))
        threshold = float(payload.get("threshold", 0.55))
        document_number = str(payload.get("document_number", "")).strip() or None
        citation = str(payload.get("citation", "")).strip() or None

        if not question:
            raise ValueError("Câu hỏi không được để trống")
        if strategy not in STRATEGIES:
            raise ValueError("Strategy không hợp lệ")
        if not 1 <= top_k <= 8:
            raise ValueError("top_k phải nằm trong khoảng 1-8")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold phải nằm trong khoảng 0-1")

        result = await asyncio.to_thread(
            service.ask,
            question,
            strategy,
            top_k,
            threshold,
            document_number,
            citation,
        )
        return web.json_response(result)
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return web.json_response(
            {"error": "Không thể xử lý yêu cầu. Kiểm tra terminal backend."},
            status=500,
        )


def create_app() -> web.Application:
    app = web.Application(client_max_size=2 * 1024 * 1024)
    app["rag_service"] = LegalRAGService()
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/config", config)
    app.router.add_post("/api/ask", ask)
    app.router.add_get("/", lambda _: web.FileResponse(WEB_DIR / "index.html"))
    app.router.add_static("/assets/", WEB_DIR, show_index=False)
    return app


def main() -> None:
    configure_console_encoding()
    port = int(os.getenv("APP_PORT", "8000"))
    web.run_app(create_app(), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
