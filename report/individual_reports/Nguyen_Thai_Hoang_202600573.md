# Individual Report: Lab 3 - Chatbot vs ReAct Agent

* **Student Name**: [Nguyễn Thái Hoàng]
* **Student ID**: [2A202600573]
* **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

* **Modules Implementated**:
* `src/tools/mock_db.py` (Cơ sở dữ liệu giả lập tập trung về học tập, sinh hoạt, tâm lý học sinh và kho tài nguyên giáo dục).
* `src/tools/tools_academic.py` (Định nghĩa Pydantic Model và hàm tra cứu điểm số, nhật ký sinh hoạt hằng ngày).
* `src/tools/tools_resources.py` (Định nghĩa Pydantic Model và hàm tìm kiếm học liệu bổ trợ).
* `src/tools/__init__.py` (Cửa ngõ Gateway đóng gói danh sách `AVAILABLE_TOOLS` xuất bản sang cho mô-đun Agent).


* **Code Highlights**:
*Áp dụng Pydantic Model (v2) để định nghĩa Schema đầu vào nghiêm ngặt cho Tool, tích hợp Docstring tiếng Việt chi tiết làm chỉ dẫn cho LLM:*
```python
class LearningResourceInput(BaseModel):
    subject: str = Field(..., description="Tên môn học cần tìm tài liệu. Chỉ nhận các giá trị: 'Toán', 'Tiếng Việt'.")
    grade: int = Field(..., description="Khối lớp của học sinh. Ví dụ: 4 hoặc 5.")
    topic: Optional[str] = Field(None, description="Từ khóa chủ đề cụ thể (ví dụ: 'Phép nhân', 'Tập làm văn'). Có thể bỏ trống.")

def get_learning_resources(subject: str, grade: int, topic: Optional[str] = None) -> str:
    """Tìm kiếm kho bài tập bổ trợ, phương pháp học tập tư duy từ thư viện nhà trường."""
    # Logic truy xuất dữ liệu từ RESOURCE_DB và lọc theo chủ đề (Fuzzy Filter)...
    return json.dumps(filtered_or_all_resources, ensure_ascii=False)

```


* **Documentation**:
Các công cụ được thiết kế theo tư duy độc lập (Mô-đun hóa) nhằm phục vụ chu trình ReAct. Khi `ReActAgent` phân tích câu hỏi phức hợp của phụ huynh, nó sẽ trích xuất mã học sinh (`student_id`), gọi `get_daily_activity_and_wellbeing` hoặc `get_student_academic_records` để lấy thông tin hiện trạng (Observation). Từ kết quả nhận được, Agent tiếp tục suy luận môn học/kiến thức con đang yếu để tự động kích hoạt tiếp `get_learning_resources`, tạo thành chuỗi hành động liên tục (Multi-step Reasoning) trước khi đưa ra câu trả lời cuối cùng.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

* **Problem Description**: Agent bị rơi vào vòng lặp vô hạn (**Infinite Loop**) khi phụ huynh hỏi về tình hình học tập môn Toán của con. Hệ thống liên tục sinh ra `Action: get_learning_resources(subject="Toán", grade="lớp 4")` và nhận về thông báo lỗi từ phía Pydantic, sau đó lại tiếp tục lặp lại đúng hành động đó cho đến khi chạm `max_steps`.
* **Log Source**: Trích xuất từ `logs/2026-06-01.log`:
```text
[2026-06-01 22:15:03] [AGENT_START] Input: "Con tôi học Toán thế nào?"
[2026-06-01 22:15:05] [LLM_RESPONSE] Thought: Tôi cần tìm tài liệu Toán lớp 4. Action: get_learning_resources(subject="Toán", grade="lớp 4")
[2026-06-01 22:15:06] [TOOL_ERROR] Lỗi thực thi tool get_learning_resources: 1 validation error for LearningResourceInput -> grade -> Input should be a valid integer
[2026-06-01 22:15:07] [LLM_RESPONSE] Thought: Lỗi định dạng khối lớp. Tôi cần thử lại. Action: get_learning_resources(subject="Toán", grade="lớp 4")

```


* **Diagnosis**: LLM bị "hiểu nhầm" cách truyền tham số do chuỗi mô tả (Tool Spec) ban đầu ghi không rõ ràng. Thay vì truyền giá trị kiểu số nguyên `4`, mô hình ngôn ngữ tự ý điền vào một chuỗi string `"lớp 4"`. Khi đi qua tầng bảo vệ Pydantic Model, dữ liệu bị từ chối và sinh lỗi `ValidationError`. Do Agent chưa được hướng dẫn cách xử lý lỗi định dạng này trong System Prompt, nó liên tục lặp lại hành vi sai trái đó.
* **Solution**:
1. Cập nhật lại thuộc tính `description` trong Pydantic Field của trường `grade`: Ghi rõ `Ví dụ: 4 hoặc 5 (bắt buộc phải là số nguyên, không kèm chữ)`.
2. Bổ sung vào cấu trúc `get_system_prompt()` một quy tắc nghiêm ngặt: *"Nếu nhận được Observation chứa thông báo lỗi ValidationError, bạn phải điều chỉnh ngay định dạng tham số đầu vào (ví dụ chuyển từ chuỗi văn bản sang số nguyên) thay vì lặp lại Action cũ."*



---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1. **Reasoning**: Khối `Thought` hoạt động như một "không gian cào nháp" (scratchpad) giúp Agent định hình tư duy trước khi hành động. Đối với các câu hỏi phức tạp mang tính tâm lý như của phụ huynh (Ví dụ: "Con đi học về thấy buồn, ở trường có chuyện gì không?"), một Chatbot thông thường chỉ có thể trả lời chung chung hoặc đưa ra lời khuyên sáo rỗng. Trong khi đó, khối `Thought` giúp ReAct Agent định hướng: Đầu tiên phải tra cứu xem ngày hôm nay ở trường có biến động gì không (`Action 1`), sau đó đánh giá điểm số xem có áp lực bài vở không (`Action 2`), từ đó xâu chuỗi nguyên nhân để đưa ra giải pháp toàn diện.
2. **Reliability**: Trong các tình huống phụ huynh chỉ muốn giao tiếp thông thường, hỏi đáp nhanh hoặc chào hỏi (ví dụ: "Chào trợ lý", "Cảm ơn cô giáo"), ReAct Agent có xu hướng hoạt động kém hiệu quả và tốn chi phí (API Cost) hơn Chatbot truyền thống. Agent đôi khi cố chấp tìm kiếm một "Action" để gọi hoặc sinh ra các chuỗi `Thought` không cần thiết, làm kéo dài thời gian phản hồi (Latency).
3. **Observation**: Phản hồi từ môi trường (`Observation`) đóng vai trò là chiếc la bàn điều hướng cho các bước tiếp theo của Agent. Nếu `Observation` từ hệ thống báo về rằng học sinh Quân ăn uống tốt nhưng có xích mích với bạn, tư duy tiếp theo (`Thought`) của Agent sẽ lập tức bám vào sự kiện xích mích này để phân tích tâm lý, thay vì tiếp tục đi tìm các nguyên nhân khách quan khác. Nó giúp Agent neo giữ thông tin thực tế thay vì bị sa đà vào ảo tưởng (Hallucination).

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

* **Scalability**: Chuyển đổi cơ chế gọi Tool từ đồng bộ (Synchronous) sang bất đồng bộ (Asynchronous) sử dụng `async/await` kết hợp với hàng đợi tác vụ (Task Queue như Celery), giúp hệ thống xử lý đồng thời hàng ngàn truy vấn từ nhiều phụ huynh cùng lúc mà không tắc nghẽn.
* **Safety**: Triển khai một lớp "Supervisor LLM" hoặc bộ lọc Guardrails độc lập (như NeMo Guardrails) để kiểm soát dữ liệu đầu ra. Đảm bảo Agent không bao giờ tiết lộ nhầm thông tin cá nhân của học sinh này cho phụ huynh của học sinh khác, và ngôn từ phản hồi luôn giữ chuẩn mực sư phạm.
* **Performance**: Thay thế Mock DB bằng một hệ thống cơ sở dữ liệu thực tế (PostgreSQL cho dữ liệu học sinh và Vector DB như Chroma/Pinecone cho kho học liệu tài nguyên). Khi số lượng tài liệu lên tới hàng triệu bài, Vector DB sẽ giúp Agent tìm kiếm tài liệu bổ trợ bằng ngữ nghĩa (Semantic Search) chính xác và nhanh chóng hơn nhiều so với việc lọc từ khóa (Fuzzy Filter) thủ công.