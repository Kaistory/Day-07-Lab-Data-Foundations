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

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self(text) for text in texts]


class LocalEmbedder:
    """Sentence Transformers-backed local embedder."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._backend_name = model_name
        self.model = SentenceTransformer(model_name)
        self._cache: dict[str, list[float]] = {}

    def __call__(self, text: str) -> list[float]:
        if text in self._cache:
            return self._cache[text]
        embedding = self.model.encode(text, normalize_embeddings=True)
        vector = embedding.tolist() if hasattr(embedding, "tolist") else [float(v) for v in embedding]
        self._cache[text] = vector
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        missing = [t for t in texts if t not in self._cache]
        if missing:
            encoded = self.model.encode(missing, normalize_embeddings=True)
            for text, vector in zip(missing, encoded):
                self._cache[text] = vector.tolist() if hasattr(vector, "tolist") else [float(v) for v in vector]
        return [self._cache[t] for t in texts]


class OpenAIEmbedder:
    """OpenAI embeddings API-backed embedder."""

    def __init__(self, model_name: str = OPENAI_EMBEDDING_MODEL) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self._backend_name = model_name
        self.client = OpenAI()
        self._cache: dict[str, list[float]] = {}

    def __call__(self, text: str) -> list[float]:
        if text in self._cache:
            return self._cache[text]
        response = self.client.embeddings.create(model=self.model_name, input=text)
        vector = [float(value) for value in response.data[0].embedding]
        self._cache[text] = vector
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # One API call for every uncached text — far cheaper/faster than per-item.
        missing = [t for t in texts if t not in self._cache]
        if missing:
            response = self.client.embeddings.create(model=self.model_name, input=missing)
            for text, item in zip(missing, response.data):
                self._cache[text] = [float(value) for value in item.embedding]
        return [self._cache[t] for t in texts]


_mock_embed = MockEmbedder()
