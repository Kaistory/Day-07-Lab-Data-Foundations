from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k)
        if not results:
            return "Tôi không tìm thấy thông tin phù hợp trong tài liệu."
        
        context_parts = []
        for i, res in enumerate(results):
            content = res.get("content", "")
            context_parts.append(f"[Tài liệu {i+1}]:\n{content}")
            
        context_str = "\n\n".join(context_parts)
        
        prompt = f"""Bạn là một trợ lý ảo trả lời câu hỏi dựa trên ngữ cảnh được cung cấp.
Dựa vào ngữ cảnh sau:
{context_str}

Câu hỏi: {question}
Hãy trả lời một cách chính xác. Nếu không có thông tin, hãy nói không biết."""
        
        return self.llm_fn(prompt)
