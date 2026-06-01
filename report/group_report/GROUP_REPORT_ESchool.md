# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: 22
- **Team Members**: Nguyễn Đức Toàn (2A202600733), Nguyễn Văn Đoan (2A202600795),Phạm Thị Tuyết Nga (2A202600877),Nguyễn Thái Hoàng (2A202600573), Nguyễn Ngô Huy Tùng Anh (2A202600613)

- **Deployment Date**: 2026-06-01

---

## 1. Executive Summary

Hệ thống được xây dựng là một **Trợ lý AI dành cho Phụ huynh** (E-School Parent Assistant), giúp phụ huynh theo dõi điểm số, chuyên cần, sinh hoạt hàng ngày của học sinh và nhận gợi ý lộ trình kèm cặp cá nhân hóa thông qua vòng lặp ReAct.

- **Success Rate**: ~80% trên 31 test case thực tế (log telemetry)
- **Key Outcome**: Agent giải quyết được các câu hỏi đa bước (tra cứu điểm → phân tích → gợi ý tài liệu) mà chatbot thuần túy không thể xử lý chỉ bằng một lần sinh text, đặc biệt các flow yêu cầu xác thực OTP trước khi cấp dữ liệu nhạy cảm.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

```
User Input
    │
    ▼
┌──────────────────────────────────────────────────┐
│  ReActAgent.run()                                │
│                                                  │
│  1. Greeting detection → short-circuit           │
│  2. Student ID / intent detection                │
│  3. Build system prompt + conversation history   │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  LOOP (max_steps = 5)                      │  │
│  │  Thought: LLM reasons about what to do     │  │
│  │  Action:  parse tool_name(args)            │  │
│  │  Observation: invoke tool → string result  │  │
│  │  → inject Observation back into prompt     │  │
│  │  → repeat until "Final Answer:" found      │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  4. _clean_response() – strip internal labels    │
│  5. Return final answer to Frontend (FastAPI)    │
└──────────────────────────────────────────────────┘
```

Cơ chế tự sửa lỗi (self-correction): khi LLM trả về `Final Answer` bọc trong markdown code block hoặc sai định dạng, `_clean_response` và fallback parser trong `_parse_args` xử lý tự động.

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `get_student_academic_records` | `student_id: str` (mã HS hoặc tên) | Tra cứu bảng điểm chi tiết, chuyên cần, nhận xét giáo viên |
| `get_daily_activity_and_wellbeing` | `student_id: str` | Tra cứu nhật ký sinh hoạt hôm nay: thực đơn, sức khỏe, tâm lý |
| `verify_parent_access` | `student_id: str, otp_code: str` | Xác thực OTP trước khi truy xuất dữ liệu nhạy cảm |
| `get_learning_resources` | `subject: str, grade: int, topic: str (optional)` | Tìm bài tập bổ trợ, tài liệu và trò chơi học tập từ thư viện |

### 2.3 LLM Providers Used

- **Primary**: Ollama local — `llama3.2:3b` (chạy offline, zero cost)
- **Secondary (Backup)**: OpenAI `gpt-4o` / Google `gemini-1.5-flash` (cấu hình qua `.env`, khởi tạo lazy qua `factory.py`)

---

## 3. Telemetry & Performance Dashboard

Dữ liệu được thu thập từ `logs/cost_metrics.json` qua 31 lượt gọi thực tế ngày 2026-06-01.

| Metric | Value |
| :--- | :--- |
| Số lượt gọi (turns) | 31 |
| **Average Latency (P50)** | **12,650 ms** |
| **Max Latency (P99)** | **68,404 ms** |
| Average Latency (Mean) | 17,279 ms |
| **Average Tokens per Turn** | **2,185 tokens** |
| **Total Cost of Test Suite** | **$0.00** (local Ollama) |

> **Nhận xét:** Latency cao (P99 ~68s) ở các bước yêu cầu agent gọi nhiều tool liên tiếp (roadmap flow: tra điểm → tra tài liệu × n môn yếu). Đây là bottleneck chính khi dùng model nhỏ `llama3.2:3b` chạy CPU.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study 1: Tool Argument Hallucination – Wrong `student_id` format

- **Input**: "Cho tôi biết điểm của con tôi tên Minh Quân"
- **Observation**: Agent gọi `get_student_academic_records(student_id="Minh Quân")` — thành công nhờ `_resolve_student_id` fuzzy matching. Tuy nhiên, với model nhỏ (`llama3.2:3b`) đôi khi sinh ra `student_id="HS_Minh_Quân"` không hợp lệ.
- **Root Cause**: System prompt thiếu ví dụ Few-Shot rõ ràng về định dạng argument. Model nhỏ không nhất quán về cách truyền tham số.
- **Fix**: Bổ sung 2 Few-Shot example trong system prompt và thêm `_resolve_student_id` với fallback fuzzy matching trong mọi tool.

### Case Study 2: Infinite Loop / Missing Final Answer

- **Input**: Câu hỏi mơ hồ không chứa tên học sinh: "Con tôi học thế nào?"
- **Observation**: Agent looping hết `max_steps=5` mà không tìm được Final Answer, trả về empty string.
- **Root Cause**: Không có student ID nên mọi tool call đều trả lỗi → LLM tiếp tục thử lại mà không escalate.
- **Fix**: Thêm logic `_detect_student_from_conversation` ưu tiên extract student từ history; nếu vẫn không tìm được sau step 1, agent hỏi ngược lại phụ huynh.

### Case Study 3: Latency Spike (P99 = 68s)

- **Input**: "Lập lộ trình học tập cho Nguyễn Minh Quân"
- **Observation**: Roadmap flow gọi `get_student_academic_records` + `get_learning_resources` × 2 môn yếu = 3 tool calls + 1 final LLM synthesis với >2500 tokens context.
- **Root Cause**: `llama3.2:3b` chạy CPU với context dài → thời gian sinh text tăng phi tuyến.
- **Fix**: Giới hạn roadmap tối đa 2 môn yếu + cache resource lookup để tránh gọi tool trùng.

---

## 5. Ablation Studies & Experiments

### Experiment 1: System Prompt v1 vs v2 (Few-Shot cho Tool Arguments)

- **Diff**: Thêm 2 ví dụ cụ thể vào system prompt:
  ```
  Ví dụ: Action: get_student_academic_records(student_id="HS001")
  Ví dụ: Action: verify_parent_access(student_id="HS002", otp_code="123456")
  ```
- **Result**: Giảm lỗi sai định dạng argument từ ~35% xuống ~10% trên model `llama3.2:3b`.

### Experiment 2: Chatbot vs Agent

| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| "Chào" | Trả lời đúng | Trả lời đúng (short-circuit) | Draw |
| "Điểm của Minh Quân?" | Hallucinate điểm số | Gọi tool → dữ liệu thật | **Agent** |
| "Con học thế nào & nên kèm gì?" | Gợi ý chung chung | Tra điểm → phân tích → lộ trình + tài liệu cụ thể | **Agent** |
| "OTP để xem nhật ký?" | Trả dữ liệu luôn (không bảo mật) | Yêu cầu OTP trước | **Agent** |

---

## 6. Production Readiness Review

- **Security**: 
  - Tool `verify_parent_access` bắt buộc xác thực OTP 6 chữ số trước khi tiết lộ bất kỳ dữ liệu học sinh nào.
  - Input validation qua Pydantic `BaseModel` cho tất cả tool arguments — ngăn injection qua tham số.
  - Cần thay OTP demo (mọi 6-digit đều pass) bằng TOTP/SMS OTP thật trước khi lên production.

- **Guardrails**: 
  - `max_steps=5` ngăn infinite loop và tràn token window.
  - `TOOL_TIMEOUT_SECONDS=30` trên mỗi tool call — dùng `ThreadPoolExecutor` để không block server.
  - `AGENT_TIMEOUT_SECONDS=180` tổng thể cho toàn bộ một lượt.

- **Scaling**: 
  - Chuyển LLM sang `gpt-4o` / `gemini-1.5-flash` qua `.env` để tăng tốc độ và độ chính xác tool-calling.
  - Refactor sang **LangGraph** hoặc **LangChain AgentExecutor** khi cần branching phức tạp hơn (multi-agent, parallel tool calls).
  - Thêm Redis cache cho `get_learning_resources` (dữ liệu tĩnh, không cần gọi lại mỗi turn).

---

> [!NOTE]
> Report được tổng hợp từ `logs/cost_metrics.json` (31 turns thực tế), source code `src/agent/agent.py`, `src/tools/`, `src/core/` và các báo cáo cá nhân của thành viên.