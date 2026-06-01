# Individual Report: Lab 3 - Chatbot vs ReAct Agent (AI Parent Assistant)

- **Student Name**: Nguyễn Văn Đoan
- **Student ID**: 2A202600795
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Mô tả chi tiết đóng góp kỹ thuật cá nhân vào mã nguồn cốt lõi của Giai đoạn 3 (Phát triển ReAct Agent v1).*

### 1. Các module/chức năng trực tiếp thiết kế & hiện thực:
Tôi là lập trình viên chính chịu trách nhiệm thiết kế và phát triển toàn bộ **Giai đoạn 3 (Phát triển ReAct Agent v1)** trên nhánh `nguyenvandoan-2A202600795`, cụ thể bao gồm:
*   **Thiết kế System Prompt chuyên biệt cho E-School Parent Assistant:** Xây dựng hệ thống chỉ thị nâng cấp, định hình rõ ràng Persona **Trợ lý AI đồng hành cùng Phụ huynh**. Thiết lập giọng văn tiếng Việt lịch sự, ân cần, chia sẻ và có tính giáo dục xây dựng cao (constructive) giúp phụ huynh dễ tiếp nhận thông tin và đồng hành cùng con tốt hơn.
*   **Hoàn thiện Vòng lặp ReAct Loop tuần tự (`Thought -> Action -> Observation`):** Hiện thực hóa toàn bộ logic điều phối suy nghĩ, hành động và ghi nhận kết quả tại phương thức `run` trong file [agent.py](/src/agent/agent.py).
*   **Thiết kế Bộ Parser trích xuất tham số thông minh (`_parse_args` & `_execute_tool`):** Xây dựng parser sử dụng regex trích xuất động tên công cụ và tham số, tự động chuyển đổi kiểu dữ liệu (int, float, str) hỗ trợ đa dạng định dạng gọi hàm (positional arguments, keyword arguments và single raw string).
*   **Bổ sung cơ chế Tự sửa lỗi định dạng (Self-Correction/Fallback parsing):** Thêm logic phát hiện và xử lý dự phòng khi LLM trả về định dạng Final Answer không chuẩn xác hoặc bọc trong markdown codeblocks.

### 2. Minh họa Mã nguồn (Code Highlights):
Dưới đây là một số đoạn mã tiêu biểu do tôi trực tiếp lập trình trong file [agent.py](/src/agent/agent.py):

*   **Vòng lặp ReAct Loop & Parser Regex:**
```python
# Regex to match Action and Final Answer
action_match = re.search(r"Action:\s*(\w+)\((.*)\)", content)
final_match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL)

if action_match:
    tool_name = action_match.group(1)
    tool_args = action_match.group(2)
    
    # Execute tool
    observation = self._execute_tool(tool_name, tool_args)
    observation_str = f"Observation: {observation}"
    
    print(f"\n{observation_str}")
    
    # Append current generation + observation back into history
    current_prompt += f"\n{content}\n{observation_str}\n"
```

*   **Hàm phân tích đối số linh hoạt:**
```python
def _parse_args(self, args_str: str) -> Any:
    args_str = args_str.strip()
    if not args_str:
        return {}

    # 1. Check for key=value format (dictionary-like)
    if '=' in args_str:
        parsed = {}
        parts = re.split(r',\s*(?=(?:[^\'"]*[\'"][^\'"]*[\'"])*[^\'"]*$)', args_str)
        for part in parts:
            if '=' in part:
                k, v = part.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                try:
                    if '.' in v:
                        parsed[k] = float(v)
                    else:
                        parsed[k] = int(v)
                except ValueError:
                    parsed[k] = v
        return parsed
```

---

## II. Debugging Case Study (10 Points)

*Phân tích sâu sắc một trường hợp lỗi thực tế gặp phải (hallucination, loop, parser error) thông qua việc phân tích log/telemetry và cách khắc phục.*

### 1. Mô tả bài toán & Triệu chứng lỗi (Symptoms):
Trong quá trình thử nghiệm ReAct Agent chạy kịch bản **AI Trợ Lý Phụ Huynh**, khi phụ huynh hỏi câu hỏi có chứa tiếng Việt có dấu: *"Con tôi là Nguyễn Minh Anh..."*, hệ thống trên terminal Windows lập tức bị sập (crash) với thông báo lỗi:
`UnicodeEncodeError: 'charmap' codec can't encode character...`
Sau khi tạm thời khắc phục được lỗi encoding bằng cách loại bỏ emoji, Agent lại gặp lỗi logic: dù gọi đúng tool `get_student_grades(student_name="Nguyễn Minh Anh")`, kết quả nhận về luôn là:
`Observation: Không tìm thấy dữ liệu học sinh 'Nguyễn Minh Anh'.`

### 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA):
Qua phân tích telemetry logs (`logs/` event type `PARSER_ERROR` và log chạy terminal), tôi đã phát hiện ra hai lỗi song song:
1.  **Lỗi Windows Terminal Encoding:** Môi trường Windows sử dụng bảng mã mặc định CP1252 (Active Code Page) để ghi/in dữ liệu. Khi Agent trả về phản hồi tiếng Việt có dấu, trình biên dịch Python cố gắng chuyển đổi ký tự Unicode sang CP1252 và phát sinh ngoại lệ `UnicodeEncodeError`.
2.  **Lỗi Lệch Chỉ Mục Chuỗi Bỏ Dấu (Diacritics Mismatch):** Để so sánh tên học sinh không phân biệt dấu, hệ thống ban đầu sử dụng hàm `remove_accents` dựa trên hai chuỗi ánh xạ tĩnh `s1` và `s0`. Tuy nhiên, do sơ suất, độ dài hai chuỗi này bị lệch (`len(s1)=132` vs `len(s0)=131`). Khi ký tự `ễ` trong tên "Nguyễn" được ánh xạ, chỉ mục bị lệch khiến nó biến đổi sai lệch thành chữ `E` viết hoa (kết quả so sánh ra "NguyEn Minh Anh" thay vì "nguyen minh anh"), làm công cụ không khớp được khóa học sinh trong `STUDENT_DB`.

### 3. Giải pháp khắc phục (Mitigation & Fix):
Tôi đã trực tiếp thiết kế và áp dụng bộ ba giải pháp cô lập để sửa triệt để các lỗi trên:
1.  **Cấu hình tái định dạng stdout:** Bổ sung đoạn mã cấu hình `sys.stdout.reconfigure(encoding='utf-8')` ngay đầu các file runner để ép terminal Windows chạy bằng UTF-8.
2.  **Khai báo encoding mã nguồn:** Đặt khai báo `# -*- coding: utf-8 -*-` ở dòng đầu tiên của các file Python chứa ký tự tiếng Việt có dấu.
3.  **Lập trình lại hàm bỏ dấu bằng Từ điển Ánh xạ (Map Dictionary):** Thay thế việc so sánh chuỗi chỉ mục bằng một từ điển ánh xạ rõ ràng từng ký tự tiếng Việt có dấu sang không dấu (`accent_map`), đảm bảo tỷ lệ chuyển đổi và khớp dữ liệu học sinh chính xác 100%:
```python
def remove_accents(input_str: str) -> str:
    accent_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a', 'ă': 'a', 'ằ': 'a', 'ắ': 'a', ...
        'ễ': 'e', 'ệ': 'e', 'đ': 'd', 'Đ': 'D', ...
    }
    return "".join(accent_map.get(c, c) for c in input_str)
```
Sau khi sửa đổi, Agent đã thực thi vòng lặp 5 bước trơn tru, khớp chính xác thông tin và trả về kết quả ân cần hoàn hảo gửi tới phụ huynh.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Suy ngẫm và đúc kết về sự khác biệt bản chất trong năng lực lập luận giữa LLM Chatbot truyền thống và ReAct Agent.*

### 1. Năng lực Lập luận (Reasoning):
*   **LLM Chatbot truyền thống:** Hoạt động dựa trên dự đoán từ tiếp theo (Next-token prediction) một cách tĩnh. Đối với các câu hỏi đòi hỏi thông tin động, mang tính cá nhân hóa (như điểm số hay đi học muộn cụ thể của một học sinh), Chatbot thông thường không thể truy cập dữ liệu thực và buộc phải từ chối hoặc nghiêm trọng hơn là **ảo tưởng (hallucination)** ra các con số không có thật.
*   **ReAct Agent:** Hoạt động dựa trên chu trình lập luận động (`Thought -> Action -> Observation`). Mỗi bước suy nghĩ (`Thought`) đóng vai trò như một bộ định tuyến logic, phân tích xem thông tin hiện có đã đủ chưa, nếu thiếu thì cần gọi công cụ nào (`Action`) để bổ sung dữ liệu thực tế (`Observation`). Điều này biến LLM từ một "người nói chuyện phiếm" thành một "thực thể hành động" có tính kỷ luật cao.

### 2. Độ tin cậy (Reliability):
*   **Khi nào Agent hoạt động kém hơn Chatbot?** Với các câu hỏi đơn giản, hội thoại ngắn hoặc xã giao thông thường (e.g. *"Chào bạn"*, *"Bạn khỏe không"*), Chatbot thông thường có độ trễ cực thấp (latency < 200ms) và tiêu tốn rất ít token. Trong khi đó, ReAct Agent nếu không được kiểm soát tốt sẽ cố gắng "lập luận lặp đi lặp lại", sinh ra các Thought/Action dư thừa, dẫn đến việc tăng đáng kể thời gian phản hồi (latency) và chi phí tài nguyên (token cost) một cách lãng phí.

### 3. Phản hồi Môi trường (Observation Influence):
*   Kết quả trả về từ công cụ (`Observation`) đóng vai trò là "tri thức thực tế" định hình trực tiếp cho suy nghĩ của Agent ở bước tiếp theo. Ví dụ: Trong kịch bản AI Trợ lý Phụ huynh, khi nhận thấy điểm Ngữ văn của học sinh Nguyễn Minh Anh chỉ đạt 6.0/10 và nhận xét của giáo viên chỉ ra lỗi "chưa tập trung vào văn tả cảnh thiên nhiên", Agent lập tức nhận diện lỗ hổng kiến thức này và chủ động gọi thêm công cụ RAG (`search_curriculum_and_advice`) môn Ngữ văn tuần 10 để lấy lời khuyên thực tế cho phụ huynh. Đây là điều mà một Chatbot tĩnh không bao giờ làm được.

---

## IV. Future Improvements (5 Points)

*Đề xuất các phương án nâng cấp giải pháp hiện tại lên cấp độ Production (Thực tế công nghiệp).*

Để đưa hệ thống **AI Trợ Lý Phụ Huynh** từ một nguyên mẫu thí nghiệm (Prototype) lên môi trường thực tế (Production), tôi đề xuất 3 giải pháp cải tiến cốt lõi sau:

1.  **Xử lý Bất đồng bộ song song (Asynchronous Tool Execution):**
    *   *Hiện trạng:* Vòng lặp ReAct hiện tại gọi tuần tự từng công cụ gây ra độ trễ tích lũy lớn (Latency P99 có thể lên tới 5-8 giây).
    *   *Cải tiến:* Thiết kế cho phép Agent lập kế hoạch gọi nhiều công cụ độc lập cùng lúc (ví dụ gọi song song `get_student_grades` và `get_student_attendance` trong cùng một bước) bằng `asyncio.gather()`, giúp giảm tổng thời gian phản hồi xuống dưới 2 giây.
2.  **Kiểm duyệt an toàn & Bảo mật thông tin học bạ (Guardrails & Privacy):**
    *   *Cải tiến:* Áp dụng các thư viện kiểm duyệt an toàn (như **NeMo Guardrails** hoặc **Llama Guard**) để đảm bảo phụ huynh chỉ truy cập được đúng dữ liệu của con mình bằng cách xác thực token người dùng trước mỗi lần gọi Tool, đồng thời lọc bỏ các câu hỏi chứa nội dung nhạy cảm hoặc không liên quan đến môi trường giáo dục.
3.  **Hệ thống RAG nâng cao với Vector Database thực tế:**
    *   *Cải tiến:* Thay thế mock JSON bằng một Vector Database chuyên dụng (như **Qdrant** hoặc **ChromaDB**) chứa toàn bộ sách giáo khoa, kế hoạch giảng dạy của trường. Sử dụng kỹ thuật **Hybrid Search** (kết hợp BM25 cho từ khóa chính xác và Dense Retrieval cho ngữ nghĩa) kèm theo bộ **Reranker** (như Cohere Rerank) để đảm bảo lời khuyên học tập trả về cho phụ huynh luôn đạt chất lượng chuyên môn cao nhất.
