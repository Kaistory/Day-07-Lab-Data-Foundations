from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Callable

from .chunking import compute_similarity
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
        self._client = None
        self._next_index = 0

        try:
            import chromadb

            persist_dir = os.getenv("CHROMA_PERSIST_DIR", "").strip()
            if persist_dir:
                resolved_dir = Path(persist_dir).expanduser().resolve()
                resolved_dir.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(path=str(resolved_dir))
                self._collection = self._client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                self._client = chromadb.EphemeralClient()
                physical_name = f"{collection_name}-{uuid.uuid4().hex}"
                self._collection = self._client.create_collection(
                    name=physical_name,
                    metadata={"hnsw:space": "cosine"},
                )
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(
        self,
        doc: Document,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        metadata = dict(doc.metadata)
        metadata["doc_id"] = doc.id
        record = {
            "id": f"{doc.id}-{self._next_index}",
            "content": doc.content,
            "metadata": metadata,
            "embedding": embedding if embedding is not None else self._embedding_fn(doc.content),
        }
        self._next_index += 1
        return record

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if top_k <= 0 or not records:
            return []

        query_embedding = self._embedding_fn(query)
        results = [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": dict(record["metadata"]),
                "score": compute_similarity(query_embedding, record["embedding"]),
            }
            for record in records
        ]
        results.sort(key=lambda result: result["score"], reverse=True)
        return results[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        embed_many = getattr(self._embedding_fn, "embed_many", None)
        if callable(embed_many):
            embeddings = embed_many([doc.content for doc in docs])
            records = [
                self._make_record(doc, embedding)
                for doc, embedding in zip(docs, embeddings)
            ]
        else:
            records = [self._make_record(doc) for doc in docs]
        if not records:
            return

        if self._use_chroma and self._collection is not None:
            self._collection.add(
                ids=[record["id"] for record in records],
                documents=[record["content"] for record in records],
                embeddings=[record["embedding"] for record in records],
                metadatas=[record["metadata"] for record in records],
            )
            return
        self._store.extend(records)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if top_k <= 0:
            return []
        if not self._use_chroma or self._collection is None:
            return self._search_records(query, self._store, top_k)

        size = self.get_collection_size()
        if size == 0:
            return []
        raw = self._collection.query(
            query_embeddings=[self._embedding_fn(query)],
            n_results=min(top_k, size),
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "id": raw["ids"][0][index],
                "content": raw["documents"][0][index],
                "metadata": raw["metadatas"][0][index] or {},
                "score": 1.0 - raw["distances"][0][index],
            }
            for index in range(len(raw["ids"][0]))
        ]

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_chroma and self._collection is not None:
            return self._collection.count()
        return len(self._store)

    def clear(self) -> None:
        """Remove every record from the current collection."""
        if self._use_chroma and self._collection is not None:
            existing = self._collection.get()
            if existing["ids"]:
                self._collection.delete(ids=existing["ids"])
            self._next_index = 0
            return
        self._store.clear()
        self._next_index = 0

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k=top_k)
        if top_k <= 0:
            return []

        if not self._use_chroma or self._collection is None:
            filtered = [
                record
                for record in self._store
                if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
            ]
            return self._search_records(query, filtered, top_k)

        raw = self._collection.get(
            where=metadata_filter,
            include=["documents", "metadatas", "embeddings"],
        )
        records = [
            {
                "id": raw["ids"][index],
                "content": raw["documents"][index],
                "metadata": raw["metadatas"][index] or {},
                "embedding": raw["embeddings"][index],
            }
            for index in range(len(raw["ids"]))
        ]
        return self._search_records(query, records, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        if self._use_chroma and self._collection is not None:
            matching = self._collection.get(where={"doc_id": doc_id})
            if not matching["ids"]:
                return False
            self._collection.delete(ids=matching["ids"])
            return True

        original_size = len(self._store)
        self._store = [
            record for record in self._store if record["metadata"].get("doc_id") != doc_id
        ]
        return len(self._store) < original_size
