# Legal RAG Web App

Ứng dụng web dùng React cho giao diện và `aiohttp` cho backend. Backend truy xuất
top K từ ChromaDB, loại các kết quả dưới threshold, sau đó dùng OpenAI Responses
API để tổng hợp câu trả lời có citation.

## Chạy ứng dụng

Từ thư mục gốc của repository:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app_backend.py
```

Mở `http://127.0.0.1:8000`.

## Cấu hình

Các biến môi trường được đọc từ `.env`:

```dotenv
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4.1-mini
CHROMA_PERSIST_DIR=./chroma_data
APP_PORT=8000
```

Mỗi chiến lược chunking dùng một collection ChromaDB riêng. Nếu collection đã
có đủ số chunk, backend tái sử dụng embedding đã lưu thay vì gọi embedding lại.

## Luồng xử lý

1. Người dùng nhập câu hỏi, chọn strategy, top K và threshold.
2. Backend truy xuất các chunk gần nhất từ collection tương ứng.
3. Toàn bộ top K, score, metadata và quyết định `PASS`/`REJECT` được in ra terminal.
4. Chỉ các chunk có score đạt threshold mới được gửi cho model chat.
5. Nếu không có chunk đạt threshold, hệ thống trả về trạng thái thiếu bằng chứng
   và không gọi model chat.
