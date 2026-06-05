"""Quick hands-on demo of every component. Run: python try_demo.py"""
from src import (
    Document, EmbeddingStore, KnowledgeBaseAgent,
    FixedSizeChunker, SentenceChunker, RecursiveChunker,
    ChunkingStrategyComparator, compute_similarity, _mock_embed,
)

line = lambda t: print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)

TEXT = (
    "Python is a high-level language. It is easy to read. "
    "Machine learning needs data. Vector search uses embeddings."
)

# 1) Three chunkers on the same text
line("1) CHUNKERS")
print("Fixed (size=30):", FixedSizeChunker(chunk_size=30, overlap=5).chunk(TEXT))
print("Sentence (2/chunk):", SentenceChunker(2).chunk(TEXT))
print("Recursive (size=40):", RecursiveChunker(chunk_size=40).chunk(TEXT))

# 2) Cosine similarity between sentences
line("2) COSINE SIMILARITY")
pairs = [
    ("I love cats", "I love cats"),
    ("I love cats", "I adore felines"),
    ("I love cats", "The weather is cold"),
]
for a, b in pairs:
    sim = compute_similarity(_mock_embed(a), _mock_embed(b))
    print(f"  {sim:+.3f}  |  '{a}'  vs  '{b}'")

# 3) Comparator
line("3) STRATEGY COMPARATOR")
for name, stats in ChunkingStrategyComparator().compare(TEXT, chunk_size=40).items():
    print(f"  {name:13} count={stats['count']}  avg_len={stats['avg_length']:.1f}")

# 4) EmbeddingStore: add / search / filter / delete
line("4) EMBEDDING STORE")
store = EmbeddingStore("demo", embedding_fn=_mock_embed)
store.add_documents([
    Document("d1", "Python programming tutorial", {"dept": "eng"}),
    Document("d2", "Marketing growth strategy",   {"dept": "biz"}),
    Document("d3", "Ky thuat lap trinh Python",   {"dept": "eng"}),
])
print("  size:", store.get_collection_size())
print("  search('coding'): top1 =", store.search("coding", top_k=1)[0]["content"])
filtered = store.search_with_filter("coding", top_k=5, metadata_filter={"dept": "eng"})
print("  filter dept=eng ->", [r["content"] for r in filtered])
print("  delete d2:", store.delete_document("d2"), "| new size:", store.get_collection_size())

# 5) RAG agent (fake LLM that echoes how many context chunks it got)
line("5) KNOWLEDGE BASE AGENT (RAG)")
def fake_llm(prompt: str) -> str:
    n = prompt.count("\n\n") - 1  # rough chunk count in context
    return f"[answer grounded on retrieved context, {len(prompt)} chars of prompt]"
agent = KnowledgeBaseAgent(store, fake_llm)
print("  Q: How do I code in Python?")
print("  A:", agent.answer("How do I code in Python?"))
