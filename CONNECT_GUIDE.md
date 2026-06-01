# 🔌 Hướng dẫn kết nối Frontend ↔ Server (`src/fe`)

Tài liệu này giải thích **cách giao diện (static) nói chuyện với backend `server.py`**:
luồng request/response, hợp đồng API, cách chạy, và cách mở rộng.

---

## 1. Sơ đồ kết nối

```
        Trình duyệt                                  Server (FastAPI)
┌──────────────────────────┐                  ┌────────────────────────────┐
│  static/index.html       │  GET /           │  server.py                 │
│  static/style.css        │ ───────────────► │  @app.get("/")    → HTML    │
│  static/app.js           │  GET /static/*   │  StaticFiles      → css/js  │
│                          │                  │                            │
│  send() trong app.js     │  POST /api/chat  │  @app.post("/api/chat")     │
│                          │ ───────────────► │    get_provider()           │
│                          │   { question }   │    llm.generate(...)        │
│                          │ ◄─────────────── │    → { ok, content, usage } │
└──────────────────────────┘   JSON           └────────────────────────────┘
```

**Cùng một server (`localhost:8000`) phục vụ CẢ giao diện lẫn API** → không cần lo CORS.

---

## 2. Server phục vụ những gì? (`server.py`)

| Đường dẫn                             | Phương thức | Trả về              | Code                                     |
| ------------------------------------- | ----------- | ------------------- | ---------------------------------------- |
| `/`                                   | GET         | `static/index.html` | `@app.get("/")`                          |
| `/static/style.css`, `/static/app.js` | GET         | File tĩnh           | `app.mount("/static", StaticFiles(...))` |
| `/api/chat`                           | POST        | JSON câu trả lời    | `@app.post("/api/chat")`                 |

```python
# server.py — phục vụ file tĩnh
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
```

> ⚠️ Vì `STATIC_DIR` tính theo vị trí `server.py`, nên **`server.py` và thư mục
> `static/` phải nằm cùng trong `src/fe/`**.

---

## 3. Hợp đồng API `/api/chat`

### Frontend GỬI (request)

```json
POST /api/chat
Content-Type: application/json

{
  "question": "Tháng này con tôi đi học muộn mấy buổi?",
  "provider": "ollama",      // tùy chọn — bỏ trống thì dùng DEFAULT_PROVIDER trong .env
  "model": "llama3"          // tùy chọn — bỏ trống thì dùng DEFAULT_MODEL
}
```

Khai báo kiểu dữ liệu trong `server.py`:

```python
class ChatRequest(BaseModel):
    question: str
    provider: str | None = None
    model: str | None = None
```

### Server TRẢ VỀ (response)

✅ Thành công:

```json
{
  "ok": true,
  "content": "Câu trả lời của AI...",
  "usage": {
    "prompt_tokens": 30,
    "completion_tokens": 80,
    "total_tokens": 110
  },
  "latency_ms": 1234,
  "provider": "ollama"
}
```

❌ Lỗi (thiếu key, Ollama chưa chạy...):

```json
{ "ok": false, "error": "mô tả lỗi" }
```

---

## 4. Frontend gọi API thế nào? (`static/app.js`)

Phần lõi nằm trong hàm `send()`:

```js
const res = await fetch("/api/chat", {
  // (1) gọi server
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question }), // (2) gửi câu hỏi
});
const data = await res.json(); // (3) nhận JSON

if (!data.ok) {
  // hiện thông báo lỗi (data.error)
} else {
  // hiện data.content + meta (latency, tokens, provider)
}
```

- Dùng đường dẫn **tương đối** `"/api/chat"` (không ghi full `http://localhost:8000`)
  → frontend luôn gọi đúng server đang phục vụ nó, dù đổi cổng hay domain.
- `data.ok` quyết định hiển thị câu trả lời hay báo lỗi.

---

## 5. Cách chạy & kiểm tra kết nối

### Chạy server (từ THƯ MỤC GỐC project)

```bash
python3 -m uvicorn src.fe.server:app --reload --port 8000
```

Mở: <http://localhost:8000>

### Kiểm tra giao diện được phục vụ

```bash
curl -I http://localhost:8000/            # mong đợi: HTTP 200
curl -I http://localhost:8000/static/app.js
```

### Kiểm tra API (gửi thử 1 câu hỏi)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"xin chào"}'
```

- Trả `{"ok": true, "content": ...}` → kết nối FE↔BE↔LLM thông suốt.
- Trả `{"ok": false, "error": ...}` → đọc `error` (thường là thiếu API key hoặc Ollama chưa chạy).

### Tài liệu API tự động (FastAPI)

Mở <http://localhost:8000/docs> để thử API ngay trên trình duyệt (Swagger UI).

---

## 6. Lỗi kết nối thường gặp

| Triệu chứng                   | Nguyên nhân                      | Khắc phục                                              |
| ----------------------------- | -------------------------------- | ------------------------------------------------------ |
| Mở trang trắng / 404          | Chạy uvicorn sai thư mục         | Chạy từ **gốc project**, lệnh `src.fe.server:app`      |
| CSS/JS không tải (trang xấu)  | Sai mount static hoặc thiếu file | Đảm bảo `static/` nằm cạnh `server.py`                 |
| Bấm gửi không có gì           | Server chưa chạy / sai cổng      | Kiểm tra uvicorn còn chạy, đúng `localhost:8000`       |
| `{"ok": false, ...}`          | Lỗi phía LLM                     | Xem `error`: thiếu key, model sai tên, Ollama chưa bật |
| `ModuleNotFoundError: src...` | Chạy sai thư mục                 | `cd` về gốc project rồi chạy lại                       |

---

## 7. Mở rộng: thêm một endpoint mới

Ví dụ muốn thêm API lấy điểm học sinh:

```python
# server.py
@app.get("/api/grades")
def grades(student: str):
    # ... đọc dữ liệu, trả JSON ...
    return {"ok": True, "student": student, "grades": {...}}
```

Rồi gọi từ `app.js`:

```js
const res = await fetch(`/api/grades?student=An`);
const data = await res.json();
```

> Quy ước nên giữ: mọi API đặt dưới tiền tố `/api/...` và trả JSON có trường `ok`.

---

## 8. Tóm tắt 1 phút

- Một server FastAPI (`server.py`) phục vụ **cả** giao diện (`/`, `/static/*`) **và** API (`/api/chat`).
- Frontend gọi API bằng `fetch("/api/chat", ...)` — đường dẫn tương đối, cùng gốc → không vướng CORS.
- Request: `{ question, provider?, model? }` → Response: `{ ok, content, usage, latency_ms, provider }`.
- Chạy: `python3 -m uvicorn src.fe.server:app --reload --port 8000` từ gốc project.
