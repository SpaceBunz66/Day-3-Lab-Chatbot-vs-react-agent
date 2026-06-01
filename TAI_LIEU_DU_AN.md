# 📋 Tài liệu Dự án — Trợ Lý AI Hỗ Trợ Phụ Huynh

> **E-School Parent Assistant** — Trợ lý AI đồng hành cùng phụ huynh học sinh
> Tài liệu tổng hợp dành cho Business Analyst, kỹ thuật và các bên liên quan.
> Phiên bản: 1.0 · Cập nhật: 01/06/2026 · Trạng thái: Prototype (nguyên mẫu)

---

## Mục lục
1. [Tổng quan sản phẩm](#1-tổng-quan-sản-phẩm)
2. [Mục tiêu & Phạm vi](#2-mục-tiêu--phạm-vi)
3. [Đối tượng người dùng & các bên liên quan](#3-đối-tượng-người-dùng--các-bên-liên-quan)
4. [Yêu cầu nghiệp vụ (Business Requirements)](#4-yêu-cầu-nghiệp-vụ)
5. [Yêu cầu chức năng (Functional Requirements)](#5-yêu-cầu-chức-năng)
6. [Yêu cầu phi chức năng (Non-functional)](#6-yêu-cầu-phi-chức-năng)
7. [Kiến trúc hệ thống](#7-kiến-trúc-hệ-thống)
8. [Luồng nghiệp vụ chính](#8-luồng-nghiệp-vụ-chính)
9. [Đặc tả API](#9-đặc-tả-api)
10. [Bộ công cụ AI & Cơ chế ReAct](#10-bộ-công-cụ-ai--cơ-chế-react)
11. [Guardrails & Kiểm soát nội dung](#11-guardrails--kiểm-soát-nội-dung)
12. [Giám sát & Đo lường (Telemetry)](#12-giám-sát--đo-lường-telemetry)
13. [Công nghệ & Cấu hình](#13-công-nghệ--cấu-hình)
14. [Cấu trúc mã nguồn](#14-cấu-trúc-mã-nguồn)
15. [Hiện trạng vs. Khoảng trống (Gap Analysis)](#15-hiện-trạng-vs-khoảng-trống)
16. [Lộ trình phát triển (Roadmap)](#16-lộ-trình-phát-triển)
17. [Rủi ro & Giả định](#17-rủi-ro--giả-định)
18. [Thuật ngữ](#18-thuật-ngữ)

---

## 1. Tổng quan sản phẩm

**Trợ Lý AI Hỗ Trợ Phụ Huynh** là một trợ lý hội thoại (chatbot) ứng dụng AI, giúp **phụ huynh học sinh** theo dõi sát sao tình hình học tập của con và nhận lời khuyên kèm cặp thực tế.

Sản phẩm trả lời bằng **tiếng Việt**, với giọng văn lịch sự, ân cần và mang tính xây dựng, tập trung vào 4 nhóm thông tin cốt lõi:

| Nhóm thông tin | Ví dụ câu hỏi của phụ huynh |
|----------------|------------------------------|
| 📊 **Điểm số** | "Cho tôi xem điểm các môn học của con" |
| 🗓️ **Thời khoá biểu** | "Thời khoá biểu tuần này của con như thế nào?" |
| ⏰ **Chuyên cần** | "Tháng này con tôi đi học muộn mấy buổi?" |
| 📝 **Nhận xét giáo viên** | "Nhận xét của thầy cô về con trong tuần qua?" |

Về mặt kỹ thuật, sản phẩm được xây dựng theo hướng **ReAct Agent** (Reasoning + Acting): AI không chỉ "trò chuyện" mà còn biết **gọi công cụ** để tra cứu dữ liệu thực và **tra cứu giáo trình (RAG)** để đưa ra lời khuyên có căn cứ.

> **Bối cảnh:** Dự án bắt nguồn từ một bài lab đào tạo ("Lab 3: Chatbot vs ReAct Agent — Industry Edition") nhằm minh hoạ sự khác biệt giữa chatbot thông thường và agent có khả năng lập luận đa bước. Kịch bản nghiệp vụ được chọn là Trợ lý phụ huynh học sinh.

---

## 2. Mục tiêu & Phạm vi

### 2.1. Mục tiêu sản phẩm
- Giúp phụ huynh **chủ động nắm bắt** tình hình học tập của con mà không cần liên hệ trực tiếp giáo viên cho từng thắc mắc nhỏ.
- Biến dữ liệu khô khan (điểm, lỗi chuyên cần) thành **lời khuyên dễ tiếp nhận**, có tính đồng hành và xây dựng.
- Cung cấp lời khuyên kèm cặp **dựa trên giáo trình nhà trường** (qua RAG), không "bịa".

### 2.2. Mục tiêu kỹ thuật
- Xây dựng vòng lặp **ReAct** (Thought → Action → Observation) ổn định, có khả năng tự sửa lỗi định dạng.
- Kiến trúc **provider-agnostic**: dễ dàng chuyển đổi giữa các nhà cung cấp LLM (OpenAI / Gemini / Local / Ollama).
- Tích hợp **telemetry** chuẩn công nghiệp: log JSON, đo token, latency, chi phí.

### 2.3. Trong phạm vi (In-scope)
- Giao diện chat web (1 trang) cho phụ huynh.
- Trả lời các câu hỏi về học tập, điểm, chuyên cần, thời khoá biểu, nhận xét, lời khuyên.
- Kiểm soát phạm vi (off-topic guardrails).
- Lưu lịch sử hội thoại phía trình duyệt.

### 2.4. Ngoài phạm vi (Out-of-scope — giai đoạn hiện tại)
- Xác thực/đăng nhập, phân quyền phụ huynh ↔ học sinh.
- Cơ sở dữ liệu học sinh thật (hiện dùng dữ liệu mô phỏng trong tool).
- Ứng dụng di động.
- Tích hợp trực tiếp với hệ thống quản lý trường học (LMS/SIS) thật.

---

## 3. Đối tượng người dùng & các bên liên quan

| Vai trò | Mô tả | Nhu cầu chính |
|---------|-------|----------------|
| **Phụ huynh** (người dùng chính) | Cha mẹ học sinh | Theo dõi việc học, hiểu ý nghĩa điểm số, biết cách đồng hành cùng con |
| **Học sinh** | Đối tượng được nói đến trong dữ liệu | (Gián tiếp) được hỗ trợ học tập tốt hơn |
| **Giáo viên / Nhà trường** | Nguồn dữ liệu & nhận xét | Giảm tải các thắc mắc lặp lại; thông tin tới phụ huynh nhất quán |
| **Quản trị/Kỹ thuật** | Vận hành hệ thống | Giám sát chi phí, độ trễ, độ tin cậy của agent |

---

## 4. Yêu cầu nghiệp vụ

| Mã | Yêu cầu nghiệp vụ |
|----|-------------------|
| BR-01 | Phụ huynh có thể tra cứu thông tin học tập của con bằng ngôn ngữ tự nhiên (tiếng Việt). |
| BR-02 | Hệ thống chỉ phản hồi các chủ đề liên quan đến học tập của học sinh; từ chối lịch sự các chủ đề ngoài phạm vi. |
| BR-03 | Phản hồi phải mang tính xây dựng: giải thích ý nghĩa điểm số, ghi nhận nỗ lực, gợi ý cải thiện. |
| BR-04 | Lời khuyên kèm cặp phải dựa trên giáo trình/kế hoạch giảng dạy của trường (không suy diễn vô căn cứ). |
| BR-05 | Phụ huynh xem lại được lịch sử các cuộc hội thoại đã hỏi. |
| BR-06 | Hệ thống phải minh bạch: nhắc rằng AI mang tính tham khảo, không thay thế tư vấn trực tiếp của giáo viên. |

---

## 5. Yêu cầu chức năng

### 5.1. Giao diện chat (Frontend)
- **FR-01** Hiển thị màn hình chào với 4 thẻ gợi ý câu hỏi nhanh khi chưa có hội thoại.
- **FR-02** Cho phép nhập câu hỏi tự do; gửi bằng nút hoặc phím Enter (Shift+Enter để xuống dòng).
- **FR-03** Hiển thị bong bóng chat hai phía (phụ huynh / AI) kèm hiệu ứng "Đang trả lời…".
- **FR-04** Tạo, tìm kiếm, mở lại các cuộc hội thoại; tự đặt tiêu đề theo 40 ký tự đầu câu hỏi.
- **FR-05** Lưu lịch sử hội thoại vào `localStorage` (giữ lại sau khi tải lại trang).
- **FR-06** Hiển thị metadata mỗi câu trả lời: độ trễ (ms), số token, provider.
- **FR-07** Chuyển đổi giao diện sáng/tối (light/dark theme).

### 5.2. Xử lý hội thoại (Backend)
- **FR-08** Nhận câu hỏi qua API `POST /api/chat`, gọi LLM provider tương ứng, trả về câu trả lời + telemetry.
- **FR-09** Cho phép chỉ định `provider` và `model` theo từng request (mặc định lấy từ `.env`).
- **FR-10** Ghi log mỗi lượt chat ở định dạng JSON có cấu trúc.

### 5.3. Lập luận của Agent (ReAct) — *đã xây ở tầng agent, xem [§15](#15-hiện-trạng-vs-khoảng-trống)*
- **FR-11** Thực thi vòng lặp Thought → Action → Observation, tối đa `max_steps` (mặc định 5) bước.
- **FR-12** Phân tích (parse) lời gọi công cụ dạng `tool_name(arg=value, ...)` với tự động ép kiểu (int/float/str).
- **FR-13** Thực thi công cụ và đưa kết quả (Observation) trở lại ngữ cảnh cho bước tiếp theo.
- **FR-14** Tự sửa lỗi định dạng (self-correction) khi LLM trả về sai cú pháp; chống lặp vô hạn bằng `max_steps`.

---

## 6. Yêu cầu phi chức năng

| Mã | Loại | Yêu cầu |
|----|------|---------|
| NFR-01 | Hiệu năng | Mục tiêu phản hồi trong khoảng 200ms–2s (theo [EVALUATION.md](EVALUATION.md)). |
| NFR-02 | Khả mở rộng | Kiến trúc Provider Pattern cho phép thêm LLM mới mà không sửa lõi. |
| NFR-03 | Quan sát được (Observability) | Mọi sự kiện & metric ghi log JSON trong `logs/` để phân tích lỗi. |
| NFR-04 | Đa ngôn ngữ AI | Lập luận nội bộ bằng tiếng Anh, phản hồi cuối cùng bằng tiếng Việt. |
| NFR-05 | Chi phí | Theo dõi token & ước tính chi phí từng request. |
| NFR-06 | Bảo mật/Riêng tư | (Mục tiêu tương lai) chỉ phụ huynh truy cập được dữ liệu của con mình. |
| NFR-07 | Triển khai | Cùng một server FastAPI phục vụ cả UI và API → không cần xử lý CORS. |

---

## 7. Kiến trúc hệ thống

```
   Trình duyệt (Frontend)                  Server (FastAPI - server.py)
┌──────────────────────────┐            ┌──────────────────────────────┐
│ index.html  (bố cục)      │  GET /     │ @app.get("/")   → trả HTML    │
│ style.css   (giao diện)   │ ─────────► │ StaticFiles     → css/js      │
│ app.js      (logic)       │            │                              │
│                          │ POST       │ @app.post("/api/chat")        │
│  send() ───────────────► │ /api/chat  │   ├─ factory.get_provider()   │
│         { question }      │ ─────────► │   └─ llm.generate(...)        │
│                          │ ◄───────── │   → { ok, content, usage,     │
└──────────────────────────┘  JSON      │       latency_ms, provider }  │
                                        └───────────────┬──────────────┘
                                                        │ Provider Pattern
                          ┌─────────────────┬───────────┼─────────────┐
                          ▼                 ▼           ▼             ▼
                     OpenAIProvider   GeminiProvider  LocalProvider  OllamaProvider
                       (GPT-4o)       (Gemini 1.5)    (Phi-3 GGUF)   (Llama 3.x)
```

### Thành phần chính
- **Frontend tĩnh** (`src/fe/static/`): `index.html`, `style.css`, `app.js` — giao diện chat 3 cột (icon rail · sidebar lịch sử · khu vực chat chính).
- **Backend** (`src/fe/server.py`): FastAPI phục vụ file tĩnh + endpoint `/api/chat`.
- **Factory** (`src/core/factory.py`): "công tắc" chọn LLM provider theo cấu hình.
- **Provider Layer** (`src/core/*_provider.py`): các lớp triển khai chung interface `LLMProvider`.
- **Agent** (`src/agent/agent.py`): lớp `ReActAgent` thực thi vòng lặp lập luận + gọi công cụ.
- **Telemetry** (`src/telemetry/`): `logger.py` (log JSON) + `metrics.py` (đo token/latency/chi phí).

### Mẫu thiết kế then chốt — Provider Pattern
Tất cả nhà cung cấp LLM kế thừa lớp trừu tượng [LLMProvider](src/core/llm_provider.py) với 2 phương thức `generate()` và `stream()`, trả về cấu trúc thống nhất: `{ content, usage, latency_ms, provider }`. Nhờ vậy việc đổi từ OpenAI sang Gemini/Local/Ollama chỉ là thay cấu hình, không sửa logic nghiệp vụ.

---

## 8. Luồng nghiệp vụ chính

### 8.1. Luồng hỏi/đáp (bản web hiện tại)
```
Phụ huynh gõ câu hỏi / bấm thẻ gợi ý
        │  (app.js: send)
        ▼
POST /api/chat { question }
        │  (server.py)
        ▼
factory.get_provider()  →  chọn OpenAI / Gemini / Local / Ollama
        │
        ▼
llm.generate(question, system_prompt)
        │
        ▼
{ content, usage, latency_ms } ──► app.js vẽ bong bóng trả lời + meta
                                    (đồng thời ghi log UI_CHAT)
```

### 8.2. Luồng ReAct Agent (thiết kế đầy đủ — xem `agent.py`)
```
Câu hỏi phụ huynh
   │
   ▼  Bước 1..N (tối đa max_steps)
 [Thought]  AI lập luận: cần dữ liệu gì?
   │
   ├─► [Action] gọi công cụ, ví dụ get_student_grades(student_name="...")
   │        │
   │        ▼ [Observation] hệ thống trả kết quả → đưa lại vào ngữ cảnh
   │   (lặp lại nếu cần thêm dữ liệu / lời khuyên RAG)
   │
   └─► [Final Answer] tổng hợp phản hồi tiếng Việt, ân cần & xây dựng
```

---

## 9. Đặc tả API

### `POST /api/chat`
**Request**
```json
{
  "question": "Tháng này con tôi đi học muộn mấy buổi?",
  "provider": "ollama",   // tuỳ chọn — bỏ trống dùng DEFAULT_PROVIDER
  "model": "llama3.2:3b"  // tuỳ chọn — bỏ trống dùng DEFAULT_MODEL
}
```

**Response — thành công**
```json
{
  "ok": true,
  "content": "Câu trả lời của AI...",
  "usage": { "prompt_tokens": 30, "completion_tokens": 80, "total_tokens": 110 },
  "latency_ms": 1234,
  "provider": "ollama"
}
```

**Response — lỗi**
```json
{ "ok": false, "error": "mô tả lỗi (thiếu API key, Ollama chưa chạy, ...)" }
```

### Các endpoint khác
| Đường dẫn | Method | Trả về |
|-----------|--------|--------|
| `/` | GET | `static/index.html` |
| `/static/*` | GET | File tĩnh (css, js) |
| `/docs` | GET | Swagger UI tự sinh của FastAPI |

> Quy ước: mọi API đặt dưới tiền tố `/api/...` và trả JSON có trường `ok`. Tham khảo chi tiết tại [CONNECT_GUIDE.md](CONNECT_GUIDE.md).

---

## 10. Bộ công cụ AI & Cơ chế ReAct

Lớp [ReActAgent](src/agent/agent.py) điều phối vòng lặp lập luận. System prompt định nghĩa định dạng bắt buộc:

- `Thought:` (tiếng Anh) — dòng suy nghĩ của agent.
- `Action: tool_name(args)` — gọi đúng một công cụ.
- `Observation:` — **do hệ thống tự điền** sau khi thực thi công cụ.
- `Final Answer:` (tiếng Việt) — câu trả lời cuối cho phụ huynh.

### Các công cụ (tools) được tham chiếu trong thiết kế
| Công cụ | Mục đích |
|---------|----------|
| `get_student_grades(student_name)` | Lấy điểm các môn của học sinh |
| `get_student_attendance(student_name)` | Lấy thông tin chuyên cần / đi học muộn |
| `search_curriculum_and_advice(subject, week)` | Tra cứu giáo trình & lời khuyên kèm cặp (RAG) |

> ⚠️ **Lưu ý hiện trạng:** Các tool trên được mô tả trong system prompt & báo cáo cá nhân nhưng **chưa có file hiện thực trong repo** (thư mục `src/tools/` được nhắc trong README nhưng chưa tồn tại). Xem [§15](#15-hiện-trạng-vs-khoảng-trống).

### Bộ phân tích tham số (`_parse_args`)
Hỗ trợ 3 định dạng đối số: `key=value` (dict), danh sách phân tách dấu phẩy (list), và đối số đơn — kèm tự động ép kiểu int/float/str. Bộ `_execute_tool` dùng `inspect.signature` để lọc tham số hợp lệ, tránh lỗi keyword.

---

## 11. Guardrails & Kiểm soát nội dung

Định nghĩa trong system prompt của agent ([agent.py:30-36](src/agent/agent.py#L30-L36)):

- **Giới hạn phạm vi:** Chỉ trả lời về học tập, điểm số, chuyên cần, thời khoá biểu, lời khuyên kèm cặp.
- **Off-topic control:** Với yêu cầu ngoài phạm vi (nấu ăn, thời tiết, giải trí, chính trị…) hoặc nội dung thô tục/nhạy cảm → **dừng ngay tại bước 1, không gọi công cụ**, đi thẳng tới `Final Answer` để từ chối lịch sự.
- **Tone & Voice:** Lịch sự, ân cần, đồng cảm, mang tính xây dựng; tránh đưa điểm số/lỗi chuyên cần một cách khô khan.
- **Minh bạch ở UI:** Dòng ghi chú "Trợ lý AI mang tính tham khảo, không thay thế tư vấn trực tiếp từ giáo viên. AI có thể mắc lỗi."

---

## 12. Giám sát & Đo lường (Telemetry)

### Logger ([logger.py](src/telemetry/logger.py))
Ghi sự kiện JSON ra **console + file** `logs/YYYY-MM-DD.log`. Các loại sự kiện: `AGENT_START`, `AGENT_STEP`, `LLM_RESPONSE`, `TOOL_EXECUTION`, `PARSER_ERROR`, `AGENT_END`, `AGENT_TIMEOUT`, `UI_CHAT`, `LLM_METRIC`.

### Metrics ([metrics.py](src/telemetry/metrics.py))
`PerformanceTracker.track_request()` ghi lại cho mỗi lượt gọi LLM: provider, model, prompt/completion/total tokens, latency_ms, và **ước tính chi phí** (hiện là công thức mock: `total_tokens/1000 × 0.01`).

### Chỉ số đánh giá chuẩn ([EVALUATION.md](EVALUATION.md))
- **Token efficiency** — prompt vs completion, phân tích chi phí.
- **Latency** — TTFT & tổng thời gian (gồm cả thực thi tool).
- **Loop count** — số vòng Thought→Action; chất lượng kết thúc.
- **Failure analysis** — parser error, hallucination tool, timeout.

---

## 13. Công nghệ & Cấu hình

### Stack công nghệ
| Lớp | Công nghệ |
|-----|-----------|
| Frontend | HTML5, CSS3 (biến màu + flexbox), Vanilla JavaScript, localStorage |
| Backend | Python 3, FastAPI, Uvicorn, Pydantic |
| LLM providers | OpenAI SDK, Google Generative AI, llama-cpp-python (GGUF), Ollama (HTTP) |
| Cấu hình | python-dotenv (`.env`) |
| Kiểm thử | pytest |

### Biến môi trường chính ([.env.example](.env.example))
```env
OPENAI_API_KEY=...
GEMINI_API_KEY=...
LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
DEFAULT_PROVIDER=ollama        # openai | google | local | ollama
DEFAULT_MODEL=llama3.2:3b
LOG_LEVEL=INFO
```

### Cách chạy
```bash
cp .env.example .env            # điền API key (nếu dùng OpenAI/Gemini)
pip install -r requirements.txt
python3 -m uvicorn src.fe.server:app --reload --port 8000
# Mở: http://localhost:8000
```

---

## 14. Cấu trúc mã nguồn

```
.
├── src/
│   ├── agent/
│   │   └── agent.py            # ReActAgent — vòng lặp Thought/Action/Observation
│   ├── core/
│   │   ├── llm_provider.py     # Interface trừu tượng LLMProvider
│   │   ├── factory.py          # get_provider() — chọn provider (dùng bởi server)
│   │   ├── provider_factory.py # create_provider_from_env() — biến thể theo .env
│   │   ├── openai_provider.py  # OpenAI (GPT-4o)
│   │   ├── gemini_provider.py  # Google Gemini
│   │   ├── local_provider.py   # Local GGUF qua llama-cpp
│   │   └── ollama_provider.py  # Ollama HTTP
│   ├── fe/
│   │   ├── server.py           # FastAPI: phục vụ UI + /api/chat
│   │   └── static/
│   │       ├── index.html      # Bố cục giao diện
│   │       ├── style.css       # Giao diện (light/dark)
│   │       └── app.js          # Logic chat + localStorage
│   └── telemetry/
│       ├── logger.py           # Log JSON có cấu trúc
│       └── metrics.py          # Theo dõi token/latency/chi phí
├── tests/                      # test_local, test_ollama, test_provider_from_env
├── report/                     # Báo cáo nhóm & cá nhân (bối cảnh lab)
├── requirements.txt
├── .env.example
├── README.md / UI_GUIDE.md / CONNECT_GUIDE.md / EVALUATION.md / SCORING.md / INSTRUCTOR_GUIDE.md
└── TAI_LIEU_DU_AN.md           # (tài liệu này)
```

> Ghi chú: tồn tại **hai factory** gần giống nhau — [factory.py](src/core/factory.py) (`get_provider`, được server dùng) và [provider_factory.py](src/core/provider_factory.py) (`create_provider_from_env`, có thêm cấu hình `n_ctx`, `n_threads`). Nên hợp nhất để tránh trùng lặp (xem [§15](#15-hiện-trạng-vs-khoảng-trống)).

---

## 15. Hiện trạng vs. Khoảng trống

### ✅ Đã có
- Giao diện chat hoàn chỉnh, đẹp, có lịch sử hội thoại (localStorage), light/dark.
- Backend FastAPI + 4 LLM provider hoạt động qua Provider Pattern.
- Lớp `ReActAgent` với parser tham số linh hoạt, self-correction, chống lặp.
- Telemetry: log JSON + đo token/latency/chi phí.
- Guardrails phạm vi & tone định nghĩa trong system prompt của agent.

### ⚠️ Khoảng trống quan trọng (ưu tiên cho BA/PO)

| # | Khoảng trống | Tác động | Mức ưu tiên |
|---|--------------|----------|-------------|
| G1 | **Web chưa dùng Agent.** [server.py](src/fe/server.py) gọi thẳng `llm.generate()` với `SYSTEM_PROMPT` **rỗng** — không qua `ReActAgent`, không có guardrails, không gọi tool. Bản web hiện chỉ là chatbot thuần. | Cao — sản phẩm thực tế chưa thể hiện đúng giá trị cốt lõi (tra cứu dữ liệu + RAG). | 🔴 Cao |
| G2 | **Chưa có công cụ (tools).** `src/tools/` được nhắc trong README nhưng chưa tồn tại; các tool `get_student_grades`, `get_student_attendance`, `search_curriculum_and_advice` chưa được hiện thực/đăng ký. | Cao — AI không truy cập được dữ liệu thật, dễ "bịa". | 🔴 Cao |
| G3 | **Chưa có dữ liệu học sinh thật.** Không có DB/nguồn dữ liệu; câu trả lời chung chung (xác nhận trong [UI_GUIDE.md §8](UI_GUIDE.md)). | Cao | 🔴 Cao |
| G4 | **Chưa có RAG thật.** Lời khuyên giáo trình mới ở mức ý tưởng. | Trung bình | 🟠 TB |
| G5 | **Chưa xác thực/phân quyền.** Bất kỳ ai cũng truy cập mọi dữ liệu — chưa đảm bảo riêng tư học bạ. | Cao (khi lên production) | 🟠 TB |
| G6 | **Chưa streaming.** Provider có `stream()` nhưng UI dùng `generate()` (chờ trả một lần). | Thấp (UX) | 🟢 Thấp |
| G7 | **Trùng lặp factory.** `factory.py` vs `provider_factory.py`. | Thấp (kỹ thuật) | 🟢 Thấp |
| G8 | **Nút UI trang trí.** Icon rail (Thư viện, Tải lên, Lịch sử, Cài đặt) và tabs thời gian chưa gắn chức năng. | Thấp | 🟢 Thấp |
| G9 | **Chi phí mock.** `_calculate_cost` dùng hằng số giả, chưa theo bảng giá thật. | Thấp | 🟢 Thấp |

---

## 16. Lộ trình phát triển (Roadmap)

### Giai đoạn 1 — Kết nối Agent vào Web (đóng G1, G2, G3) 
- Thay luồng `server.py` để gọi `ReActAgent` thay vì `llm.generate()` trực tiếp.
- Hiện thực thư mục `src/tools/` với 3 công cụ cốt lõi (grades, attendance, curriculum) trên dữ liệu mô phỏng (mock JSON/`STUDENT_DB`).
- Đưa guardrails phạm vi vào luồng thực tế của web.

### Giai đoạn 2 — Dữ liệu & RAG thật (đóng G3, G4) 
- Kết nối nguồn dữ liệu học sinh thật (file/DB hoặc API trường học).
- Triển khai RAG với Vector DB (Qdrant/ChromaDB), Hybrid Search + Reranker cho lời khuyên giáo trình.

### Giai đoạn 3 — An toàn & Sản xuất (đóng G5) 
- Xác thực phụ huynh & phân quyền truy cập đúng dữ liệu của con.
- Guardrails nâng cao (NeMo Guardrails / Llama Guard) lọc nội dung nhạy cảm.
- Thực thi tool bất đồng bộ song song (`asyncio.gather`) để giảm latency.

### Giai đoạn 4 — Hoàn thiện trải nghiệm (đóng G6, G8, G9) 
- Streaming chữ hiện dần.
- Gắn chức năng cho icon rail & tabs; lọc lịch sử theo thời gian.
- Tính chi phí theo bảng giá thật theo model; dashboard giám sát.

---

## 17. Rủi ro & Giả định

### Rủi ro
- **Ảo tưởng (hallucination):** Khi chưa có tool/dữ liệu thật, AI có thể bịa điểm số → rủi ro uy tín. (Giảm thiểu: Giai đoạn 1–2.)
- **Riêng tư dữ liệu học bạ:** Thiếu xác thực có thể lộ thông tin học sinh. (Giảm thiểu: Giai đoạn 3.)
- **Phụ thuộc nhà cung cấp LLM:** Chi phí/độ trễ/khả dụng biến động. (Giảm thiểu: Provider Pattern đã cho phép chuyển đổi.)
- **Mã hoá tiếng Việt:** Lỗi encoding trên Windows từng xảy ra (xem [báo cáo cá nhân](report/individual_reports/REPORT_NGUYEN_VAN_DOAN.md)) — cần cấu hình UTF-8 nhất quán.

### Giả định
- Trường học có thể cung cấp dữ liệu điểm/chuyên cần/nhận xét ở định dạng truy vấn được.
- Mỗi phụ huynh chỉ tra cứu dữ liệu của (các) con mình.
- Người dùng có kết nối internet (trừ khi dùng provider local/Ollama).

---

## 18. Thuật ngữ

| Thuật ngữ | Giải thích |
|-----------|------------|
| **ReAct** | Reasoning + Acting — mô hình agent xen kẽ lập luận (Thought) và hành động (Action) dựa trên quan sát (Observation). |
| **Provider** | Nhà cung cấp/lớp truy cập một mô hình LLM cụ thể (OpenAI, Gemini, Local, Ollama). |
| **RAG** | Retrieval-Augmented Generation — sinh câu trả lời có truy xuất tài liệu (ở đây là giáo trình nhà trường). |
| **Telemetry** | Dữ liệu giám sát vận hành: log sự kiện, token, latency, chi phí. |
| **Guardrails** | Hàng rào kiểm soát phạm vi/nội dung phản hồi của AI. |
| **Token** | Đơn vị văn bản LLM xử lý; cơ sở tính chi phí. |
| **Latency** | Độ trễ phản hồi (ms). |
| **GGUF** | Định dạng mô hình lượng tử hoá chạy local qua llama-cpp. |

---

*Tài liệu được tổng hợp từ toàn bộ mã nguồn và tài liệu hiện có trong dự án. Các mục [§15](#15-hiện-trạng-vs-khoảng-trống) và [§16](#16-lộ-trình-phát-triển) là phần phân tích/đề xuất của BA dựa trên hiện trạng code.*
