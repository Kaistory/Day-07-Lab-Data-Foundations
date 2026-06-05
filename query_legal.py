from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from benchmark_legal import (
    ROOT,
    chunk_documents,
    collection_name,
    make_strategies,
)
from src import EmbeddingStore, OpenAIEmbedder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query Vietnamese legal documents and inspect top-k chunks."
    )
    parser.add_argument("query", help="Question or text used for semantic search")
    parser.add_argument(
        "--strategy",
        choices=["fixed", "sentence", "recursive", "semantic", "document"],
        default="document",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--document-number",
        help="Optional metadata filter, for example 81/2025/TT-BTC",
    )
    parser.add_argument(
        "--citation",
        help="Optional exact citation filter, for example 81/2025/TT-BTC:10",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env", override=False)
    args = parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required")
    if args.top_k <= 0:
        raise ValueError("top-k must be greater than 0")

    embedder = OpenAIEmbedder(
        model_name=args.model,
        dimensions=None,
        batch_size=100,
    )
    chunker = make_strategies(embedder)[args.strategy]
    documents = chunk_documents(chunker, args.strategy)

    store = EmbeddingStore(
        collection_name=collection_name(args.strategy, args.model),
        embedding_fn=embedder,
    )
    existing_size = store.get_collection_size()
    if existing_size == len(documents):
        index_status = f"reused {existing_size} persisted chunks"
    else:
        if existing_size:
            store.clear()
        store.add_documents(documents)
        index_status = f"indexed and persisted {len(documents)} chunks"

    metadata_filter = None
    if args.citation:
        metadata_filter = {"citation": args.citation}
    elif args.document_number:
        metadata_filter = {"document_number": args.document_number}

    if metadata_filter:
        results = store.search_with_filter(
            args.query,
            top_k=args.top_k,
            metadata_filter=metadata_filter,
        )
    else:
        results = store.search(args.query, top_k=args.top_k)

    print(f"Query: {args.query}")
    print(f"Strategy: {args.strategy}")
    print(f"Model: {args.model}")
    print(f"Collection: {collection_name(args.strategy, args.model)}")
    print(f"Index: {index_status}")
    print(f"Filter: {metadata_filter or 'none'}")
    print(f"Results: {len(results)}")

    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]
        print("\n" + "=" * 80)
        print(f"TOP {rank} | SCORE: {result['score']:.6f}")
        print(f"Source: {metadata.get('source', '-')}")
        print(f"Document: {metadata.get('document_number', '-')}")
        print(f"Article: {metadata.get('article', '-') or '-'}")
        print(f"Citation: {metadata.get('citation', '-') or '-'}")
        print("-" * 80)
        print(result["content"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
