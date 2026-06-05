from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # 1. Tách văn bản thành các dòng để xử lý cấu trúc Luật (Điều, Khoản, Điểm)
        lines = text.split('\n')
        sentences = []
        
        # Regex này dùng để nhận diện dấu chấm kết thúc câu thực sự.
        # Sử dụng Negative Lookbehind (?<!...) để TRÁNH tách ở các trường hợp:
        # - Số điều: "Điều 1. " -> (?<!\bĐiều \d\.) (hỗ trợ tối đa 3 chữ số)
        # - Số khoản: "1. " hoặc "12. " -> (?<!\b\d\.)
        # - Ký tự viết tắt đơn lẻ hoặc mục lục: (?<!\b[A-Za-z]\.)
        sentence_end_pattern = re.compile(r'(?<!\bĐiều \d\.)(?<!\bĐiều \d{2}\.)(?<!\bĐiều \d{3}\.)(?<!\b\d\.)(?<!\b\d{2}\.)(?<!\b\d{3}\.)(?<!\b[A-Za-z]\.)(?<=[.!?])\s+')

        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Bỏ qua các dòng đánh dấu trang dạng "--- PAGE X ---" hoặc số trang trần nếu có
            if line.startswith("---") or re.match(r'^\d+$', line):
                continue

            # Tách các câu trong cùng một dòng dựa trên pattern đã định nghĩa
            splits = sentence_end_pattern.split(line)
            
            for s in splits:
                s_clean = s.strip()
                if s_clean:
                    sentences.append(s_clean)

        # 2. Gom nhóm các câu thành các đoạn (chunks) theo cấu trúc max_sentences_per_chunk
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            # Nếu thêm câu này vào mà chunk vượt quá 700 ký tự hoặc vượt quá max_sentences
            if (current_length + sentence_len > 700) or (len(current_chunk) >= self.max_sentences_per_chunk):
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_len
            else:
                current_chunk.append(sentence)
                current_length += sentence_len + 1 # +1 cho dấu cách
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        
        # Gọi hàm đệ quy bắt đầu với danh sách tất cả separators ban đầu
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        current_text = current_text.strip()
        
        # Điểm dừng đệ quy 1: Nếu đoạn văn bản đã đủ nhỏ dưới ngưỡng chunk_size
        if len(current_text) <= self.chunk_size:
            return [current_text] if current_text else []
            
        # Điểm dừng đệ quy 2: Nếu không còn dấu phân tách nào để thử
        if not remaining_separators:
            return [current_text]

        # Lấy dấu phân tách có độ ưu tiên cao nhất hiện tại và chuẩn bị danh sách cho vòng kế tiếp
        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]
        
        # Tiến hành tách văn bản dựa trên separator hiện tại
        # Sử dụng re.escape để tránh lỗi khi ký tự đặc biệt như dấu chấm "." nằm trong separator
        if separator == "":
            # Tách theo từng ký tự nếu là chuỗi rỗng
            splits = list(current_text)
        else:
            # Tách theo ký tự phân tách nhưng giữ lại vị trí trống, lọc bỏ chuỗi rỗng sau đó
            splits = re.split(re.escape(separator), current_text)
            
        final_chunks = []
        good_splits = []
        
        for part in splits:
            part_clean = part.strip()
            if not part_clean:
                continue
                
            # Nếu đoạn con sau khi bẻ vẫn lớn hơn chunk_size, bắt buộc đệ quy sâu xuống dấu phân tách tiếp theo
            if len(part_clean) > self.chunk_size:
                # Trước khi đệ quy đoạn lớn, gom nốt các đoạn nhỏ đang tích lũy trước đó (nếu có)
                if good_splits:
                    final_chunks.extend(self._merge_splits(good_splits, separator))
                    good_splits = []
                # Đệ quy xuống sâu hơn
                recursive_sub_chunks = self._split(part_clean, next_separators)
                final_chunks.extend(recursive_sub_chunks)
            else:
                good_splits.append(part_clean)
                
        # Gom nhóm nốt các đoạn nhỏ còn lại trong hàng đợi
        if good_splits:
            final_chunks.extend(self._merge_splits(good_splits, separator))
            
        return final_chunks

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """
        Hàm bổ trợ: Gom nhóm các đoạn văn nhỏ lại với nhau bằng dấu `separator` 
        sao cho tổng độ dài của nhóm gần bằng `chunk_size` nhất nhưng không vượt quá.
        """
        merged_chunks = []
        current_group = []
        current_length = 0
        
        # Nếu separator là chuỗi rỗng, khi nối lại ta dùng chuỗi rỗng, ngược lại giữ nguyên ký tự gốc (ví dụ: '\n', '. ')
        sep_to_join = separator if separator != "" else ""

        for split in splits:
            # Tính toán độ dài nếu thêm đoạn này vào nhóm hiện tại
            # Độ dài mới = độ dài hiện tại + độ dài dấu phân tách + độ dài đoạn mới
            add_len = len(sep_to_join) if current_length > 0 else 0
            
            if current_length + add_len + len(split) <= self.chunk_size:
                current_group.append(split)
                current_length += add_len + len(split)
            else:
                # Nếu vượt quá, đóng gói nhóm hiện tại và tạo nhóm mới
                if current_group:
                    merged_chunks.append(sep_to_join.join(current_group))
                current_group = [split]
                current_length = len(split)
                
        if current_group:
            merged_chunks.append(sep_to_join.join(current_group))
            
        return merged_chunks

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    # 1. Kiểm tra điều kiện độ dài danh sách (optional nhưng an toàn)
    if len(vec_a) != len(vec_b) or len(vec_a) == 0:
        return 0.0

    dot_product = 0.0
    norm_a = 0.0
    norm_b = 0.0

    # 2. Tính toán các giá trị trong một vòng lặp duy nhất để tối ưu hiệu năng
    for a, b in zip(vec_a, vec_b):
        dot_product += a * b
        norm_a += a * a
        norm_b += b * b

    # Tích căn bậc hai độ dài của 2 vector
    magnitude_product = math.sqrt(norm_a) * math.sqrt(norm_b)

    # 3. Trả về kết quả và xử lý trường hợp vector có độ dài bằng 0
    if magnitude_product == 0.0:
        return 0.0

    return dot_product / magnitude_product


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 500) -> dict:
        # Ước lượng số câu tương ứng dựa trên chunk_size mong muốn (trung bình 1 câu luật tiếng Việt ~150 ký tự)
        max_sentences = max(1, math.ceil(chunk_size / 150))
        
        fixed_size_chunker = FixedSizeChunker(chunk_size=chunk_size)
        sentence_chunker = SentenceChunker(max_sentences_per_chunk=max_sentences)
        recursive_chunker = RecursiveChunker(chunk_size=chunk_size)

        fixed_size_result = fixed_size_chunker.chunk(text)
        sentence_result = sentence_chunker.chunk(text)
        recursive_result = recursive_chunker.chunk(text)

        def _calculate_stats(chunks: list[str]) -> dict:
            if not chunks:
                return {"total_chunks": 0, "avg_length": 0.0, "max_length": 0, "min_length": 0, "chunks": []}
            
            lengths = [len(c) for c in chunks]
            return {
                "total_chunks": len(chunks),
                "avg_length": round(sum(lengths) / len(chunks), 2),
                "max_length": max(lengths),
                "min_length": min(lengths),
                "chunks": chunks
            }

        return {
            "fixed_size_chunking": _calculate_stats(fixed_size_result),
            "sentence_chunking": _calculate_stats(sentence_result),
            "recursive_chunking": _calculate_stats(recursive_result)
        }