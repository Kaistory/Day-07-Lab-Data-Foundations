from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent import KnowledgeBaseAgent
from src.chunking import RecursiveChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

SAMPLE_FILES = [
    "data/python_intro.txt",
    "data/vector_store_notes.md",
    "data/rag_system_design.md",
    "data/customer_support_playbook.txt",
    "data/chunking_experiment_report.md",
    "data/vi_retrieval_notes.md",
]


def load_documents_from_files(file_paths: list[str]) -> list[Document]:
    """Load documents from file paths for the manual demo."""
    allowed_extensions = {".md", ".txt"}
    documents: list[Document] = []

    for raw_path in file_paths:
        path = Path(raw_path)

        if path.suffix.lower() not in allowed_extensions:
            print(f"Skipping unsupported file type: {path} (allowed: .md, .txt)")
            continue

        if not path.exists() or not path.is_file():
            print(f"Skipping missing file: {path}")
            continue

        content = path.read_text(encoding="utf-8")
        documents.append(
            Document(
                id=path.stem,
                content=content,
                metadata={"source": str(path), "extension": path.suffix.lower()},
            )
        )

    return documents


def chunk_documents(docs: list[Document], chunk_size: int) -> list[Document]:
    """Split each document into smaller chunk-documents using RecursiveChunker.

    Every chunk inherits the parent's metadata plus a stable doc_id/chunk_index,
    so EmbeddingStore can still group and delete by the original document.
    """
    chunker = RecursiveChunker(chunk_size=chunk_size)
    chunked: list[Document] = []
    for doc in docs:
        pieces = chunker.chunk(doc.content)
        for index, piece in enumerate(pieces):
            chunked.append(
                Document(
                    id=f"{doc.id}#{index}",
                    content=piece,
                    metadata={**doc.metadata, "doc_id": doc.id, "chunk_index": index},
                )
            )
    return chunked


def demo_llm(prompt: str) -> str:
    """A simple mock LLM for manual RAG testing."""
    preview = prompt[:400].replace("\n", " ")
    return f"[DEMO LLM] Generated answer from prompt preview: {preview}..."


def make_openai_llm(model_name: str):
    """Return an llm_fn backed by the real OpenAI Chat Completions API."""
    from openai import OpenAI

    client = OpenAI()

    def openai_llm(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    return openai_llm


def run_manual_demo(
    question: str | None = None,
    sample_files: list[str] | None = None,
    chunk_size: int | None = None,
) -> int:
    files = sample_files or SAMPLE_FILES
    query = question or "Summarize the key information from the loaded files."

    print("=== Manual File Test ===")
    print("Accepted file types: .md, .txt")
    print("Input file list:")
    for file_path in files:
        print(f"  - {file_path}")

    docs = load_documents_from_files(files)
    if not docs:
        print("\nNo valid input files were loaded.")
        print("Create files matching the sample paths above, then rerun:")
        print("  python3 main.py")
        return 1

    print(f"\nLoaded {len(docs)} documents")
    for doc in docs:
        print(f"  - {doc.id}: {doc.metadata['source']}")

    if chunk_size:
        docs = chunk_documents(docs, chunk_size)
        print(f"\nChunked into {len(docs)} chunks (RecursiveChunker, chunk_size={chunk_size})")

    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "openai":
        try:
            embedder = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    else:
        embedder = _mock_embed

    print(f"\nEmbedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")

    store = EmbeddingStore(collection_name="manual_test_store", embedding_fn=embedder)
    store.add_documents(docs)

    print(f"\nStored {store.get_collection_size()} documents in EmbeddingStore")
    print("\n=== EmbeddingStore Search Test ===")
    print(f"Query: {query}")
    search_results = store.search(query, top_k=3)
    for index, result in enumerate(search_results, start=1):
        print(f"{index}. score={result['score']:.3f} source={result['metadata'].get('source')}")
        print(f"   content preview: {result['content'][:120].replace(chr(10), ' ')}...")

    print("\n=== KnowledgeBaseAgent Test ===")
    if provider == "openai":
        try:
            llm_fn = make_openai_llm(os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"))
            print(f"LLM backend: OpenAI {os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')}")
        except Exception as exc:
            llm_fn = demo_llm
            print(f"LLM backend: demo (OpenAI unavailable: {exc})")
    else:
        llm_fn = demo_llm
        print("LLM backend: demo (set EMBEDDING_PROVIDER=openai for real answers)")

    agent = KnowledgeBaseAgent(store=store, llm_fn=llm_fn)
    print(f"Question: {query}")
    print("Agent answer:")
    print(agent.answer(query, top_k=3))
    return 0


def main() -> int:
    # Windows consoles default to cp1252 and choke on non-Latin text (e.g. Vietnamese).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    # Parse flags: --chunk (enable chunking) and --chunk-size N (default 300).
    args = sys.argv[1:]
    chunk_size: int | None = None
    rest: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--chunk":
            chunk_size = chunk_size or 300
        elif arg == "--chunk-size":
            i += 1
            chunk_size = int(args[i]) if i < len(args) else 300
        else:
            rest.append(arg)
        i += 1

    question = " ".join(rest).strip() or None
    return run_manual_demo(question=question, chunk_size=chunk_size)


if __name__ == "__main__":
    raise SystemExit(main())
