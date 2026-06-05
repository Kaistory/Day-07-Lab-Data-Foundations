from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src import (
    Document,
    DocumentChunker,
    EmbeddingStore,
    FixedSizeChunker,
    OpenAIEmbedder,
    RecursiveChunker,
    SemanticChunker,
    SentenceChunker,
)

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
RESULTS_PATH = DATA_DIR / "legal_benchmark_results.json"
SUMMARY_PATH = DATA_DIR / "legal_benchmark_summary.md"

LAW_FILES = [DATA_DIR / f"luat116_ch{chapter:02d}.md" for chapter in range(1, 9)]
DOCUMENT_FILES = [DATA_DIR / "81-btc.md", *LAW_FILES]

BENCHMARKS = [
    {
        "id": 1,
        "query": "Theo Thông tư 81/2025/TT-BTC, thời điểm COT được quy định vào lúc mấy giờ?",
        "gold_answer": "COT được quy định lúc 16 giờ của ngày làm việc theo giờ Việt Nam.",
        "expected_source": "81-btc",
        "expected_phrases": ["16 giờ"],
        "metadata_filter": {"document_number": "81/2025/TT-BTC"},
    },
    {
        "id": 2,
        "query": "Theo Điều 10 Thông tư 81/2025/TT-BTC, Kho bạc Nhà nước phải hoàn thành chuyển đổi sang mô hình tài khoản thanh toán tập trung chậm nhất khi nào?",
        "gold_answer": "Chậm nhất đến ngày 30 tháng 6 năm 2028.",
        "expected_source": "81-btc",
        "expected_phrases": ["30 tháng 6 năm 2028"],
        "metadata_filter": None,
        "document_metadata_filter": {"citation": "81/2025/TT-BTC:10"},
    },
    {
        "id": 3,
        "query": "Cha mẹ hoặc người giám hộ có trách nhiệm gì khi trẻ em sử dụng dịch vụ giá trị gia tăng trên không gian mạng?",
        "gold_answer": (
            "Cha mẹ hoặc người giám hộ đứng ký tài khoản bằng thông tin của mình "
            "và giám sát, quản lý nội dung trẻ em truy cập, đăng tải, chia sẻ."
        ),
        "expected_source": "luat116_ch03",
        "expected_phrases": ["cha, mẹ hoặc người giám hộ", "giám sát, quản lý nội dung"],
        "metadata_filter": None,
    },
    {
        "id": 4,
        "query": "Luật An ninh mạng số 116/2025 có hiệu lực thi hành từ ngày nào?",
        "gold_answer": "Luật có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026.",
        "expected_source": "luat116_ch08",
        "expected_phrases": ["01 tháng 7 năm 2026"],
        "metadata_filter": None,
    },
    {
        "id": 5,
        "query": "Theo Điều 7 Luật An ninh mạng 116/2025, hành vi xuyên tạc lịch sử và phủ nhận thành tựu cách mạng có bị nghiêm cấm không?",
        "gold_answer": (
            "Có. Đăng tải, phát tán nội dung xuyên tạc lịch sử hoặc phủ nhận "
            "thành tựu cách mạng trên không gian mạng là hành vi bị nghiêm cấm."
        ),
        "expected_source": "luat116_ch01",
        "expected_phrases": ["Xuyên tạc lịch sử", "phủ nhận thành tựu cách mạng"],
        "metadata_filter": None,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare retrieval strategies on Vietnamese legal documents."
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=["fixed", "sentence", "recursive", "semantic", "document"],
        default=["fixed", "sentence", "recursive", "semantic", "document"],
    )
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def document_metadata(path: Path) -> dict[str, Any]:
    if path.name == "81-btc.md":
        return {
            "source": path.name,
            "source_stem": path.stem,
            "title": "Thông tư 81/2025/TT-BTC",
            "document_number": "81/2025/TT-BTC",
            "document_type": "thong_tu",
            "year": 2025,
            "language": "vi",
        }
    return {
        "source": path.name,
        "source_stem": path.stem,
        "title": "Luật An ninh mạng số 116/2025/QH15",
        "document_number": "116/2025/QH15",
        "document_type": "luat",
        "year": 2025,
        "language": "vi",
        "chapter_file": path.stem.removeprefix("luat116_"),
    }


def make_strategies(embedder: OpenAIEmbedder) -> dict[str, Any]:
    return {
        "fixed": FixedSizeChunker(chunk_size=1200, overlap=150),
        "sentence": SentenceChunker(max_sentences_per_chunk=5),
        "recursive": RecursiveChunker(chunk_size=1200),
        "semantic": SemanticChunker(
            embedding_fn=embedder,
            similarity_threshold=0.20,
            max_chunk_size=1500,
        ),
        "document": DocumentChunker(chunk_size=1500),
    }


def collection_name(strategy_name: str, model_name: str) -> str:
    fingerprint = hashlib.sha256()
    fingerprint.update(model_name.encode("utf-8"))
    fingerprint.update(strategy_name.encode("utf-8"))
    fingerprint.update(
        json.dumps(
            strategy_parameters(strategy_name),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    )
    for path in DOCUMENT_FILES:
        fingerprint.update(path.name.encode("utf-8"))
        fingerprint.update(path.read_bytes())
    suffix = fingerprint.hexdigest()[:12]
    safe_model = re.sub(r"[^a-zA-Z0-9_-]+", "-", model_name)
    return f"legal-{strategy_name}-{safe_model}-{suffix}"[:63]


def extract_article(content: str) -> str:
    match = re.search(r"(?im)^#{1,6}\s*(Điều\s+\d+[A-Za-z]?(?:\.[^\n]*)?)", content)
    return match.group(1).strip() if match else ""


def extract_article_number(article: str) -> str:
    match = re.search(r"Điều\s+(\d+[A-Za-z]?)", article, re.IGNORECASE)
    return match.group(1) if match else ""


def has_substantive_content(content: str) -> bool:
    body_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not re.match(r"^#{1,6}\s+", line.strip())
    ]
    return len(" ".join(body_lines)) >= 30


def chunk_documents(chunker: Any, strategy_name: str) -> list[Document]:
    documents: list[Document] = []
    for path in DOCUMENT_FILES:
        text = path.read_text(encoding="utf-8")
        base_metadata = document_metadata(path)
        for index, content in enumerate(chunker.chunk(text)):
            if not has_substantive_content(content):
                continue
            article = extract_article(content)
            article_number = extract_article_number(article)
            metadata = {
                **base_metadata,
                "strategy": strategy_name,
                "chunk_index": index,
                "article": article,
                "article_number": article_number,
            }
            if article_number:
                metadata["citation"] = (
                    f"{base_metadata['document_number']}:{article_number}"
                )
            embedding_context = f"[{base_metadata['title']}]"
            if article:
                embedding_context += f" [{article}]"
            documents.append(
                Document(
                    id=f"{path.stem}-{strategy_name}-{index:04d}",
                    content=f"{embedding_context}\n{content}",
                    metadata=metadata,
                )
            )
    return documents


def is_relevant(result: dict[str, Any], benchmark: dict[str, Any]) -> bool:
    source_matches = result["metadata"].get("source_stem") == benchmark["expected_source"]
    content = result["content"].casefold()
    phrase_matches = all(
        phrase.casefold() in content for phrase in benchmark["expected_phrases"]
    )
    return source_matches and phrase_matches


def evaluate_strategy(
    strategy_name: str,
    chunker: Any,
    embedder: OpenAIEmbedder,
    top_k: int,
) -> dict[str, Any]:
    documents = chunk_documents(chunker, strategy_name)
    store = EmbeddingStore(
        collection_name=collection_name(strategy_name, embedder.model_name),
        embedding_fn=embedder,
    )
    existing_size = store.get_collection_size()
    if existing_size != len(documents):
        if existing_size:
            store.clear()
        store.add_documents(documents)

    query_results = []
    relevant_top3 = 0
    reciprocal_rank_total = 0.0
    for benchmark in BENCHMARKS:
        metadata_filter = benchmark.get("metadata_filter")
        if strategy_name == "document":
            metadata_filter = benchmark.get("document_metadata_filter") or metadata_filter

        if metadata_filter:
            results = store.search_with_filter(
                benchmark["query"],
                top_k=top_k,
                metadata_filter=metadata_filter,
            )
        else:
            results = store.search(benchmark["query"], top_k=top_k)

        relevant_rank = None
        serialized_results = []
        for rank, result in enumerate(results, start=1):
            relevant = is_relevant(result, benchmark)
            if relevant and relevant_rank is None:
                relevant_rank = rank
            serialized_results.append(
                {
                    "rank": rank,
                    "score": round(float(result["score"]), 6),
                    "relevant": relevant,
                    "source": result["metadata"].get("source"),
                    "article": result["metadata"].get("article"),
                    "content_preview": " ".join(result["content"].split())[:300],
                }
            )

        if relevant_rank is not None:
            relevant_top3 += 1
            reciprocal_rank_total += 1.0 / relevant_rank
        query_results.append(
            {
                "id": benchmark["id"],
                "query": benchmark["query"],
                "gold_answer": benchmark["gold_answer"],
                "metadata_filter": metadata_filter,
                "relevant_rank": relevant_rank,
                "results": serialized_results,
            }
        )

    lengths = [len(document.content) for document in documents]
    return {
        "strategy": strategy_name,
        "parameters": strategy_parameters(strategy_name),
        "chunk_count": len(documents),
        "avg_chunk_length": round(sum(lengths) / len(lengths), 2),
        "max_chunk_length": max(lengths),
        "collection_name": collection_name(strategy_name, embedder.model_name),
        "top3_recall": relevant_top3 / len(BENCHMARKS),
        "mrr": round(reciprocal_rank_total / len(BENCHMARKS), 4),
        "retrieval_score": relevant_top3 * 2,
        "queries": query_results,
    }


def strategy_parameters(strategy_name: str) -> dict[str, Any]:
    return {
        "fixed": {"chunk_size": 1200, "overlap": 150},
        "sentence": {"max_sentences_per_chunk": 5},
        "recursive": {"chunk_size": 1200},
        "semantic": {"similarity_threshold": 0.20, "max_chunk_size": 1500},
        "document": {"chunk_size": 1500, "boundaries": ["Chương", "Mục", "Điều"]},
    }[strategy_name]


def write_summary(payload: dict[str, Any]) -> None:
    lines = [
        "# Vietnamese Legal Retrieval Benchmark",
        "",
        f"- Embedding model: `{payload['embedding_model']}`",
        "- Embedding dimensions: `1536` (model default)",
        "- Similarity: cosine",
        f"- Documents: {payload['document_count']}",
        f"- Benchmark queries: {len(BENCHMARKS)}",
        "",
        "| Strategy | Parameters | Chunks | Avg length | Top-3 recall | MRR | Score /10 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in payload["strategies"]:
        parameters = ", ".join(
            f"{key}={value}" for key, value in result["parameters"].items()
        )
        lines.append(
            f"| {result['strategy']} | {parameters} | {result['chunk_count']} | "
            f"{result['avg_chunk_length']} | {result['top3_recall']:.0%} | "
            f"{result['mrr']:.4f} | {result['retrieval_score']} |"
        )

    lines.extend(["", "## Query Results", ""])
    for result in payload["strategies"]:
        lines.append(f"### {result['strategy']}")
        lines.append("")
        lines.append("| # | Relevant rank | Top-1 source | Top-1 score | Top-1 article |")
        lines.append("|---:|---:|---|---:|---|")
        for query in result["queries"]:
            top1 = query["results"][0] if query["results"] else {}
            lines.append(
                f"| {query['id']} | {query['relevant_rank'] or '-'} | "
                f"{top1.get('source', '-')} | {top1.get('score', '-')} | "
                f"{top1.get('article', '-') or '-'} |"
            )
        lines.append("")

    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    args = parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to run the legal benchmark")
    if args.top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    missing_files = [str(path) for path in DOCUMENT_FILES if not path.exists()]
    if missing_files:
        raise FileNotFoundError(f"Missing legal documents: {missing_files}")

    embedder = OpenAIEmbedder(
        model_name=args.model,
        dimensions=None,
        batch_size=100,
    )
    strategies = make_strategies(embedder)
    results = [
        evaluate_strategy(name, strategies[name], embedder, args.top_k)
        for name in args.strategies
    ]
    payload = {
        "embedding_model": args.model,
        "embedding_dimensions": 1536,
        "similarity": "cosine",
        "document_count": len(DOCUMENT_FILES),
        "documents": [document_metadata(path) for path in DOCUMENT_FILES],
        "benchmarks": BENCHMARKS,
        "strategies": results,
    }
    RESULTS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_summary(payload)

    for result in results:
        print(
            f"{result['strategy']}: chunks={result['chunk_count']} "
            f"top3={result['top3_recall']:.0%} "
            f"mrr={result['mrr']:.4f} score={result['retrieval_score']}/10"
        )
    print(f"JSON: data/{RESULTS_PATH.name}")
    print(f"Summary: data/{SUMMARY_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
