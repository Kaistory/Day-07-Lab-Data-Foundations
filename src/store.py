from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb  # noqa: F401

            client = chromadb.Client()
            self._collection = client.get_or_create_collection(self._collection_name)
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": doc.metadata,
            "embedding": self._embedding_fn(doc.content)
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        query_emb = self._embedding_fn(query)
        scored_records = []
        for r in records:
            score = _dot(query_emb, r["embedding"])
            scored_records.append((score, r))
        
        scored_records.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, r in scored_records[:top_k]:
            result = dict(r)
            result["score"] = score
            results.append(result)
        return results

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if self._use_chroma:
            ids = [doc.id for doc in docs]
            documents = [doc.content for doc in docs]
            metadatas = [doc.metadata for doc in docs]
            embeddings = [self._embedding_fn(doc.content) for doc in docs]
            self._collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        else:
            for doc in docs:
                self._store.append(self._make_record(doc))

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if self._use_chroma:
            query_emb = self._embedding_fn(query)
            results = self._collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            output = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    output.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") and results["metadatas"][0] else {},
                        "score": 1.0 - results["distances"][0][i]
                    })
            return output

        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_chroma:
            return self._collection.count()
        return len(self._store)

    def get_all_documents(self) -> list[dict[str, Any]]:
        """Return all stored chunks."""
        if self._use_chroma:
            results = self._collection.get()
            output = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    output.append({
                        "id": results["ids"][i],
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i] if results.get("metadatas") else {}
                    })
            return output
            
        # Dành cho In-Memory Store
        output = []
        for r in self._store:
            output.append({
                "id": r["id"],
                "content": r["content"],
                "metadata": r["metadata"]
            })
        return output

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if self._use_chroma:
            query_emb = self._embedding_fn(query)
            results = self._collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                where=metadata_filter if metadata_filter else None,
                include=["documents", "metadatas", "distances"]
            )
            output = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    output.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") and results["metadatas"][0] else {},
                        "score": 1.0 - results["distances"][0][i]
                    })
            return output

        if not metadata_filter:
            return self.search(query, top_k)
            
        filtered_records = []
        for r in self._store:
            match = True
            for k, v in metadata_filter.items():
                if r["metadata"].get(k) != v:
                    match = False
                    break
            if match:
                filtered_records.append(r)
                
        return self._search_records(query, filtered_records, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        if self._use_chroma:
            initial_count = self._collection.count()
            try:
                self._collection.delete(ids=[doc_id])
            except Exception:
                pass
            try:
                self._collection.delete(where={"doc_id": doc_id})
            except Exception:
                pass
            return self._collection.count() < initial_count

        initial_len = len(self._store)
        self._store = [r for r in self._store if r.get("id") != doc_id and r.get("metadata", {}).get("doc_id") != doc_id]
        return len(self._store) < initial_len
