from __future__ import annotations

import hashlib
import math

LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_PROVIDER_ENV = "EMBEDDING_PROVIDER"


class MockEmbedder:
    """Deterministic embedding backend used by tests and default classroom runs."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self._backend_name = "mock embeddings fallback"

    def __call__(self, text: str) -> list[float]:
        digest = hashlib.md5(text.encode()).hexdigest()
        seed = int(digest, 16)
        vector = []
        for _ in range(self.dim):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            vector.append((seed / 0xFFFFFFFF) * 2 - 1)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self(text) for text in texts]


class LocalEmbedder:
    """Sentence Transformers-backed local embedder."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._backend_name = model_name
        self.model = SentenceTransformer(model_name)

    def __call__(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return [float(value) for value in embedding]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return [[float(value) for value in embedding] for embedding in embeddings]


class OpenAIEmbedder:
    """OpenAI embeddings API-backed embedder."""

    def __init__(
        self,
        model_name: str = OPENAI_EMBEDDING_MODEL,
        dimensions: int | None = None,
        batch_size: int = 100,
    ) -> None:
        from openai import OpenAI

        if dimensions is not None and dimensions <= 0:
            raise ValueError("dimensions must be greater than 0")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size
        self._backend_name = model_name
        self.client = OpenAI()
        self._cache: dict[str, list[float]] = {}

    def __call__(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("embedding input cannot be empty")

        missing = list(dict.fromkeys(text for text in texts if text not in self._cache))
        for start in range(0, len(missing), self.batch_size):
            batch = missing[start : start + self.batch_size]
            request = {
                "model": self.model_name,
                "input": batch,
                "encoding_format": "float",
            }
            if self.dimensions is not None:
                request["dimensions"] = self.dimensions
            response = self.client.embeddings.create(**request)
            ordered = sorted(response.data, key=lambda item: item.index)
            for text, item in zip(batch, ordered):
                self._cache[text] = [float(value) for value in item.embedding]

        return [self._cache[text] for text in texts]


_mock_embed = MockEmbedder()
