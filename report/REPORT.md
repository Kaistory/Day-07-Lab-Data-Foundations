# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** [Vũ Xuân Bách]
**Nhóm:** [Tên nhóm]
**Ngày:** [5/6/2026]

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> *Viết 1-2 câu: (chỉ số tiến gần về 1) đơn giản là hai đoạn văn bản có ngữ nghĩa cực kỳ giống nhau, bất kể chúng được viết bằng những từ vựng khác biệt. Trong hệ thống RAG, tài liệu nào đạt chỉ số này càng cao so với câu hỏi thì sẽ càng được AI ưu tiên trích xuất để làm câu trả lời cho người dùng.*

**Ví dụ HIGH similarity:**
- Sentence A: "Giá nhà đất tại thành phố đang tăng mạnh."
- Sentence B: "Bất động sản khu vực đô thị có xu hướng leo thang."
- Tại sao tương đồng: Hai câu đều truyền đạt chung một thông điệp về sự tăng giá của nhà cửa ở thành thị, dù sử dụng các từ vựng hoàn toàn khác nhau.

**Ví dụ LOW similarity:**
- Sentence A: "Giá nhà đất tại thành phố đang tăng mạnh."
- Sentence B: "Đàn mèo con đang ngủ say trên ghế sofa."
- Tại sao khác: Nội dung hai câu hoàn toàn không liên quan đến nhau, một câu nói về chủ đề kinh tế thị trường, câu còn lại mô tả về động vật.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> *Viết 1-2 câu: Cosine similarity được ưu tiên vì nó chỉ đo lường góc (hướng) giữa hai vector, giúp loại bỏ hoàn toàn sự ảnh hưởng của độ dài văn bản (magnitude). Nhờ vậy, AI có thể nhận diện hai câu có cùng ngữ nghĩa là tương đồng ngay cả khi tần suất xuất hiện từ vựng hoặc độ dài văn bản của chúng chênh lệch nhau rất lớn.*

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính: Gọi $L$ là tổng số ký tự ($10000$), $C$ là kích thước chunk ($500$), và $O$ là phần gối lên nhau ($50$).Mỗi chunk (sau chunk đầu tiên) sẽ tiến thêm một bước là $C-O=450$ ký tự.Công thức tính tổng số chunks:$$\text{Total Chunks}=\left\lceil\frac{L-O}{C-O}\right\rceil$$Áp dụng số liệu:$$\text{Total Chunks}=\left\lceil\frac{10000-50}{500-50}\right\rceil=\left\lceil\frac{9950}{450}\right\rceil=\lceil22.11\rceil=23$$*
> *Đáp án: 23*

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> *Viết 1-2 câu: Nếu overlap tăng lên 100 (bước tiến giảm xuống còn 400), số lượng chunk sẽ tăng thêm 2, đạt mức tổng cộng 25 chunks ($\left\lceil\frac{9900}{400}\right\rceil$). Việc tăng overlap được sử dụng nhằm duy trì bối cảnh ngữ nghĩa (context) an toàn ở các điểm cắt, đảm bảo một câu văn hoặc một khái niệm quan trọng không bị đứt gãy giữa chừng làm LLM mất phương hướng khi truy xuất.*

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Pháp luật Việt Nam

**Tại sao nhóm chọn domain này?**
> Văn bản pháp luật có cấu trúc rõ theo Chương, Mục, Điều và chứa nhiều mốc thời gian, trách nhiệm, điều kiện cần truy xuất chính xác. Bộ dữ liệu này phù hợp để so sánh chunking theo kích thước với chunking nhận biết cấu trúc, đồng thời đánh giá tác dụng của metadata như số văn bản và trích dẫn Điều.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | Thông tư 81/2025/TT-BTC | `data/81-btc.md`, chuyển từ PDF nhóm cung cấp | 15.803 | `document_number`, `document_type`, `year`, `language`, `source` |
| 2 | Luật An ninh mạng 116/2025 — Chương I | `data/luat116_ch01.md` | 12.234 | Như trên + `chapter_file` |
| 3 | Luật An ninh mạng 116/2025 — Chương II | `data/luat116_ch02.md` | 9.023 | Như trên + `chapter_file` |
| 4 | Luật An ninh mạng 116/2025 — Chương III | `data/luat116_ch03.md` | 15.783 | Như trên + `chapter_file` |
| 5 | Luật An ninh mạng 116/2025 — Chương IV | `data/luat116_ch04.md` | 4.271 | Như trên + `chapter_file` |
| 6 | Luật An ninh mạng 116/2025 — Chương V | `data/luat116_ch05.md` | 3.231 | Như trên + `chapter_file` |
| 7 | Luật An ninh mạng 116/2025 — Chương VI | `data/luat116_ch06.md` | 7.640 | Như trên + `chapter_file` |
| 8 | Luật An ninh mạng 116/2025 — Chương VII | `data/luat116_ch07.md` | 7.309 | Như trên + `chapter_file` |
| 9 | Luật An ninh mạng 116/2025 — Chương VIII | `data/luat116_ch08.md` | 6.069 | Như trên + `chapter_file` |

Không index `luat116-2025.md` vì file này lặp lại nội dung của tám file theo chương, dễ tạo kết quả top-k trùng nhau.

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `document_number` | string | `81/2025/TT-BTC` | Giới hạn tìm kiếm đúng văn bản được hỏi |
| `document_type` | string | `luat`, `thong_tu` | Phân biệt loại văn bản và giảm nhiễu |
| `year` | integer | `2025` | Hỗ trợ lọc theo năm ban hành |
| `language` | string | `vi` | Bảo đảm truy xuất đúng ngôn ngữ |
| `article_number` | string | `10` | Nhận diện số Điều trong custom strategy |
| `citation` | string | `81/2025/TT-BTC:10` | Lọc chính xác theo văn bản và Điều trước khi vector search |

### Vector Embedding Configuration

- Model: `text-embedding-3-small`
- Kích thước vector: 1.536 chiều mặc định
- Similarity: cosine
- Batch size khi index: 100 chunks/request
- Retrieval: top-3
- Lý do: model hỗ trợ tốt nội dung đa ngôn ngữ, giới hạn input lớn hơn nhiều so với chunk dài nhất trong thí nghiệm, và quy mô 9 tài liệu chưa cần giảm dimensions. Embedding context được bổ sung tên văn bản và tiêu đề Điều để tăng khả năng phân biệt các quy định có từ vựng gần nhau.

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| `81-btc.md` | FixedSize (`1200/150`) | 15 | 1.193,53 | Trung bình, có thể cắt giữa Điều |
| `81-btc.md` | Sentence (`5 câu`) | 35 | 447,66 | Tốt ở ranh giới câu, kích thước không đều |
| `81-btc.md` | Recursive (`1200`) | 15 | 1.051,60 | Tốt, ưu tiên đoạn và dòng |
| `luat116_ch03.md` | FixedSize (`1200/150`) | 15 | 1.192,20 | Trung bình |
| `luat116_ch03.md` | Sentence (`5 câu`) | 13 | 1.211,31 | Có chunk dài tới 3.699 ký tự |
| `luat116_ch03.md` | Recursive (`1200`) | 15 | 1.049,67 | Tốt |
| `luat116_ch08.md` | FixedSize (`1200/150`) | 6 | 1.136,50 | Trung bình |
| `luat116_ch08.md` | Sentence (`5 câu`) | 8 | 755,75 | Tốt |
| `luat116_ch08.md` | Recursive (`1200`) | 8 | 756,38 | Tốt |

### Strategy Của Tôi

**Loại:** Custom `DocumentChunker` kết hợp metadata trích dẫn

**Mô tả cách hoạt động:**
> Strategy nhận diện heading Markdown của `Chương`, `Mục`, `Điều`, lấy mỗi Điều làm đơn vị retrieval chính và lặp lại context Chương/Mục ở đầu chunk. Điều dài hơn 1.500 ký tự được chia recursive nhưng vẫn giữ tiêu đề Điều ở từng phần. Trước khi embedding, chunk được bổ sung tên văn bản và Điều; các chunk chỉ có tiêu đề, không có nội dung thực chất, bị loại bỏ. Với câu hỏi có trích dẫn rõ, metadata `citation` được lọc trước khi cosine search.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Người dùng pháp lý thường cần biết câu trả lời thuộc văn bản và Điều nào, nên ranh giới cấu trúc quan trọng hơn việc chỉ giữ độ dài cố định. Strategy này tăng khả năng truy vết nguồn, tránh trộn nội dung của hai Điều và cho phép lọc chính xác theo citation.

**Code snippet (nếu custom):**
```python
chunker = DocumentChunker(chunk_size=1500)
chunks = chunker.chunk(legal_text)

# Ví dụ metadata dùng trước vector search
metadata["citation"] = "81/2025/TT-BTC:10"
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| Toàn bộ 9 tài liệu | Recursive `chunk_size=1200` | 83 | 1.054,92 | 10/10, MRR 1,00 |
| Toàn bộ 9 tài liệu | **Document `chunk_size=1500` + citation filter** | 95 | 975,88 | 10/10, MRR 0,90 |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | DocumentChunker + citation metadata | 10 | Giữ Điều/Chương, truy vết nguồn tốt | Cần parser sạch và filter khi nhiều Điều gần nghĩa |
| [Tên] | | | | |
| [Tên] | | | | |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> Trên đúng 5 benchmark queries hiện tại, RecursiveChunker tốt nhất vì cả 5 kết quả relevant đều ở top-1. DocumentChunker cũng đạt 10/10 và phù hợp hơn khi cần giải thích nguồn; metadata filter đã đưa Điều 10 từ ngoài top-3 lên top-1. Vì vậy recursive là baseline hiệu quả nhất, còn document-aware strategy là lựa chọn tốt hơn cho hệ thống pháp lý cần citation và audit.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\n+)` để tách tại khoảng trắng hoặc xuống dòng ngay sau dấu kết thúc câu. Các câu được `strip`, bỏ phần rỗng, sau đó gom theo `max_sentences_per_chunk`; văn bản rỗng trả về danh sách rỗng.

**`RecursiveChunker.chunk` / `_split`** — approach:
> Thuật toán thử separator theo thứ tự ưu tiên từ ranh giới lớn như đoạn văn đến khoảng trắng, đồng thời gom các phần nhỏ nếu tổng độ dài chưa vượt `chunk_size`. Base case là đoạn đã đủ ngắn; nếu hết separator hoặc gặp separator rỗng, nội dung được cắt cứng theo `chunk_size` để luôn kết thúc an toàn.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> Mỗi `Document` được chuẩn hóa thành record gồm ID duy nhất, nội dung, metadata có thêm `doc_id`, và embedding. Store ưu tiên ChromaDB nếu khả dụng, nếu không sẽ dùng danh sách in-memory; truy vấn được embed rồi xếp hạng giảm dần bằng cosine similarity (Chroma collection cũng được cấu hình cosine).

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter` lọc metadata trước, rồi chỉ tính độ tương đồng trên tập ứng viên còn lại để tránh top-k bị chiếm bởi tài liệu sai phạm vi. `delete_document` xóa toàn bộ record có `metadata["doc_id"]` trùng ID yêu cầu và trả về `True` chỉ khi thực sự có dữ liệu bị xóa.

### KnowledgeBaseAgent

**`answer`** — approach:
> Agent lấy top-k kết quả, ghép từng chunk với nhãn nguồn thành phần `Context`, rồi đặt câu hỏi ở cuối prompt. Prompt yêu cầu LLM chỉ trả lời từ bằng chứng được cung cấp và phải nói rõ khi context không đủ, nhờ đó giảm khả năng bịa thông tin.

### Test Results

```text
============================= test session starts =============================
collected 42 items
tests/test_solution.py ..........................................         [100%]
============================= 42 passed in 2.69s ==============================
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Giá nhà đất tại thành phố đang tăng mạnh. | Bất động sản khu vực đô thị có xu hướng leo thang. | high | 0.012411 | Không |
| 2 | Python là một ngôn ngữ lập trình phổ biến. | Python được sử dụng rộng rãi để phát triển phần mềm. | high | 0.120767 | Không |
| 3 | Cơ sở dữ liệu vector lưu trữ embedding. | Vector store hỗ trợ tìm kiếm theo độ tương đồng. | high | -0.211230 | Không |
| 4 | Hôm nay trời mưa rất lớn. | Tôi đang học cách xây dựng hệ thống RAG. | low | -0.036277 | Đúng |
| 5 | Metadata filtering giúp giảm nhiễu khi truy xuất. | Lọc theo phòng ban có thể cải thiện độ chính xác retrieval. | high | 0.042912 | Không |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Cặp 3 bất ngờ nhất vì hai câu cùng nói về vector store nhưng lại nhận điểm âm. Nguyên nhân là thí nghiệm đang dùng `_mock_embed`, vốn tạo vector xác định từ hash của toàn bộ chuỗi chứ không học ngữ nghĩa; vì vậy điểm số chỉ phù hợp để kiểm thử pipeline và không nên được diễn giải như chất lượng semantic embedding thật.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Theo Thông tư 81/2025/TT-BTC, thời điểm COT được quy định vào lúc mấy giờ? | 16 giờ của ngày làm việc theo giờ Việt Nam. |
| 2 | Theo Điều 10 Thông tư 81/2025/TT-BTC, hạn hoàn thành chuyển đổi sang mô hình tài khoản tập trung là khi nào? | Chậm nhất ngày 30 tháng 6 năm 2028. |
| 3 | Cha mẹ/người giám hộ có trách nhiệm gì khi trẻ em dùng dịch vụ giá trị gia tăng trên không gian mạng? | Đứng ký tài khoản bằng thông tin của mình và giám sát, quản lý nội dung trẻ truy cập, đăng tải, chia sẻ. |
| 4 | Luật An ninh mạng số 116/2025 có hiệu lực từ ngày nào? | Ngày 01 tháng 7 năm 2026. |
| 5 | Theo Điều 7, xuyên tạc lịch sử và phủ nhận thành tựu cách mạng có bị nghiêm cấm không? | Có; đăng tải, phát tán nội dung này trên không gian mạng bị nghiêm cấm. |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời điểm COT | Thông tư 81, Điều 2 — giải thích COT và mốc 16 giờ | 0,664835 | Có | COT là 16 giờ ngày làm việc theo giờ Việt Nam. |
| 2 | Hạn chuyển đổi mô hình tập trung | Thông tư 81, Điều 10 — tổ chức thực hiện | 0,619321 | Có | Hạn chót là 30/06/2028. |
| 3 | Trách nhiệm cha mẹ/người giám hộ | Luật 116, Điều 16 — bảo vệ trẻ em trên không gian mạng | 0,606685 | Có | Đăng ký bằng thông tin người lớn và giám sát nội dung của trẻ. |
| 4 | Ngày Luật 116 có hiệu lực | Luật 116, Điều 44 — hiệu lực thi hành | 0,764904 | Có | Luật có hiệu lực ngày 01/07/2026. |
| 5 | Xuyên tạc lịch sử | Top-1 là phần khác của Điều 7; chunk chứa gold answer ở top-2 | 0,723532 | Không ở top-1, có ở top-2 | Có, đây là nội dung bị nghiêm cấm. |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5

Chi tiết đầy đủ của năm strategy được lưu tại `data/legal_benchmark_summary.md` và `data/legal_benchmark_results.json`.

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> *Viết 2-3 câu:*

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> *Viết 2-3 câu:*

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> Tôi sẽ làm sạch các heading OCR sai như `Chương 20` hoặc các Điều bị lặp trước khi index, đồng thời chuẩn hóa citation ngay từ bước ingestion. Với corpus lớn hơn, tôi sẽ kết hợp vector similarity với citation/keyword reranking để tránh Điều có từ vựng gần nghĩa xếp trên Điều được hỏi trực tiếp.

### Failure Analysis

Khi query 2 chạy bằng DocumentChunker nhưng **không có metadata filter**, top-3 bị Điều 5 và Điều 6 chiếm vì các chunk này lặp nhiều cụm “mô hình tài khoản thanh toán tập trung”; Điều 10 chứa mốc thời gian đúng lại nằm ngoài top-3. Sau khi lọc trước bằng `citation=81/2025/TT-BTC:10`, Điều 10 lên top-1. Trường hợp này cho thấy embedding tốt vẫn có thể nhầm các Điều gần chủ đề, và metadata pháp lý có giá trị trực tiếp đối với precision.

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
| Core implementation (tests) | Cá nhân | / 30 |
| Demo | Nhóm | / 5 |
| **Tổng** | | **/ 100** |
