# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Dương Quang Khải
**Nhóm:** Bàn E2
**Ngày:** 2026-06-05

> Ghi chú: các phần kỹ thuật (số liệu chunking, similarity, benchmark) được đo
> trực tiếp trên package `src` của tôi với embedding `text-embedding-3-small`
> (OpenAI). Các ô đánh dấu **[điền cùng nhóm]** cần thống nhất với thành viên.

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> Hai chunk có embedding chỉ gần như **cùng hướng** trong không gian vector, nghĩa là chúng mang ý nghĩa rất gần nhau — bất kể độ dài văn bản. Cosine đo góc giữa hai vector, không đo khoảng cách độ lớn.

**Ví dụ HIGH similarity:**
- Sentence A: "A vector store keeps embeddings for similarity search"
- Sentence B: "A database that stores vectors to retrieve similar items"
- Tại sao tương đồng: cùng nói về một khái niệm (lưu vector để tìm kiếm tương tự), chỉ khác cách diễn đạt. Đo thật: **+0.738**.

**Ví dụ LOW similarity:**
- Sentence A: "Python is great for machine learning"
- Sentence B: "Customers were charged twice on their billing statement"
- Tại sao khác: hai chủ đề hoàn toàn rời nhau (ngôn ngữ lập trình vs lỗi thanh toán). Đo thật: **−0.051**.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Vì độ dài văn bản làm vector dài/ngắn khác nhau, nhưng **hướng** mới mang ngữ nghĩa. Cosine chuẩn hóa theo độ lớn nên một câu và bản lặp lại của nó vẫn được coi là giống nhau; Euclidean sẽ bị độ lớn vector làm sai lệch.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> `num_chunks = ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11) = `**23 chunks**.

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> `num_chunks = ceil((10000 − 100) / (500 − 100)) = ceil(9900 / 400) = ceil(24.75) = `**25 chunks** → overlap lớn hơn ⇒ bước trượt nhỏ hơn ⇒ **nhiều chunk hơn**. Muốn overlap nhiều hơn để **không cắt đứt ý ở ranh giới chunk**: một câu/ý nằm vắt qua điểm cắt sẽ xuất hiện trọn vẹn trong ít nhất một chunk, tránh mất thông tin khi retrieve (đánh đổi: tốn thêm bộ nhớ/embedding).

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Internal Knowledge Assistant / RAG documentation (tài liệu kỹ thuật nội bộ về embedding, vector store, chunking, support).

**Tại sao nhóm chọn domain này?**
> Bộ tài liệu nói về chính chủ đề của lab (retrieval, chunking, metadata), nên gold answer dễ verify và cho phép thiết kế query đa dạng (định nghĩa, so sánh, quy trình). Có thêm 1 tài liệu **tiếng Việt** để thử metadata filter theo ngôn ngữ.
> *(Nếu nhóm đổi sang domain khác — FAQ, luật, recipe — cập nhật lại bảng bên dưới.)*

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | python_intro.txt | data/ | 1944 | source, doc_id, lang=en |
| 2 | vector_store_notes.md | data/ | 2123 | source, doc_id, lang=en |
| 3 | rag_system_design.md | data/ | 2391 | source, doc_id, lang=en |
| 4 | customer_support_playbook.txt | data/ | 1692 | source, doc_id, lang=en |
| 5 | chunking_experiment_report.md | data/ | 1987 | source, doc_id, lang=en |
| 6 | vi_retrieval_notes.md | data/ | 1667 | source, doc_id, **lang=vi** |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `source` | str | `vector_store_notes.md` | Truy vết chunk về đúng file gốc (grounding/audit) |
| `doc_id` | str | `vector_store_notes` | Gom & xóa toàn bộ chunk của 1 tài liệu (`delete_document`) |
| `lang` | str | `en` / `vi` | Lọc theo ngôn ngữ — tránh trả nhầm tài liệu khác ngôn ngữ |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare(text, chunk_size=300)` (số liệu thật):

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| vector_store_notes.md | `fixed_size` | 8 | 265.4 | Trung bình — cắt cứng theo ký tự, có thể cắt giữa câu |
| vector_store_notes.md | `by_sentences` | 8 | 263.6 | Tốt — theo ranh giới câu, nhưng độ dài không đều |
| vector_store_notes.md | `recursive` | 12 | 175.1 | Tốt nhất — tách theo đoạn rồi gộp lại gần chunk_size |
| python_intro.txt | `fixed_size` | 7 | 277.7 | Trung bình |
| python_intro.txt | `by_sentences` | 5 | 387.0 | Câu dài → chunk to, dễ vượt ngưỡng lý tưởng |
| python_intro.txt | `recursive` | 11 | 174.8 | Tốt nhất — chunk đều, bám cấu trúc, giữ ngữ cảnh |

#### Cải tiến `RecursiveChunker`: gộp mẩu nhỏ (before/after)

Phiên bản đầu tách xong là giữ luôn từng mẩu → nhiều chunk vụn, chỉ dùng ~45% `chunk_size`. Tôi sửa `_split` để **gộp các mẩu liên tiếp** tới gần `chunk_size` trước khi cắt:

| Tài liệu (chunk_size=300) | Chunk count | Avg length |
|---|---|---|
| vector_store_notes.md — *before* | 15 | 139.7 |
| vector_store_notes.md — **after** | **12** | **175.1** |
| python_intro.txt — *before* | 15 | 127.7 |
| python_intro.txt — **after** | **11** | **174.8** |

→ chunk đầy đặn hơn (~128 → ~175 ký tự), ít vector hơn (giảm ~20-27%), giữ ngữ cảnh tốt hơn mà vẫn trong giới hạn size. 42/42 test vẫn pass.

### Strategy Của Tôi

**Loại:** `RecursiveChunker` (chunk_size=300)

**Mô tả cách hoạt động:**
> Thử lần lượt các separator theo thứ tự ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Nếu một đoạn vẫn lớn hơn `chunk_size`, đệ quy xuống separator mịn hơn; khi hết separator thì cắt cứng theo kích thước. Nhờ vậy chunk ưu tiên giữ trọn đoạn/câu, chỉ cắt nhỏ khi thật sự cần.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Tài liệu nhóm là markdown/kỹ thuật có cấu trúc đoạn rõ ràng (`\n\n`). Recursive khai thác đúng cấu trúc đó để tạo chunk vừa gọn vừa giữ ngữ cảnh — đúng như kết luận trong `chunking_experiment_report.md`.

### So Sánh: Strategy của tôi vs Baseline (whole-doc)

Cùng query *"How does metadata filtering improve retrieval precision?"*, cùng data, cùng embedder:

| Cách lưu | Số vector | Top-1 score | Top-1 trả về |
|-----------|-----------|-------------|--------------|
| Whole document (không chunk) | 6 | 0.405 | Cả file `vector_store_notes.md` (mờ) |
| **RecursiveChunker(300)** | 94 | **0.694** | Đúng câu *"When a user asks... metadata filters can narrow the search space..."* |

> Chunking nâng top-1 score từ 0.405 → 0.694 và trỏ đúng **đoạn văn** thay vì cả file. Lý do: tài liệu ~2000 ký tự nếu nén thành 1 vector sẽ bị pha loãng nhiều ý; chia nhỏ giúp mỗi vector tập trung 1 ý → khớp query chính xác hơn.

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | RecursiveChunker(300) | [điền] | Giữ ngữ cảnh, chunk đều | Cần tune chunk_size |
| [Tên] | [điền cùng nhóm] | | | |
| [Tên] | [điền cùng nhóm] | | | |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> [điền sau khi so sánh cùng nhóm — gợi ý dựa trên baseline: recursive là default mạnh cho tài liệu có cấu trúc đoạn]

---

## 4. My Approach — Cá nhân (10 điểm)

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Tách câu bằng regex `(?<=[.!?])\s+` — lookbehind giữ dấu câu dính vào cuối câu, chỉ dùng khoảng trắng phía sau làm điểm cắt (xử lý cả `". "` và `".\n"`). Sau đó gom `max_sentences_per_chunk` câu/chunk. Edge case: text rỗng/toàn khoảng trắng → `[]`; lọc bỏ phần tử rỗng bằng `if s.strip()`.

**`RecursiveChunker.chunk` / `_split`** — approach:
> `_split` là đệ quy: **base case** là đoạn ≤ `chunk_size` (trả về nguyên đoạn), hoặc hết separator / gặp separator rỗng → cắt cứng theo kích thước. Ngược lại tách theo separator hiện tại, đoạn nào vẫn quá dài thì đệ quy với separator mịn hơn.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> `add_documents` gọi `_make_record` để embed `doc.content` và đóng gói (id, doc_id, content, embedding, metadata) rồi append vào `self._store`. `search` embed query, tính `_dot(query_emb, rec_emb)` cho mọi record (embedding đã chuẩn hóa nên dot product = cosine), sort giảm dần, lấy `top_k`.

**`search_with_filter` + `delete_document`** — approach:
> Filter **trước** rồi search sau: lọc record có `metadata` khớp tất cả cặp key-value, rồi chạy `_search_records` trên tập đã lọc (giảm nhiễu). `delete_document` lọc ra mọi record có `metadata['doc_id'] == doc_id`; nếu không có thì trả `False`, có thì gán lại `self._store` bỏ các record đó và trả `True`.

### KnowledgeBaseAgent

**`answer`** — approach:
> RAG 3 bước: (1) `store.search(question, top_k)` lấy chunk liên quan; (2) ghép `content` các chunk thành `Context` và dựng prompt yêu cầu LLM "chỉ trả lời từ context, thiếu thì nói thiếu"; (3) gọi `llm_fn(prompt)`. `llm_fn` được inject nên dễ test (hàm giả) hoặc cắm OpenAI thật.

### Cải Tiến Thêm (ngoài yêu cầu cơ bản)

Sau khi pass hết test, tôi nâng cấp thêm 5 điểm (vẫn giữ 42/42 test):

| # | Cải tiến | Tác động đo được |
|---|----------|------------------|
| 1 | `RecursiveChunker` gộp mẩu nhỏ tới gần `chunk_size` | 15→11-12 chunk, avg_len 128→175 (xem Section 3) |
| 2 | `search` xếp hạng bằng **cosine chuẩn** (`compute_similarity`) thay vì dot thô | Không còn giả định vector đã normalize |
| 3 | `agent.answer` xử lý **retrieval rỗng/yếu** + tham số `min_score` | Trả "không tìm thấy" thay vì bịa (honest uncertainty) |
| 4 | **Batch embedding** (`embed_batch`) | 20 docs → 1 API request thay vì 20 |
| 5 | **Cache embedding** theo nội dung (OpenAI/Local) | Text trùng → 0 API call lần sau |

### Test Results

```
$ pytest tests/ -q
..........................................                               [100%]
42 passed in 0.08s
```

**Số tests pass:** **42 / 42**

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

Đo thật bằng `compute_similarity()` + embedding OpenAI:

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "A vector store keeps embeddings for similarity search" | "A database that stores vectors to retrieve similar items" | high | **+0.738** | ✓ |
| 2 | "Recursive chunking preserves context" | "Recursive chunking splits on paragraphs first, then smaller separators" | high | **+0.639** | ✓ |
| 3 | "Python is great for machine learning" | "Customers were charged twice on their billing statement" | low | **−0.051** | ✓ |
| 4 | "How do I recover my password?" | "Steps to reset account credentials" | high | **+0.528** | ~ (thấp hơn dự đoán) |
| 5 | "The weather in Hanoi is hot today" | "Embeddings encode semantic meaning of text" | low | **+0.020** | ✓ |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Bất ngờ nhất là **Pair 4 (0.528)**: hai câu cùng *ý định* (khôi phục/đặt lại mật khẩu) nhưng score chỉ ở mức trung bình, vì gần như không trùng từ vựng và một câu là câu hỏi, một câu là mô tả thao tác. Điều này cho thấy embedding bắt được ngữ nghĩa nhưng vẫn nhạy với cách diễn đạt/cấu trúc câu — cùng ý chưa chắc cho score rất cao nếu từ ngữ khác hẳn. Ngược lại Pair 3 ra số **âm**, xác nhận hai chủ đề thực sự không liên quan.

---

## 6. Results — Cá nhân (10 điểm)

> Chạy 5 benchmark queries trên package `src` (RecursiveChunker 300, embedding OpenAI, **71 chunks** sau cải tiến merge). Query #5 dùng **metadata filter `lang=vi`**.
> ⚠️ 5 queries dưới đây cần **thống nhất với nhóm** — hiện là bản nháp của tôi.

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | What are the four stages of a typical vector search pipeline? | Chunk documents → embed each chunk → store vector+metadata → embed query & rank by similarity |
| 2 | Which chunking strategy gave the best balance and why? | Recursive chunking — tách theo cấu trúc lớn trước rồi mới nhỏ hơn, giữ ngữ cảnh trong giới hạn size |
| 3 | What should a support assistant do when no document explains an issue? | Khuyến nghị escalation thay vì bịa câu trả lời rủi ro |
| 4 | How does metadata filtering improve retrieval precision? | Thu hẹp không gian tìm kiếm, tránh trả tài liệu sai phòng ban/lỗi thời |
| 5 | Tại sao chunk quá dài làm giảm độ chính xác? *(filter lang=vi)* | Nhiều ý không liên quan bị gộp lại → làm loãng độ chính xác kết quả |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score (before→after) | Relevant? | Nguồn |
|---|-------|--------------------------------|-------|-----------|-------|
| 1 | (xem trên) | "A common vector search pipeline has four stages: ..." | 0.903 → **0.838** | ✓ | vector_store_notes.md |
| 2 | (xem trên) | "Recursive chunking offered the best balance in the experiment..." | 0.729 → **0.721** | ✓ | chunking_experiment_report.md |
| 3 | (xem trên) | "A high-quality support assistant should recognize when retrieval is insufficient..." | 0.565 → **0.659** | ✓ | customer_support_playbook.txt |
| 4 | (xem trên) | "When a user asks... metadata filters can narrow the search space..." | 0.694 → **0.693** | ✓ | vector_store_notes.md |
| 5 | (filter vi) | "Nếu chunk quá dài, nhiều ý không liên quan sẽ bị gộp lại, làm giảm độ chính xác..." | 0.670 → **0.644** | ✓ | vi_retrieval_notes.md |

> *before* = RecursiveChunker chưa merge (94 chunk); *after* = đã merge mẩu nhỏ (71 chunk). Đánh đổi rõ rệt: Q3 **tăng mạnh** (0.565→0.659) vì chunk được merge mang thêm ngữ cảnh liên quan; các query "pinpoint" như Q1/Q5 **giảm nhẹ** vì chunk lớn hơn pha loãng một chút similarity đỉnh. Số vector giảm 94→71 ⇒ rẻ & nhanh hơn. Đây đúng là đánh đổi chunk-size mà tài liệu mô tả ("too small lose context, too large dilute").

**Bao nhiêu queries trả về chunk relevant trong top-3?** **5 / 5** (cả before lẫn after)

---

## 7. What I Learned (5 điểm — Demo)

### Failure Analysis (Ex 3.5)

**Failure case quan sát được:** Khi lưu **nguyên tài liệu không chunk** (như `main.py` mặc định), query *"How does metadata filtering improve retrieval precision?"* chỉ đạt top-1 = **0.405** và trỏ vào cả file — score thấp, không tách bạch được đoạn liên quan với phần còn lại.

- **Query nào thất bại:** các query hỏi về 1 ý cụ thể trong tài liệu dài.
- **Tại sao:** chunk quá lớn (cả tài liệu ~2000 ký tự = 1 vector) → nhiều ý bị nén chung, embedding bị pha loãng (đúng cảnh báo trong `vector_store_notes.md`: *"chunks too large... dilute semantic relevance"*). Đây là vấn đề **chunk coherence** + **retrieval precision**.
- **Đề xuất cải thiện:** bật chunking (RecursiveChunker 300) → top-1 cùng query tăng lên **0.694** và trỏ đúng câu. Ngoài ra `SentenceChunker` còn điểm yếu: regex tách câu nhầm ở viết tắt (`v.v.`, `Dr.`) → có thể bổ sung danh sách ngoại lệ.

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> [điền cùng nhóm — sau buổi so sánh]

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> [điền sau demo]

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> [điền — gợi ý: tune chunk_size theo độ dài tài liệu, thêm metadata `section`/`date`, xử lý viết tắt cho SentenceChunker]

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | / 5 |
| Document selection | Nhóm | / 10 |
| Chunking strategy | Nhóm | / 15 |
| My approach | Cá nhân | / 10 |
| Similarity predictions | Cá nhân | / 5 |
| Results | Cá nhân | / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 (42/42 tests pass) |
| Demo | Nhóm | / 5 |
| **Tổng** | | **/ 100** |
