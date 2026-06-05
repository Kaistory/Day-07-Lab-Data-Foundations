# Frontend - RAG Luật An ninh Mạng 116/2025

ReactJS frontend với MVC structure cho hệ thống Q&A dựa trên RAG (Retrieval-Augmented Generation).

## 📁 Cấu trúc Thư mục

```
frontend/
├── src/
│   ├── components/          # React components (Chatbot, Dashboard)
│   │   ├── Chatbot.jsx
│   │   └── Dashboard.jsx
│   ├── models/              # Data models & types
│   │   └── types.js
│   ├── services/            # API integration layer
│   │   └── apiClient.js
│   ├── styles/              # CSS files
│   │   ├── chatbot.css
│   │   └── dashboard.css
│   ├── App.jsx              # Main app component
│   ├── App.css              # Global styles
│   ├── index.css            # Base styles
│   ├── main.jsx             # Entry point
│   └── ...
├── index.html               # HTML template
├── vite.config.js           # Vite configuration
├── package.json             # Dependencies
└── ...
```

## 🎨 Bảng Màu

- **Primary**: `#9FA1FF` (Soft Blue-Purple)
- **Secondary**: `#B5BAFF` (Lighter Blue-Purple)
- **Accent**: `#AEE2FF` (Light Cyan)
- **Success**: `#D9F9DF` (Light Green)

## 🚀 Cách Chạy

### 1. Cài đặt dependencies
```bash
npm install
```

### 2. Khởi động Backend (API)
```bash
# Từ thư mục root project
uvicorn api:app --reload
# Mở http://localhost:8000/docs để test API
```

### 3. Khởi động Frontend Dev Server
```bash
# Từ thư mục frontend/
npm run dev
```

Frontend sẽ mở tại `http://localhost:5173`

### 4. Build cho Production
```bash
npm run build
# Kết quả sẽ ở folder `dist/`
```

## 🏗️ Kiến trúc MVC

- **Models** (`models/types.js`): Định nghĩa các data structures
- **Views** (components): `Chatbot.jsx`, `Dashboard.jsx` - hiển thị UI
- **Controllers** (App.jsx): Quản lý state và logic

## 📱 Layout

- **Left Sidebar** (Dashboard): 
  - Lựa chọn Chapter
  - Backend selector
  - Chunking strategy selector
  - Lịch sử Q&A (20 mục gần nhất)

- **Right Main Area** (Chatbot):
  - Khu vực hiển thị messages
  - Input form để hỏi câu hỏi
  - Hiển thị answer + citations
  - Indicator confidence score

## 🔧 API Endpoints (Backend)

- `GET /` - Thông tin hệ thống
- `GET /chapters` - Danh sách 8 chương
- `POST /search` - Tìm kiếm đoạn liên quan
- `POST /ask` - Hỏi đáp RAG (Q&A)
- `GET /history` - Lịch sử Q&A

## 📝 Ví dụ Sử Dụng

1. Chọn một chương từ sidebar
2. Nhập câu hỏi: "An ninh mạng được định nghĩa như thế nào?"
3. Xem kết quả:
   - Câu trả lời từ LLM
   - Nguồn (citations) từ luật
   - Confidence score
4. Click vào lịch sử để xem lại câu trả lời cũ

## 🛠️ Công nghệ

- **React 18** - UI library
- **Vite** - Build tool & dev server
- **Fetch API** - HTTP requests
- **CSS3** - Styling (No CSS framework)

## 🐛 Troubleshooting

**Error: CORS**
- Đảm bảo backend API chạy trên `http://localhost:8000`
- Kiểm tra `.env.local` có `VITE_API_URL` đúng

**Error: Port 5173 đã sử dụng**
```bash
npm run dev -- --port 5174
```

**Build error**
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```
