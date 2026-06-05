import json
import os
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
    """Đọc toàn bộ text từ file PDF sử dụng PyMuPDF."""
    if not fitz:
        raise ImportError("Vui lòng cài đặt PyMuPDF (pip install pymupdf) để đọc file PDF.")
    
    doc = fitz.open(pdf_path)
    text = ""
    pages_to_read = min(max_pages, len(doc)) if max_pages else len(doc)
    for i in range(pages_to_read):
        text += doc[i].get_text() + "\n"
    return text

def process_text_with_llm(raw_text: str, doc_short_name: str, llm_fn) -> list[dict]:
    """
    Gửi nội dung thô cho LLM xử lý chunking và metadata theo đúng Prompt.
    """
    prompt = f"""Nhiệm vụ: Bạn là một chuyên gia xử lý dữ liệu cho Vector Database (Chroma DB). Nhiệm vụ của bạn là tiếp nhận tài liệu thô từ người dùng, thực hiện chia nhỏ văn bản (chunking) theo chuẩn ngữ nghĩa và trích xuất cấu trúc dữ liệu chính xác để sẵn sàng nạp vào Chroma DB.

Hướng dẫn xử lý:
1. Chunking (Chia nhỏ): Chia văn bản thành các đoạn nhỏ (mỗi đoạn khoảng 500 - 800 ký tự). Đảm bảo mỗi đoạn giữ nguyên được một ý nghĩa trọn vẹn. Tạo khoảng chồng lấp (overlap) khoảng 10-15% ngữ cảnh giữa chunk trước và chunk sau nếu đoạn văn bị ngắt ở giữa câu.
2. Tạo IDs: Tạo ID duy nhất cho mỗi chunk theo định dạng: "doc_{doc_short_name}_[số_thứ_tự_chunk]". (Ví dụ: doc_{doc_short_name}_0, doc_{doc_short_name}_1).
3. Trích xuất Metadata: Với mỗi chunk, hãy tự động phân tích và trích xuất các thông tin sau vào object "metadata":
   - "source": Tên tài liệu gốc (người dùng sẽ cung cấp hoặc bạn tự suy luận ngắn gọn).
   - "topic": Chủ đề chính của riêng đoạn chunk đó (1-3 từ).
   - "summary": Một câu tóm tắt cực ngắn gọn nội dung của chunk đó.

Yêu cầu đầu ra (Output Format):
Bạn CHỈ ĐƯỢC PHÉP trả về kết quả dưới dạng một mảng JSON (JSON Array) hợp lệ, không kèm theo lời giải thích, không có ký tự markdown nằm ngoài khối JSON.

Cấu trúc JSON đầu ra phải chạy được trực tiếp với code Python sau:
[
  {{
    "id": "chuỗi_id",
    "document": "nội dung văn bản thô của chunk",
    "metadata": {{
      "source": "tên_nguồn",
      "topic": "chủ_đề",
      "summary": "tóm_tắt"
    }}
  }}
]

--- TÀI LIỆU THÔ CẦN XỬ LÝ ---
{raw_text}
"""

    # Gọi LLM
    response_text = llm_fn(prompt)
    
    # Xử lý làm sạch chuỗi JSON nếu LLM lỡ in ra block markdown
    response_text = response_text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]
        
    if response_text.endswith("```"):
        response_text = response_text[:-3]
        
    response_text = response_text.strip()
    
    # Parse mảng JSON thành Python objects
    try:
        # Cố gắng tìm chuỗi JSON (bỏ qua các text ngoài luồng nếu có)
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        if start_idx != -1 and end_idx != 0:
            json_text = response_text[start_idx:end_idx]
            return json.loads(json_text)
        return json.loads(response_text)
    except Exception as e:
        print("Lỗi khi parse JSON từ LLM:", e)
        print("Raw response:", response_text)
        return []

def process_pdf_with_llm(pdf_path: str, doc_short_name: str, llm_fn, max_pages: int = 5) -> list[dict]:
    """
    Đọc PDF và gửi toàn bộ nội dung cho LLM xử lý chunking và metadata
    theo đúng Prompt yêu cầu.
    """
    # Để tránh quá tải context window của LLM với file lớn (như 15MB), ta giới hạn số trang
    raw_text = extract_text_from_pdf(pdf_path, max_pages=max_pages)
    return process_text_with_llm(raw_text, doc_short_name, llm_fn)

# --- Hướng dẫn cách sử dụng ---
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load API keys từ file .env (cần cấu hình OPENAI_API_KEY trong .env)
    load_dotenv()
    
    def openai_llm_call(prompt_text: str) -> str:
        from openai import OpenAI
        client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Có thể đổi thành gpt-4o hoặc model khác
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.1
        )
        return response.choices[0].message.content

    # Mẫu gọi thực tế:
    # pdf_path = "data/sample.pdf"
    # if os.path.exists(pdf_path):
    #     print("Đang xử lý PDF qua OpenAI...")
    #     chunks = process_pdf_with_llm(pdf_path, "sample", openai_llm_call)
    #     print(json.dumps(chunks, indent=2, ensure_ascii=False))
    # else:
    #     print(f"File {pdf_path} không tồn tại. Vui lòng chuẩn bị một file PDF để test.")
