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

    def answer(self, question: str, top_k: int = 3, min_score: float | None = None) -> str:
        results = self.store.search(question, top_k=top_k)
        if min_score is not None:
            results = [r for r in results if r["score"] >= min_score]
        if not results:
            # Honest uncertainty beats a confident but ungrounded answer.
            return "I could not find relevant information in the knowledge base to answer this question."
        context = "\n\n".join(r["content"] for r in results)
        prompt = (
            "You are a helpful assistant. Answer the question using only the "
            "context below. If the context is insufficient, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )
        return self.llm_fn(prompt)
