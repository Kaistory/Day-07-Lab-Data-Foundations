from chunking import ChunkingStrategyComparator
if __name__ == "__main__":
    # Dữ liệu văn bản Luật mẫu
    law_data = """
    Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng
    1. Luật này quy định về an ninh mạng, bảo vệ an ninh mạng; quyền, nghĩa vụ, trách nhiệm của cơ quan, tổ chức, cá nhân có liên quan.
    2. Luật này áp dụng đối với:
    a) Cơ quan, tổ chức, cá nhân Việt Nam;
    b) Cơ quan, tổ chức, cá nhân nước ngoài tại Việt Nam và người gốc Việt Nam chưa xác định được quốc tịch đang sinh sống tại Việt Nam đã được cấp giấy chứng nhận căn cước;
    c) Cơ quan, tổ chức, cá nhân nước ngoài trực tiếp tham gia hoặc có liên quan đến hoạt động bảo vệ an ninh mạng.
    
    Điều 2. Giải thích từ ngữ
    Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
    1. An ninh mạng là sự ổn định, an ninh, an toàn của không gian mạng; bảo vệ hệ thống thông tin không gây phương hại đến an ninh quốc gia, trật tự, an toàn xã hội.
    """

    print("--- 1. CHẠY BỘ SO SÁNH CÁC CHIẾN LƯỢC CHUNK VĂN BẢN (Ví dụ Chunk Size = 400 cho local model) ---")
    comparator = ChunkingStrategyComparator()
    report = comparator.compare(law_data, chunk_size=400)
    
    for strategy, stats in report.items():
        print(f"\n[Chiến lược: {strategy.upper()}]")
        print(f"  + Tổng số chunk: {stats['total_chunks']}")
        print(f"  + Độ dài Max/Min: {stats['max_length']} / {stats['min_length']} ký tự")
        print