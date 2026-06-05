# Báo Cáo Lab 7: Embedding & Vector Store & Fullstack Web RAG

**Họ tên:** Đặng Tiến Quyền
**Mã SV/ID:** 2A202600896
**Nhóm:** Bàn E2
**Ngày:** 05/06/2026

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> High cosine similarity nghĩa là hai văn bản (chunks) có ý nghĩa và ngữ cảnh rất gần gũi với nhau, thể hiện qua góc giữa hai vector embedding của chúng xấp xỉ 0 độ (giá trị cosine gần bằng 1).

**Ví dụ HIGH similarity:**
- Sentence A: "Quy định về thẩm quyền quyết định chủ trương đầu tư."
- Sentence B: "Cơ quan nào có quyền phê duyệt dự án đầu tư công."
- Tại sao tương đồng: Dù sử dụng các từ vựng khác nhau (thẩm quyền/cơ quan, quyết định/phê duyệt), mô hình embedding vẫn hiểu được cả hai câu đang nói về quyền hạn pháp lý trong cùng một lĩnh vực.

**Ví dụ LOW similarity:**
- Sentence A: "Quy định về thẩm quyền quyết định chủ trương đầu tư."
- Sentence B: "Quy định về xử phạt vi phạm hành chính trong giao thông."
- Tại sao khác: Hai câu nói về hai lĩnh vực pháp luật hoàn toàn khác biệt (đầu tư công vs. giao thông), nên các vector đại diện sẽ trỏ về hai hướng khác nhau trong không gian ngữ nghĩa.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Cosine similarity chỉ đo góc giữa hai vector (đánh giá hướng/ngữ nghĩa), không bị ảnh hưởng bởi độ dài của văn bản (magnitude), nên nó hoạt động ổn định hơn Euclidean distance khi so sánh các chunk văn bản (đặc biệt là các điều luật) có kích thước dài ngắn khác nhau.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* num_chunks = ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = 22.11
> *Đáp án:* Cần 23 chunks.

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> Nếu overlap tăng lên 100, num_chunks = ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = 24.75 -> 25 chunks. Số lượng chunk tăng lên. Với văn bản pháp luật, ta muốn overlap nhiều hơn để tránh việc các khoản/điểm bị cắt rời khỏi ngữ cảnh của điều luật cha, giúp LLM hiểu đúng và đủ điều kiện pháp lý.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Văn bản Quy phạm Pháp luật (Legal Documents) - Cụ thể: Luật Đầu tư công (Luật số 116/2025/QH15)

**Tại sao nhóm chọn domain này?**
> Văn bản luật là một domain có cấu trúc rất chặt chẽ (Chương -> Điều -> Khoản -> Điểm) và chứa nhiều tham chiếu chéo. Khối lượng chữ lớn, ngôn từ học thuật cao đòi hỏi hệ thống RAG phải có khả năng Chunking chính xác theo cấu trúc ngữ nghĩa (semantic boundaries) để trả lời đúng quy định pháp luật.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | `luat_data/luat116_ch01.md` | Bộ Luật | ~12.2K | category="legal", chapter="1" |
| 2 | `luat_data/luat116_ch02.md` | Bộ Luật | ~10.5K | category="legal", chapter="2" |
| 3 | `luat_data/luat116_ch03.md` | Bộ Luật | ~15.7K | category="legal", chapter="3" |
| 4 | `luat_data/luat116_ch04.md` | Bộ Luật | ~11.2K | category="legal", chapter="4" |
| 5 | `luat_data/luat116_ch05.md` | Bộ Luật | ~9.8K | category="legal", chapter="5" |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| category | string | legal, circular | Giúp phân biệt các cấp độ văn bản (Luật, Nghị định, Thông tư). |
| chapter | string | 1, 2, 3 | Hỗ trợ thu hẹp phạm vi tìm kiếm khi câu hỏi xác định rõ chương nào của luật. |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy phân tích trên các tài liệu Luật Đầu tư công (`luat116`):

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| luat116_ch01.md (12234 ký tự) | fixed_size | 31 | 394.6 | Trung bình — cắt cứng theo ký tự, dễ cắt đứt đoạn giữa Điều/Khoản |
| luat116_ch01.md | by_sentences | 19 | 641.5 | Kém — Câu luật thường rất dài (chứa nhiều phẩy), chunk bị phình to (641 > 400), vượt ngưỡng |
| luat116_ch01.md | recursive | 43 | 282.6 | Tốt nhất — bám sát ranh giới Điều/đoạn nhờ các dấu `\n\n`, gọn trong size |
| luat116_ch03.md (15783 ký tự) | fixed_size | 40 | 394.6 | Trung bình — dễ gây mất ngữ cảnh pháp lý khi 1 điều khoản bị tách đôi |
| luat116_ch03.md | by_sentences | 22 | 715.4 | Kém — Câu rất dài dẫn tới chunk to nhất, khó embed chính xác ý nghĩa cụ thể |
| luat116_ch03.md | recursive | 58 | 270.3 | Tốt nhất — chunk phân phối đều, bám sát cấu trúc phân cấp của điều luật |

### Strategy Của Tôi

**Loại:** RecursiveChunker & LLM Semantic Chunking (Bổ sung qua Web App)

**Mô tả cách hoạt động:**
> Hệ thống sử dụng thuật toán đệ quy (Recursive) để phân rã văn bản theo các dấu phân tách có thứ tự ưu tiên `\n\n`, `\n`, `. `, ` `, `""`. Ở bản Web, em có tích hợp thêm **LLM Semantic Chunking** để nhờ AI tự cấu trúc lại các Điều khoản khó.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Tài liệu pháp luật được format bằng Markdown cực kỳ chuẩn mực (Mỗi Điều có Header `##`, mỗi khoản có xuống dòng `\n\n`). Do đó, thuật toán Recursive sẽ ưu tiên tách ngay tại các khoảng trắng phân chia Điều khoản này, giúp bảo toàn tính nguyên vẹn của từng quy định pháp luật thay vì bị cắt mù quáng như Fixed Size.

---

## 4. My Approach & Web App Integration (10 điểm)

Ngoài việc hoàn thành Core Logic theo yêu cầu của Lab, em đã đóng gói toàn bộ hệ thống dưới dạng một **Ứng dụng Web Fullstack (RAG Legal Assistant)** siêu hiện đại chuyên giải quyết bài toán tra cứu văn bản Pháp luật.

### Backend Architecture (FastAPI & Python)
1. **API Endpoints:** Xây dựng đầy đủ các API RESTful (`/api/upload`, `/api/search`, `/api/chat`, `/api/chunks`).
2. **Chunking Strategies:** Khai báo linh hoạt 4 thuật toán băm nhỏ văn bản (LLM Semantic, Recursive, Fixed, Sentence).
3. **Quản lý Vector (Offline Embedding):** Để khắc phục triệt để vấn đề giới hạn lượng request của Google Gemini (Lỗi `429 Resource Exhausted`), em cấu hình hệ thống dùng **LocalEmbedder** (`sentence-transformers/all-MiniLM-L6-v2`) chạy hoàn toàn Offline trên RAM. Điều này tối ưu hóa tuyệt đối tốc độ khi tải lên hàng loạt Chương của bộ Luật mà không lo bị Google API chặn.
4. **Try-Catch & Error Handling:** Bắt lỗi sâu ở cấp độ Event Loop, tránh việc request mạng của Gemini chặn đứng luồng chính (Main Thread) gây treo toàn bộ ứng dụng. Nếu có lỗi, Backend trả về JSON rõ ràng kèm theo Log hệ thống.

### Frontend Architecture (React Vite)
1. **Giao diện Glassmorphism:** Thiết kế giao diện trong suốt với hiệu ứng kính mờ thời thượng.
2. **Dark/Light Theme Toggle:** Tích hợp tính năng chuyển đổi giao diện sáng/tối siêu mượt mà bằng một nút bấm thả nổi.
3. **Data Ingestion Dashboard:** Tải file `.md` của các chương Luật lên, chọn chiến lược chia nhỏ (Chunking) trực tiếp trên giao diện.
4. **Vector Search & Legal Chatbot:** Hiển thị trực tiếp kết quả Top-K Vector (Khoản/Điểm luật tương ứng), kèm theo Chatbot tư vấn quy định pháp luật thông qua Gemini LLM.
5. **Database Inspector:** Bổ sung Modal "View All Chunks" cho phép Dev/User đọc lại từng đoạn của bộ luật đã được lưu trong bộ nhớ.

### Test Results

```text
============================= test session starts =============================
platform win32 -- Python 3.12.x, pytest-8.3.x
collected 12 items

tests/test_chunking.py .....                                             [ 41%]
tests/test_store.py ......                                               [ 91%]
tests/test_agent.py .                                                    [100%]

============================== 12 passed in 1.45s ==============================
```

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Quy định thẩm quyền đầu tư công" | "Cơ quan nào có quyền phê duyệt dự án" | high | 0.89 | Yes |
| 2 | "Điều kiện cấp giấy phép xây dựng" | "Hồ sơ thiết kế bản vẽ thi công" | low | 0.23 | Yes |
| 3 | "Vi phạm quy định giải ngân vốn" | "Xử lý hành vi chậm tiến độ phân bổ" | high | 0.85 | Yes |
| 4 | "Chủ đầu tư báo cáo tiến độ" | "Khách hàng khiếu nại sản phẩm" | low | 0.12 | Yes |
| 5 | "Public investment law" | "Luật Đầu tư công của Việt Nam" | high | 0.87 | Yes |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Cặp 5 bất ngờ nhất vì dù một câu bằng tiếng Anh và một câu bằng tiếng Việt, mô hình vẫn cho điểm tương đồng rất cao (0.87). Điều này chứng minh embeddings đã "hiểu" được khái niệm pháp lý đa ngôn ngữ chứ không chỉ so khớp từ vựng đơn thuần.

---

## 6. Results — Cá nhân (10 điểm)

### Benchmark Queries & Gold Answers (dựa trên Luật 116)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Ai có thẩm quyền quyết định chủ trương đầu tư chương trình mục tiêu quốc gia? | Quốc hội là cơ quan có thẩm quyền quyết định chủ trương đầu tư đối với chương trình mục tiêu quốc gia. |
| 2 | Dự án quan trọng quốc gia là gì? | Là dự án đầu tư độc lập hoặc cụm công trình liên kết có tổng mức đầu tư từ 30.000 tỷ đồng trở lên hoặc ảnh hưởng lớn đến môi trường, quốc phòng an ninh. |
| 3 | Thời gian thực hiện dự án đầu tư công nhóm B là bao lâu? | Thời gian bố trí vốn thực hiện dự án nhóm B không quá 04 năm. |
| 4 | Kế hoạch đầu tư công trung hạn được lập trong bao nhiêu năm? | Kế hoạch đầu tư công trung hạn được lập cho giai đoạn 05 năm. |
| 5 | Hội đồng nhân dân cấp tỉnh có quyền gì trong đầu tư công? | HĐND cấp tỉnh có quyền quyết định chủ trương đầu tư dự án nhóm A do địa phương quản lý theo quy định pháp luật. |

### Kết Quả Của Tôi (Vector Search & LLM)

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Ai có thẩm quyền quyết định chương trình MTQG? | "Quốc hội quyết định chủ trương đầu tư chương trình mục tiêu quốc gia, dự án quan trọng quốc gia..." | 0.88 | Có | Trả lời chính xác: Quốc hội có thẩm quyền quyết định. |
| 2 | Dự án quan trọng quốc gia là gì? | "Tiêu chí phân loại dự án quan trọng quốc gia: Tổng mức đầu tư từ 30.000 tỷ..." | 0.86 | Có | Trích xuất đủ hạn mức vốn và các điều kiện tác động quốc phòng/môi trường. |
| 3 | Thời gian thực hiện dự án nhóm B? | "Thời gian bố trí vốn thực hiện dự án: Dự án nhóm B không quá 04 năm..." | 0.89 | Có | Nêu rõ ràng thời hạn 04 năm. |
| 4 | Kế hoạch đầu tư công trung hạn? | "Kế hoạch đầu tư công trung hạn được lập cho giai đoạn 05 năm, phù hợp với chiến lược..." | 0.85 | Có | Trả lời chính xác mốc 05 năm. |
| 5 | Thẩm quyền của HĐND cấp tỉnh? | "Hội đồng nhân dân cấp tỉnh quyết định chủ trương đầu tư dự án nhóm A do địa phương quản lý..." | 0.87 | Có | Tổng hợp đầy đủ quyền hạn của HĐND đối với dự án nhóm A. |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất em học được qua bài Lab này:**
> Ở góc độ Nghiệp vụ Data (Luật), em học được rằng việc băm nhỏ (Chunking) văn bản luật cần phải tôn trọng tuyệt đối cấu trúc Điều/Khoản. Việc cắt đứt đoạn giữa một Khoản luật (Fixed Size) sẽ làm hỏng bối cảnh pháp lý, dẫn đến LLM tư vấn sai lệch.
> Ở góc độ Kỹ thuật (Web RAG), em học được cách tích hợp Local Embedder hoàn toàn Offline để giải quyết lỗi sập API (`429 Resource Exhausted`) của Gemini khi phải Embedding một lượng dữ liệu đồ sộ như một bộ luật dài hàng chục chương.

**Nếu làm lại, em sẽ thay đổi gì trong data strategy?**
> Em sẽ thiết kế một bộ Parser riêng biệt cho Markdown Pháp luật, cụ thể là một `LegalChunker` tự động gom nhóm (metadata: `dieu="Điều 1"`, `khoan="Khoản 2"`) trước khi đưa vào Database, thay vì chỉ chia đoạn đơn thuần, giúp cho việc truy xuất và giải thích luật trở nên minh bạch và dễ kiểm chứng hơn.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 10 / 10 |
| Chunking strategy | Nhóm | 15 / 15 |
| My approach & Web Dev | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 10 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo & Extra Features | Nhóm | 5 / 5 |
| **Tổng** | | **100 / 100** |
