# Vietnamese Legal Retrieval Benchmark

- Embedding model: `text-embedding-3-small`
- Embedding dimensions: `1536` (model default)
- Similarity: cosine
- Documents: 9
- Benchmark queries: 5

| Strategy | Parameters | Chunks | Avg length | Top-3 recall | MRR | Score /10 |
|---|---|---:|---:|---:|---:|---:|
| fixed | chunk_size=1200, overlap=150 | 79 | 1249.42 | 100% | 0.9000 | 10 |
| sentence | max_sentences_per_chunk=5 | 106 | 811.08 | 100% | 0.8000 | 10 |
| recursive | chunk_size=1200 | 83 | 1054.92 | 100% | 1.0000 | 10 |
| semantic | similarity_threshold=0.2, max_chunk_size=1500 | 162 | 539.32 | 80% | 0.7000 | 8 |
| document | chunk_size=1500, boundaries=['Chương', 'Mục', 'Điều'] | 95 | 975.88 | 100% | 0.9000 | 10 |

## Query Results

### fixed

| # | Relevant rank | Top-1 source | Top-1 score | Top-1 article |
|---:|---:|---|---:|---|
| 1 | 1 | 81-btc.md | 0.619615 | Điều 2. Giải thích từ ngữ |
| 2 | 1 | 81-btc.md | 0.701075 | Điều 10. Tổ chức thực hiện |
| 3 | 1 | luat116_ch03.md | 0.664817 | - |
| 4 | 2 | luat116_ch08.md | 0.665606 | - |
| 5 | 1 | luat116_ch01.md | 0.705288 | Điều 7. Các hành vi bị nghiêm cấm về an ninh mạng |

### sentence

| # | Relevant rank | Top-1 source | Top-1 score | Top-1 article |
|---:|---:|---|---:|---|
| 1 | 2 | 81-btc.md | 0.72489 | - |
| 2 | 1 | 81-btc.md | 0.794008 | - |
| 3 | 1 | luat116_ch03.md | 0.651096 | Điều 16. Phòng, chống xâm hại trẻ em trên không gian mạng |
| 4 | 1 | luat116_ch08.md | 0.731374 | - |
| 5 | 2 | luat116_ch01.md | 0.638681 | Điều 13 |

### recursive

| # | Relevant rank | Top-1 source | Top-1 score | Top-1 article |
|---:|---:|---|---:|---|
| 1 | 1 | 81-btc.md | 0.630265 | Điều 2. Giải thích từ ngữ |
| 2 | 1 | 81-btc.md | 0.697619 | - |
| 3 | 1 | luat116_ch03.md | 0.654174 | - |
| 4 | 1 | luat116_ch08.md | 0.708276 | Điều 44. Hiệu lực thi hành |
| 5 | 1 | luat116_ch01.md | 0.70097 | Điều 7. Các hành vi bị nghiêm cấm về an ninh mạng |

### semantic

| # | Relevant rank | Top-1 source | Top-1 score | Top-1 article |
|---:|---:|---|---:|---|
| 1 | 2 | 81-btc.md | 0.76632 | - |
| 2 | 1 | 81-btc.md | 0.728005 | - |
| 3 | 1 | luat116_ch03.md | 0.752083 | - |
| 4 | 1 | luat116_ch08.md | 0.679937 | - |
| 5 | - | luat116_ch01.md | 0.662573 | Điều 7. Các hành vi bị nghiêm cấm về an ninh mạng |

### document

| # | Relevant rank | Top-1 source | Top-1 score | Top-1 article |
|---:|---:|---|---:|---|
| 1 | 1 | 81-btc.md | 0.664835 | Điều 2. Giải thích từ ngữ |
| 2 | 1 | 81-btc.md | 0.619355 | Điều 10. Tổ chức thực hiện |
| 3 | 1 | luat116_ch03.md | 0.606685 | Điều 16. Phòng, chống xâm hại trẻ em trên không gian mạng |
| 4 | 1 | luat116_ch08.md | 0.764962 | Điều 44. Hiệu lực thi hành |
| 5 | 2 | luat116_ch01.md | 0.723532 | Điều 7. Các hành vi bị nghiêm cấm về an ninh mạng |

