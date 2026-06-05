from __future__ import annotations

import math
import re
from typing import Callable

from .embeddings import _mock_embed


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        respect_boundaries: bool = False,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.respect_boundaries = respect_boundaries

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]
        return self._chunk_plain(text)

    def _chunk_plain(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            hard_end = min(start + self.chunk_size, len(text))
            end = hard_end
            if self.respect_boundaries and hard_end < len(text):
                minimum_end = start + int(self.chunk_size * 0.65)
                for separator in ("\n\n", "\n", ". ", "; ", " "):
                    boundary = text.rfind(separator, minimum_end, hard_end)
                    if boundary >= minimum_end:
                        end = boundary + len(separator)
                        break

            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start = max(start + 1, end - self.overlap)
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?:[ \t]+|\n+)")

    def __init__(
        self,
        max_sentences_per_chunk: int = 3,
        overlap_sentences: int = 0,
    ) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)
        if overlap_sentences < 0 or overlap_sentences >= self.max_sentences_per_chunk:
            raise ValueError(
                "overlap_sentences must satisfy "
                "0 <= overlap_sentences < max_sentences_per_chunk"
            )
        self.overlap_sentences = overlap_sentences

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        sentences = [
            sentence.strip()
            for sentence in self.SENTENCE_BOUNDARY.split(text.strip())
            if sentence.strip()
        ]
        step = self.max_sentences_per_chunk - self.overlap_sentences
        chunks: list[str] = []
        for index in range(0, len(sentences), step):
            group = sentences[index : index + self.max_sentences_per_chunk]
            if index and len(group) <= self.overlap_sentences:
                break
            chunks.append(" ".join(group))
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(
        self,
        separators: list[str] | None = None,
        chunk_size: int = 500,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        return self._split(text.strip(), self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text]
        if not remaining_separators:
            return [
                current_text[index : index + self.chunk_size]
                for index in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]
        if separator == "":
            return [
                current_text[index : index + self.chunk_size]
                for index in range(0, len(current_text), self.chunk_size)
            ]
        if separator not in current_text:
            return self._split(current_text, remaining_separators[1:])

        raw_parts = current_text.split(separator)
        parts = [
            part + (separator if index < len(raw_parts) - 1 else "")
            for index, part in enumerate(raw_parts)
            if part
        ]

        chunks: list[str] = []
        buffer = ""
        for part in parts:
            candidate = buffer + part
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue

            if buffer.strip():
                chunks.append(buffer.strip())
            if len(part) <= self.chunk_size:
                buffer = part
            else:
                chunks.extend(self._split(part.strip(), remaining_separators[1:]))
                buffer = ""

        if buffer.strip():
            chunks.append(buffer.strip())
        return chunks


class SemanticChunker:
    """
    Group adjacent sentences when their embeddings remain semantically similar.

    A real semantic embedding function should be injected for meaningful results.
    The mock embedder remains the default so the class works in classroom setups.
    """

    SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?:[ \t]+|\n+)")

    def __init__(
        self,
        embedding_fn: Callable[[str], list[float]] | None = None,
        similarity_threshold: float = 0.5,
        max_chunk_size: int = 1000,
    ) -> None:
        if not -1.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between -1 and 1")
        if max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be greater than 0")
        self.embedding_fn = embedding_fn or _mock_embed
        self.similarity_threshold = similarity_threshold
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sentences = [
            sentence.strip()
            for sentence in self.SENTENCE_BOUNDARY.split(text.strip())
            if sentence.strip()
        ]
        if not sentences:
            return []

        embed_many = getattr(self.embedding_fn, "embed_many", None)
        if callable(embed_many):
            embeddings = embed_many(sentences)
        else:
            embeddings = [self.embedding_fn(sentence) for sentence in sentences]
        chunks: list[str] = []
        current_sentences = [sentences[0]]

        for index in range(1, len(sentences)):
            sentence = sentences[index]
            candidate = " ".join([*current_sentences, sentence])
            similarity = compute_similarity(embeddings[index - 1], embeddings[index])
            if (
                similarity >= self.similarity_threshold
                and len(candidate) <= self.max_chunk_size
            ):
                current_sentences.append(sentence)
            else:
                chunks.extend(self._enforce_size(" ".join(current_sentences)))
                current_sentences = [sentence]

        chunks.extend(self._enforce_size(" ".join(current_sentences)))
        return chunks

    def _enforce_size(self, text: str) -> list[str]:
        if len(text) <= self.max_chunk_size:
            return [text]
        return RecursiveChunker(chunk_size=self.max_chunk_size).chunk(text)


class LegalDocumentChunker:
    """
    Chunk Vietnamese legal documents by Chương, Mục, and Điều headings.

    Each article is kept as the primary retrieval unit. Current chapter and
    section headings are repeated in article chunks so legal context is not lost.
    Oversized articles are recursively split while preserving that context.
    """

    MARKDOWN_PREFIX = r"(?:#{1,6}\s*)?"
    CHAPTER_RE = re.compile(
        rf"^\s*{MARKDOWN_PREFIX}Chương\s+(?:[IVXLCDM]+(?:\s*[-:]\s*.+)?|\d+)\s*$",
        re.IGNORECASE,
    )
    SECTION_RE = re.compile(
        rf"^\s*{MARKDOWN_PREFIX}Mục\s+(?:[IVXLCDM]+|\d+)(?:[.:\s-].*)?$",
        re.IGNORECASE,
    )
    ARTICLE_RE = re.compile(
        rf"^\s*{MARKDOWN_PREFIX}Điều\s+\d+[A-Za-z]?(?:[.:\s-].*)?$",
        re.IGNORECASE,
    )

    def __init__(self, chunk_size: int = 1500) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        chunks: list[str] = []
        current_chapter = ""
        current_section = ""
        current_article: list[str] = []
        introductory_lines: list[str] = []

        def flush_article() -> None:
            if not current_article:
                return
            article_heading = current_article[0].strip()
            article_body = "\n".join(current_article[1:]).strip()
            chunks.extend(
                self._split_article(
                    article_heading,
                    article_body,
                    [current_chapter, current_section],
                )
            )
            current_article.clear()

        def flush_introductory_lines() -> None:
            if not introductory_lines:
                return
            content = "\n".join(introductory_lines).strip()
            if content:
                chunks.extend(self._split_with_context(content, []))
            introductory_lines.clear()

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()

            if self.CHAPTER_RE.match(stripped):
                flush_article()
                flush_introductory_lines()
                current_chapter = stripped
                current_section = ""
                continue

            if self.SECTION_RE.match(stripped):
                flush_article()
                current_section = stripped
                continue

            if self.ARTICLE_RE.match(stripped):
                flush_article()
                flush_introductory_lines()
                current_article.append(stripped)
                continue

            if current_article:
                current_article.append(line)
            elif stripped:
                introductory_lines.append(line)

        flush_article()
        flush_introductory_lines()
        return chunks

    def _split_with_context(self, content: str, context: list[str]) -> list[str]:
        context_prefix = "\n".join(item for item in context if item).strip()
        if context_prefix and not content.startswith(context_prefix):
            full_text = f"{context_prefix}\n{content}"
        else:
            full_text = content
        if len(full_text) <= self.chunk_size:
            return [full_text]

        available_size = self.chunk_size - len(context_prefix) - 1
        if available_size <= 0:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(full_text)

        parts = RecursiveChunker(chunk_size=available_size).chunk(content)
        return [
            f"{context_prefix}\n{part}".strip() if context_prefix else part
            for part in parts
        ]

    def _split_article(
        self,
        article_heading: str,
        article_body: str,
        context: list[str],
    ) -> list[str]:
        legal_context = [*context, article_heading]
        if not article_body:
            return self._split_with_context(article_heading, context)
        return self._split_with_context(article_body, legal_context)


class DocumentChunker(LegalDocumentChunker):
    """Backward-friendly name for structure-aware Vietnamese legal chunking."""


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    magnitude_a = math.sqrt(_dot(vec_a, vec_a))
    magnitude_b = math.sqrt(_dot(vec_b, vec_b))
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=0),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
            "semantic": SemanticChunker(max_chunk_size=chunk_size),
            "document": DocumentChunker(chunk_size=chunk_size),
        }
        comparison = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            comparison[name] = {
                "count": len(chunks),
                "avg_length": (
                    sum(len(chunk) for chunk in chunks) / len(chunks)
                    if chunks
                    else 0.0
                ),
                "chunks": chunks,
            }
        return comparison
