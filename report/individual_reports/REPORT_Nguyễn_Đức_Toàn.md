# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Đức Toàn
- **Student ID**: 2A202600733
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

### 1. Vai trò: Git Integrator & LLM Integration Lead

Trong nhóm, tôi đảm nhận hai vai trò chính:
- **Git Integrator**: Chịu trách nhiệm merge code từ các nhánh thành viên vào `main`, giải quyết conflict, đảm bảo codebase luôn chạy được sau mỗi lần tích hợp.
- **LLM Integration Lead**: Kết nối toàn bộ pipeline từ Frontend → FastAPI → ReActAgent → LLM (Ollama/llama3.2:3b), xử lý các vấn đề về provider, model config và token flow.

---

### 2. Các module trực tiếp thiết kế & hiện thực

#### 2.1 Kết nối Frontend ↔ Agent (`src/fe/server.py`)
Thiết kế endpoint `/api/chat` nhận `question`, `history`, khởi tạo `ReActAgent` với `AVAILABLE_TOOLS`, truyền lịch sử hội thoại vào agent:
```python
class ChatRequest(BaseModel):
    question: str
    provider: str | None = None
    model: str | None = None
    history: list[HistoryMessage] = []

tools = [{"name": t["name"], "description": t["description"],
          "func": t["function"], "input_model": t.get("input_model")}
         for t in AVAILABLE_TOOLS]
agent = ReActAgent(llm=llm, tools=tools)
history = [(m.role, m.content) for m in req.history]
content = agent.run(req.question, history=history)
```

#### 2.2 Sửa lỗi OllamaProvider (`src/core/factory.py`)
Phát hiện và fix lỗi `OllamaProvider` nhận `host=` nhưng code truyền sai tham số, khiến toàn bộ local LLM không kết nối được:
```python
base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
# Fix: truyền base_url= thay vì host=
provider = OllamaProvider(base_url=base_url, model=model)
```

#### 2.3 Bộ nhớ ngữ cảnh hội thoại (`src/agent/agent.py` — `_build_history_context`)
Xây dựng cơ chế inject lịch sử hội thoại vào prompt, giới hạn 300 ký tự/lượt để tránh tràn context window của model nhỏ:
```python
def _build_history_context(self, history):
    lines = ["=== LỊCH SỬ HỘI THOẠI ==="]
    for role, content in history:
        label = "Phụ huynh" if role == "user" else "Trợ lý"
        display = content if len(content) <= 300 else content[:300] + "..."
        lines.append(f"[{label}]: {display}")
    lines.append("=== KẾT THÚC LỊCH SỬ ===")
    return "\n".join(lines) + "\n"
```

#### 2.4 Intent-based Response Filtering (`src/agent/agent.py` — `_detect_intent` + `_build_tool_response`)
Thiết kế hệ thống nhận diện ý định câu hỏi để chỉ trả về dữ liệu phù hợp — không trả thừa thông tin ngoài lề:

| Intent | Từ khóa kích hoạt | Dữ liệu trả về |
|---|---|---|
| `attendance` | muộn, vắng, nghỉ, buổi... | Chỉ chuyên cần + đi muộn + nghỉ |
| `scores` | điểm, học lực, bảng điểm... | Chỉ điểm từng môn |
| `full` | tình hình, kết quả, học tập... | Toàn bộ + phân tích + gợi ý tài liệu |

#### 2.5 Resolve học sinh theo tên hoặc mã (`src/tools/tools_academic.py` — `_resolve_student_id`)
Viết hàm chuẩn hóa input từ LLM: xử lý `"Lê_Hoàng_Phúc"` (gạch dưới), tên riêng một từ (`"Phúc"`), hoặc mã `"HS003"`:
```python
def _resolve_student_id(identifier: str) -> str | None:
    key = identifier.strip().upper()
    if re.match(r"^HS\d+$", key) and key in STUDENT_DB:
        return key
    normalized = re.sub(r"[_\-]+", " ", identifier).strip().lower()
    for sid, info in STUDENT_DB.items():
        name = info.get("name", "").lower()
        if normalized in name or name in normalized:
            return sid
    return None
```

#### 2.6 Cost Metrics & Logging (`src/telemetry/metrics.py`)
Xây dựng hệ thống đo lường chi phí token theo thời gian thực, lưu vào `logs/cost_metrics.json`:
- Bảng giá thực tế: gpt-4o, gpt-4o-mini, gemini-1.5-flash, local = $0
- Fields: `timestamp`, `provider`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `cost_total_usd`

#### 2.7 Xử lý artifact ReAct trong response (`_clean_response`)
Loại bỏ các nhãn nội bộ `Thought:`, `Action:`, `Observation:`, `Final Answer:` trước khi trả về FE:
```python
text = re.sub(r"(?im)^Thought:.*?(?=\nFinal Answer:|\nAction:|\Z)", "", text, flags=re.DOTALL)
text = re.sub(r"(?im)^Action:\s*\S+.*$", "", text)
text = re.sub(r"(?im)^Observation:\s*.*$", "", text)
```

---

## II. Debugging Case Study (10 Points)

### Bug: LLM gọi sai tool — `verify_parent_access` thay vì `get_student_academic_records`

**Triệu chứng:**
```
Error executing tool 'verify_parent_access': 1 validation error for SecurityVerificationInput
otp_code — Field required [type=missing]
```

**Nguyên nhân (Root Cause):**
Model nhỏ llama3.2:3b thấy tool `verify_parent_access` trong danh sách và "suy luận" rằng cần xác thực OTP trước khi tra điểm — một hành vi hợp lý về mặt logic nhưng sai về thiết kế hệ thống. Tool description cũ quá ngắn, không chỉ rõ khi nào nên dùng tool nào.

**Chẩn đoán qua log:**
```
AGENT_STEP → LLM_RESPONSE: "Action: verify_parent_access(student_id='Nguyễn_Minh_Quân')"
TOOL_EXECUTION → Error: otp_code missing
```

**Giải pháp:**
1. Bỏ `verify_parent_access` khỏi `AVAILABLE_TOOLS` — LLM không thấy tool này nên không gọi nhầm
2. Viết lại description rõ ràng với ví dụ use-case:
```python
"description": (
    "Tra cứu điểm số, chuyên cần, nhận xét giáo viên của học sinh. "
    "Dùng khi phụ huynh hỏi về: điểm, học lực, bảng điểm, số buổi vắng/muộn. "
    "Đầu vào: student_id — mã (VD: 'HS001') HOẶC tên (VD: 'Nguyễn Minh Quân')."
)
```

---

### Bug: Student profile bị nhiễu từ lịch sử hội thoại

**Triệu chứng:** Hỏi "tình hình học tập của Phúc" → trả về dữ liệu của Quân (học sinh trong tin nhắn trước).

**Nguyên nhân:** `_detect_student_from_conversation` duyệt toàn bộ history theo thứ tự, tìm thấy "Quân" trước "Phúc".

**Giải pháp:** Ưu tiên câu hỏi hiện tại trước, chỉ fallback sang history nếu không tìm thấy:
```python
def _detect_student_from_conversation(self, current_input, history):
    student_id = self._extract_student_id(current_input)  # current first
    if student_id:
        return student_id
    for _, content in reversed(history):  # most recent history
        student_id = self._extract_student_id(content)
        if student_id:
            return student_id
    return None
```

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Năng lực Lập luận (Reasoning)
LLM Chatbot thuần túy dự đoán token tiếp theo dựa trên tham số đã train — không thể truy cập dữ liệu động. Khi phụ huynh hỏi "điểm Toán của con", Chatbot hoặc từ chối hoặc hallucinate số điểm không có thật.

ReAct Agent giải quyết điều này bằng chu trình `Thought → Action → Observation`: LLM tự quyết định cần gọi tool nào, thực thi, nhận kết quả thực, rồi tổng hợp thành câu trả lời. Khối `Thought` hoạt động như một bộ định tuyến logic có kiểm soát.

### 2. Độ tin cậy (Reliability)
Agent hoạt động **kém hơn** Chatbot trong các trường hợp:
- Câu chào hỏi đơn giản: Agent cố "lập luận" dẫn đến latency 8–16 giây thay vì <1 giây → giải pháp: thêm `_is_greeting()` shortcut
- Model nhỏ (3b params): thường bỏ qua format `Action:` → parser fail → dùng fallback `Thought:` content
- Multi-turn khi học sinh thay đổi: history làm nhiễu student detection nếu không ưu tiên đúng

### 3. Phản hồi Môi trường (Observation Influence)
`Observation` từ tool là "dữ liệu thực tế" định hướng suy nghĩ tiếp theo của Agent. Ví dụ thực tế trong lab: khi Observation trả về điểm Toán 5.5 (giảm từ 6.0) + trạng thái "Cần cải thiện", Agent nhận diện xu hướng giảm và tự động gợi ý tài liệu từ RESOURCE_DB — hành vi không thể có với Chatbot tĩnh.

---

## IV. Future Improvements (5 Points)

### 1. Xử lý bất đồng bộ (Async Tool Execution)
Vòng lặp ReAct hiện tại gọi tool tuần tự. Với `asyncio.gather()`, có thể gọi song song `get_student_academic_records` và `get_daily_activity_and_wellbeing` cùng lúc, giảm latency từ ~16s xuống ~8s.

### 2. Bảo mật & Phân quyền dữ liệu (Auth + Row-level Security)
Hiện tại bất kỳ ai cũng tra được điểm của bất kỳ học sinh nào. Production cần JWT authentication + row-level security: mỗi phụ huynh chỉ truy cập được dữ liệu của con mình.

### 3. Vector DB thay Mock DB
Thay STUDENT_DB JSON bằng vector database (Qdrant/ChromaDB) + hybrid search (BM25 + dense retrieval) để hỗ trợ hàng nghìn học sinh, tìm kiếm ngữ nghĩa và tích hợp tài liệu giáo trình thực tế.

### 4. LLM lớn hơn cho production
llama3.2:3b phù hợp demo nhưng hay bỏ format Action. Production nên dùng llama3.1:8b hoặc qwen2.5:7b để tăng độ chính xác parsing và chất lượng phân tích học lực.
