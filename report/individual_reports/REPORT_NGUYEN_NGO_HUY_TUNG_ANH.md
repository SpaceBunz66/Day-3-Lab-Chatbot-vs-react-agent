# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Ngô Huy Tùng Anh
- **Student ID**: 2A202600613
- **Date**: 1/6/2026

---

## I. Technical Contribution (15 Points)

- **Modules Implemented**: `src/tools/tools_academic.py`, `src/chatbot/chatbot.py`

### `src/tools/tools_academic.py`

File này định nghĩa 2 tool cung cấp dữ liệu thực từ mock database cho ReAct Agent.

**Input schema dùng Pydantic để validate tự động:**
```python
class StudentIdInput(BaseModel):
    student_id: str = Field(..., description="Mã số định danh học sinh (ví dụ: 'HS001').")
```

**Tool 1 — `get_student_academic_records`:** Tra cứu điểm số từng môn, tỉ lệ chuyên cần và nhận xét của giáo viên chủ nhiệm từ `STUDENT_DB`. Trả về JSON bao gồm `name`, `class`, `attendance_rate`, `teacher_remark`, `subjects`.

```python
def get_student_academic_records(student_id: str) -> str:
    student = STUDENT_DB.get(student_id)
    if not student:
        return json.dumps({"error": "Không tìm thấy dữ liệu học tập."})
    response = {
        "name": student["name"],
        "class": student["class"],
        "attendance_rate": student["attendance_rate"],
        "teacher_remark": student["teacher_remark"],
        "subjects": student["subjects"],
    }
    return json.dumps(response, ensure_ascii=False)
```

**Tool 2 — `get_daily_activity_and_wellbeing`:** Tra cứu nhật ký sinh hoạt trong ngày từ `DAILY_LIFE_DB`, bao gồm thực đơn (`meals`), tình trạng sức khỏe, tâm lý và dặn dò của giáo viên.

Cả 2 tool đều trả về JSON string — định dạng này phù hợp để ReAct Agent đặt vào `Observation` trong vòng lặp Thought → Action → Observation.

### `src/chatbot/chatbot.py`

File này xây dựng `SimpleChatbot` — baseline không có tool, không có loop, dùng để so sánh với ReAct Agent.

**Điểm kỹ thuật nổi bật:**

1. **Multi-turn context:** `_build_context()` ghép toàn bộ lịch sử hội thoại thành một chuỗi text trước khi gửi LLM, giúp chatbot nhớ ngữ cảnh qua nhiều lượt.

```python
def _build_context(self, user_input: str) -> str:
    lines = []
    for turn in self.history:
        prefix = "Phụ huynh" if turn["role"] == "user" else "Trợ lý"
        lines.append(f"{prefix}: {turn['content']}")
    lines.append(f"Phụ huynh: {user_input}")
    return "\n".join(lines)
```

2. **Telemetry tích hợp:** Mọi request/response đều được log qua `logger.log_event()` và đo lường token + latency qua `tracker.track_request()`, tạo dữ liệu so sánh trực tiếp với Agent.

3. **System prompt định hướng:** Prompt hướng dẫn chatbot thành thật từ chối khi không có dữ liệu thực, thay vì hallucinate — đây là giới hạn cốt lõi của kiến trúc không có tool.

---

## II. Debugging Case Study (10 Points)

**Problem Description:** Sau khi `mock_db.py` được cập nhật cấu trúc (gộp `STUDENT_TABLE` + `ACADEMIC_TABLE` thành `STUDENT_DB` duy nhất), test `test_academic_records_valid` bị fail với lỗi `KeyError: 'records'`.

**Log Source:** Chạy `python -m pytest tests/test_tools_and_agent.py::test_academic_records_valid -v`:
```
FAILED tests/test_tools_and_agent.py::test_academic_records_valid
KeyError: 'records'
```

**Diagnosis:** `tools_academic.py` ban đầu ghép dữ liệu từ 2 bảng riêng biệt (`STUDENT_TABLE` cho thông tin cơ bản, `ACADEMIC_TABLE` cho điểm số), rồi đặt điểm số vào key `"records"`. Khi mock DB được cập nhật gộp tất cả vào `STUDENT_DB` (điểm số nằm trực tiếp trong key `"subjects"`), cả function lẫn test đều lỗi thời.

Đây không phải lỗi của LLM hay prompt — mà là **contract mismatch** giữa data layer và tool layer khi schema thay đổi mà không cập nhật đồng bộ.

**Solution:**
- Cập nhật import: `STUDENT_TABLE, ACADEMIC_TABLE` → `STUDENT_DB`
- Bỏ logic ghép 2 bảng, truy cập trực tiếp `student["subjects"]`
- Sửa test: `assert "subjects" in result["records"]` → `assert "subjects" in result`

Bài học: Tool schema và DB schema phải được cập nhật đồng bộ — một thay đổi ở `mock_db.py` kéo theo thay đổi bắt buộc ở cả tool implementation lẫn test assertions.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

**1. Reasoning — Vai trò của khối `Thought`:**

`SimpleChatbot` trả lời trực tiếp từ kiến thức huấn luyện. Khi phụ huynh hỏi *"Con ăn gì hôm nay?"*, chatbot không có dữ liệu thực và chỉ có thể từ chối hoặc đoán chung chung.

ReAct Agent dùng khối `Thought` để lập kế hoạch trước: *"Tôi cần gọi `get_daily_activity_and_wellbeing` để biết thực đơn hôm nay."* Bước lý luận tường minh này cho phép agent biết **khi nào cần dùng tool** và **tool nào** — thay vì phụ thuộc vào kiến thức nội tại.

**2. Reliability — Khi nào Agent thực sự kém hơn Chatbot:**

Với câu hỏi chung không cần dữ liệu thực (*"Làm thế nào để giúp con học Toán tốt hơn?"*), Agent kém hiệu quả hơn vì:
- Tốn thêm ít nhất 1 lần gọi LLM để quyết định có cần tool không
- Nếu agent hallucinate action trên câu hỏi không cần tool, phải tốn thêm bước recover
- Latency cao hơn rõ rệt so với chatbot trả lời 1 shot

**3. Observation — Phản hồi môi trường định hướng bước tiếp theo:**

`Observation` từ tool thực sự thay đổi hành vi của agent. Ví dụ: sau khi nhận kết quả từ `get_student_academic_records` với `"status": "Cần cải thiện"` ở môn Toán, agent ở bước tiếp theo có thể quyết định gọi tiếp `get_learning_resources` để tìm tài liệu — một chuỗi hành động **không thể xảy ra** trong kiến trúc chatbot đơn giản.

---

## IV. Future Improvements (5 Points)

- **Scalability:** Chạy nhiều tool call song song (async) thay vì tuần tự. Với câu hỏi yêu cầu cả điểm số lẫn nhật ký sinh hoạt, 2 tool có thể được gọi đồng thời để giảm latency tổng.

- **Safety:** Thêm một lớp validation trước khi tool trả kết quả về Agent — đảm bảo dữ liệu nhạy cảm (thông tin học sinh) chỉ được truy cập sau khi xác thực danh tính phụ huynh. Có thể bổ sung một Supervisor LLM kiểm tra action trước khi thực thi.

- **Performance:** Khi số lượng tool tăng lên (hàng chục tool), việc đưa toàn bộ tool descriptions vào system prompt sẽ tốn token và nhiễu. Giải pháp: dùng vector embedding để retrieval đúng tool cần thiết theo từng câu hỏi, thay vì load tất cả mọi lúc.

---

> Submitted by: Nguyễn Ngô Huy Tùng Anh — 2A202600613
