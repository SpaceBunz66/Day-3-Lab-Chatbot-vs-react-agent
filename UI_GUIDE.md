# 📘 Tài liệu Giao diện — Trợ Lý AI Hỗ Trợ Phụ Huynh

Tài liệu này giải thích **cấu trúc** và **logic** của giao diện chat (frontend) và cách
nó nối với backend gọi LLM.

---

## 1. Tổng quan kiến trúc

```
Trình duyệt (UI)                     Server (Python)
┌─────────────────────────┐          ┌──────────────────────────┐
│ index.html  (bố cục)     │          │ server.py  (FastAPI)      │
│ style.css   (giao diện)  │  fetch   │  GET  /          → HTML   │
│ app.js      (logic)      │ ───────► │  POST /api/chat  → gọi LLM│
└─────────────────────────┘  JSON     └──────────┬───────────────┘
                                                  │
                                       factory.py → chọn provider
                                                  │
                                       OpenAI / Gemini / Local .generate()
```

- **Frontend** = 3 file tĩnh trong `static/`: `index.html`, `style.css`, `app.js`.
- **Backend** = `server.py`: phục vụ file tĩnh + 1 API `/api/chat`.
- Khi người dùng gửi câu hỏi → JavaScript gọi `POST /api/chat` → server gọi LLM →
  trả về câu trả lời (JSON) → JavaScript hiển thị lên màn hình.

---

## 2. Bố cục màn hình (`index.html`)

Toàn bộ nằm trong `<div class="app">`, chia **3 cột ngang** (dùng flexbox):

```
┌────┬──────────────┬─────────────────────────────────────┐
│icon│   sidebar    │             main                     │
│rail│  (hội thoại) │  ┌─────────────────────────────────┐ │
│    │              │  │ topbar (header)                 │ │
│ 💬 │ + Hội thoại  │  ├─────────────────────────────────┤ │
│ 📚 │ 🔍 Tìm kiếm  │  │ content (welcome / messages)    │ │
│ ⬆️ │ [tabs]       │  │                                 │ │
│ 🕘 │ danh sách    │  ├─────────────────────────────────┤ │
│ ⚙️ │ hội thoại    │  │ composer (ô nhập câu hỏi)        │ │
└────┴──────────────┴─────────────────────────────────────┘
```

### 2.1. `.icon-rail` — Thanh icon trái
- Cột hẹp ngoài cùng, chứa các nút điều hướng (Chat, Thư viện, Tải lên, Lịch sử, Cài đặt).
- Hiện tại mang tính **trang trí** — chưa gắn hành động. Nút có class `active` được tô sáng.

### 2.2. `.sidebar` — Lịch sử hội thoại
| Phần | id / class | Vai trò |
|------|-----------|---------|
| Tiêu đề | `.sidebar-title` | Tên ứng dụng |
| Nút tạo mới | `#newChatBtn` | Bắt đầu một cuộc hội thoại mới |
| Ô tìm kiếm | `#searchInput` | Lọc danh sách hội thoại theo từ khoá |
| Tabs | `.tabs` | Lọc theo thời gian (hiện chỉ đổi giao diện) |
| Số đếm | `#convoCount` | Hiển thị "N cuộc hội thoại" |
| Danh sách | `#convoList` | Nơi JS render các hội thoại đã lưu |

### 2.3. `.main` — Khu vực chính, chia 3 tầng dọc
1. **`.topbar`** (header): logo, nút đổi giao diện sáng/tối `#themeBtn`, chuông thông báo, thông tin người dùng.
2. **`.content`**: vùng cuộn, chứa **2 trạng thái**:
   - **`#welcome`** — màn hình chào (icon 🎓, tiêu đề, chip "Tra cứu nhanh", 4 thẻ gợi ý). Hiện khi **chưa có tin nhắn**.
   - **`#messages`** — danh sách bong bóng chat. Hiện khi **đã có tin nhắn** (ẩn `#welcome`).
3. **`.composer`** (footer): ô nhập `#questionInput`, nút ghi âm (trang trí), nút gửi `#sendBtn`, dòng ghi chú.

> **Quy tắc hiển thị:** chỉ một trong hai (`#welcome` **hoặc** `#messages`) hiện tại một thời điểm — do hàm `renderMessages()` quyết định.

---

## 3. Giao diện (`style.css`)

- **Biến màu** khai báo trong `:root` (chế độ sáng) và `[data-theme="dark"]` (chế độ tối).
  Đổi theme chỉ cần đổi thuộc tính `data-theme` trên `<html>` → toàn bộ màu tự cập nhật.
  ```css
  :root        { --bg: #f7f8fa; --primary: #4f46e5; ... }
  [data-theme="dark"] { --bg: #14161c; ... }
  ```
- **Layout** dùng `display: flex` (3 cột) và flex dọc trong `.main`.
- Các khối chính: `.icon-rail`, `.sidebar`, `.topbar`, `.welcome`, `.suggestions`
  (lưới 2×2), `.messages` (bong bóng), `.composer`.
- Bong bóng chat: `.msg.user` (của phụ huynh, nền xanh, canh phải) và
  `.msg.bot` (của AI, nền trắng, canh trái).

---

## 4. Logic JavaScript (`app.js`)

### 4.1. Trạng thái & lưu trữ
```js
let conversations = [...]   // mảng các hội thoại
let currentId = null        // id hội thoại đang mở
```
- Mỗi hội thoại: `{ id, title, messages: [{role, content, meta}] }`.
- Lưu vào **`localStorage`** (khoá `"convos"`) → tải lại trang vẫn còn lịch sử.
- `save()` ghi localStorage rồi vẽ lại sidebar.

### 4.2. Các hàm render (vẽ giao diện)
| Hàm | Nhiệm vụ |
|-----|----------|
| `renderConvoList()` | Vẽ danh sách hội thoại ở sidebar, áp dụng bộ lọc tìm kiếm, cập nhật số đếm |
| `renderMessages()` | Quyết định hiện `#welcome` hay `#messages`; vẽ lại toàn bộ bong bóng |
| `addBubble(role, content, meta)` | Tạo 1 bong bóng chat (escape HTML để an toàn) |

### 4.3. Luồng gửi câu hỏi — hàm `send()`
```
1. Lấy nội dung câu hỏi (từ ô nhập hoặc từ thẻ gợi ý)
2. Nếu chưa có hội thoại → tạo mới; đặt tiêu đề = 40 ký tự đầu câu hỏi
3. Thêm tin nhắn "user" → lưu → vẽ lại
4. Hiện bong bóng "Đang trả lời..." (tạm thời)
5. fetch POST /api/chat  { question }
6. Nhận JSON:
     - ok=true  → thêm tin nhắn "bot" + meta (latency, tokens, provider)
     - ok=false → hiện thông báo lỗi
7. Lưu → vẽ lại
```

### 4.4. Gắn sự kiện (event)
- `#sendBtn` click → `send()`
- `#questionInput` nhấn **Enter** (không Shift) → `send()`; ô input tự giãn chiều cao.
- Mỗi `.suggest-card` click → `send(nội dung thẻ)` (hỏi luôn câu gợi ý).
- `#searchInput` gõ → lọc danh sách hội thoại.
- `.tab` click → đổi tab đang chọn (giao diện).
- `#themeBtn` click → bật/tắt chế độ tối, đổi icon 🌙/☀️.

---

## 5. Backend (`server.py`)

### 5.1. Endpoint `POST /api/chat`
- Nhận JSON `{ question, provider?, model? }` (định nghĩa bằng `ChatRequest`).
- Gọi `get_provider(...)` (trong `core/factory.py`) để chọn LLM theo `.env`.
- Gọi `llm.generate(question, system_prompt=SYSTEM_PROMPT)`.
- Trả về:
  ```json
  { "ok": true, "content": "...", "usage": {...}, "latency_ms": 123, "provider": "openai" }
  ```
  Nếu lỗi (thiếu API key, v.v.): `{ "ok": false, "error": "..." }`.

### 5.2. `SYSTEM_PROMPT` — "tính cách" của trợ lý
Đoạn văn bản định hình **vai trò**: trả lời tiếng Việt, gọi "quý phụ huynh", tập trung
vào việc học của con (điểm số, phương pháp học, tâm lý, phối hợp nhà trường), không bịa
thông tin. Đây là nơi điều chỉnh giọng điệu & phạm vi trả lời của AI.

### 5.3. Phục vụ file tĩnh
- `GET /` → trả `static/index.html`.
- `/static/*` → trả các file `style.css`, `app.js`.

---

## 6. Cách chạy

```bash
# Tạo .env và điền API key (1 lần)
cp .env.example .env        # rồi điền OPENAI_API_KEY=...

# Chạy server từ thư mục gốc project
python3 -m uvicorn src.fe.server:app --reload --port 8000
```
Mở trình duyệt: <http://localhost:8000>

---

## 7. Sơ đồ luồng một lần hỏi/đáp

```
Người dùng gõ câu hỏi / bấm thẻ gợi ý
        │  (app.js: send)
        ▼
POST /api/chat { question }
        │  (server.py)
        ▼
factory.get_provider()  →  chọn OpenAI / Gemini / Local
        │
        ▼
llm.generate(question, system_prompt=SYSTEM_PROMPT)
        │
        ▼
{ content, usage, latency_ms }  ──►  app.js vẽ bong bóng trả lời + meta
```

---

## 8. Phần CHƯA có (gợi ý nâng cấp)

- **Dữ liệu thật của học sinh** (điểm, thời khoá biểu, đi học muộn, nhận xét) — hiện AI
  trả lời chung chung vì chưa có nguồn dữ liệu. Cần thêm file/DB rồi cho AI tra cứu (RAG).
- **Streaming** chữ hiện dần (đang dùng `generate()` trả về một lần).
- Các nút trong **icon rail** và **tabs thời gian** mới là giao diện, chưa gắn chức năng.
