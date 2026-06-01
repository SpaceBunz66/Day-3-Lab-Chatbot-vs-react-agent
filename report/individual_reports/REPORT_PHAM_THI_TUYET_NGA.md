# Individual Report: Lab 3 - Chatbot vs ReAct Agent (AI Parent Assistant)

- **Student Name**: Phạm Thị Tuyết Nga
- **Student ID**: 2A202600877
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Mô tả chi tiết đóng góp kỹ thuật cá nhân: tôi phụ trách toàn bộ tầng Backend (web server) + Frontend (giao diện chat) và hệ thống Tài liệu dự án.*

### 1. Các module/chức năng trực tiếp thiết kế & hiện thực:

Tôi đảm nhiệm vai trò **Full-stack Developer + Technical Writer** trên nhánh `NgaPTT-2A202600877`, là người nối toàn bộ phần lõi ReAct Agent (do nhóm xây dựng) ra một sản phẩm web hoàn chỉnh mà phụ huynh có thể sử dụng thực tế. Cụ thể:

* **Backend Web Server (FastAPI):** Thiết kế và hiện thực file [server.py](/src/fe/server.py) — dựng ứng dụng `FastAPI`, định nghĩa endpoint `POST /api/chat` nhận câu hỏi từ phụ huynh, khởi tạo `ReActAgent`, nạp toàn bộ `AVAILABLE_TOOLS`, gọi `agent.run()` và trả về JSON kèm telemetry (latency, provider). Đồng thời cấu hình phục vụ file tĩnh (`StaticFiles`) và route `/` trả về trang chat.
* **Frontend giao diện chat (HTML/CSS/JS thuần):** Tự thiết kế và lập trình toàn bộ UI gồm 3 file:
  * [index.html](/src/fe/static/index.html): bố cục 3 cột (icon-rail, sidebar lịch sử, khu vực chat), màn hình chào với các thẻ gợi ý câu hỏi (suggestion cards), ô nhập câu hỏi (composer).
  * [style.css](/src/fe/static/style.css): toàn bộ giao diện, hỗ trợ **chế độ Sáng/Tối (dark/light theme)** qua biến CSS, responsive cơ bản.
  * [app.js](/src/fe/static/app.js): logic phía client — quản lý nhiều cuộc hội thoại, **lưu lịch sử bằng `localStorage`**, render bong bóng tin nhắn, gửi câu hỏi qua `fetch` tới `/api/chat`, hiển thị trạng thái "Đang trả lời...", và **gửi kèm lịch sử 10 tin nhắn gần nhất** để Agent có ngữ cảnh hội thoại.
* **Factory tích hợp đa LLM Provider:** Đóng góp vào [factory.py](/src/core/factory.py) theo **Provider Pattern** — một "công tắc" cho phép chuyển đổi linh hoạt giữa các nhà cung cấp (OpenAI, Google Gemini, Local Phi-3, Ollama) qua biến môi trường, dùng lazy import để không bắt buộc cài đủ mọi SDK.
* **Hệ thống Tài liệu dự án:** Biên soạn 3 tài liệu chính: [TAI_LIEU_DU_AN.md](/TAI_LIEU_DU_AN.md) (tài liệu BA/PO 18 mục: tổng quan, yêu cầu chức năng/phi chức năng, kiến trúc, đặc tả API, roadmap, rủi ro), [UI_GUIDE.md](/UI_GUIDE.md) (giải thích chi tiết FE/BE) và [CONNECT_GUIDE.md](/CONNECT_GUIDE.md) (hướng dẫn kết nối Frontend ↔ Server).

### 2. Minh họa Mã nguồn (Code Highlights):

* **Endpoint `/api/chat` — cầu nối Web ↔ ReAct Agent** trong [server.py](/src/fe/server.py):
```python
@app.post("/api/chat")
def chat(req: ChatRequest):
    """Nhan cau hoi -> Agent ReAct sinh cau tra loi -> tra ve JSON."""
    try:
        llm = get_provider(provider=req.provider, model=req.model or None)
        tools = [
            {"name": t["name"], "description": t["description"],
             "func": t["function"], "input_model": t.get("input_model")}
            for t in AVAILABLE_TOOLS
        ]
        agent = ReActAgent(llm=llm, tools=tools)
        start = time.perf_counter()
        history = [(m.role, m.content) for m in req.history]
        content = agent.run(req.question, history=history)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"ok": True, "content": content, "latency_ms": latency_ms, ...}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"ok": False, "error": str(e)}
```

* **Frontend gửi câu hỏi kèm ngữ cảnh hội thoại** trong [app.js](/src/fe/static/app.js):
```javascript
// Lấy lịch sử TRƯỚC khi push câu hỏi mới để tránh bị trùng
const historyMessages = (currentConvo()?.messages || []).slice(-10);
const history = historyMessages
  .filter((m) => m.role === "user" || m.role === "bot")
  .map((m) => ({ role: m.role, content: m.content }));

const res = await fetch("/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question, history }),
});
```

### 3. Cách code tương tác với vòng lặp ReAct:

Frontend (`app.js`) thu thập câu hỏi + 10 tin nhắn lịch sử → gửi JSON tới `server.py`. Backend khởi tạo `ReActAgent` với đầy đủ tools, truyền `history` vào `agent.run()`. Agent thực thi vòng lặp `Thought → Action → Observation` để gọi đúng công cụ (điểm số, chuyên cần, RAG…), rồi trả `Final Answer` ngược về server, server đóng gói JSON kèm latency, và app.js hiển thị thành bong bóng chat. Như vậy phần tôi làm chính là **lớp vỏ I/O** bao quanh và đưa lõi ReAct ra thành sản phẩm dùng được.

---

## II. Debugging Case Study (10 Points)

*Phân tích một lỗi thực tế gặp phải ở tầng Frontend/Backend khi tích hợp với ReAct Agent.*

### 1. Mô tả bài toán & Triệu chứng lỗi (Symptoms):

Khi kết nối giao diện chat với Agent, tôi gặp hai lỗi liên tiếp:
1. **Lỗi hiển thị (XSS/render):** Câu trả lời của Agent chứa các ký tự `<`, `>`, `&` (ví dụ khi gợi ý dạng bài tập, hoặc khi LLM lỡ trả về thẻ HTML) làm vỡ bố cục bong bóng chat, một số nội dung biến mất khỏi màn hình.
2. **Lỗi ngữ cảnh hội thoại bị trùng/lệch:** Khi phụ huynh hỏi câu hỏi tiếp nối (ví dụ "Thế còn môn Toán thì sao?"), Agent thường xuyên hiểu sai hoặc lặp lại câu trả lời trước, do lịch sử gửi lên bị **lẫn cả câu hỏi vừa nhập** (bị đếm hai lần).

### 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA):

1. **Render trực tiếp chuỗi chưa escape:** Ban đầu hàm `addBubble` gán thẳng nội dung Agent vào `innerHTML`. Trình duyệt diễn giải các ký tự `<...>` thành thẻ HTML thật thay vì văn bản, gây vỡ giao diện và tiềm ẩn lỗ hổng XSS.
2. **Thứ tự push & lấy lịch sử bị sai:** Trong hàm `send()`, ban đầu tôi `push` câu hỏi mới vào mảng `messages` **trước** rồi mới cắt lịch sử gửi đi. Hậu quả: câu hỏi hiện tại vừa nằm trong trường `question`, vừa nằm trong mảng `history` → Agent nhận một câu hỏi bị lặp hai lần, làm nhiễu vòng lặp `Thought`.

### 3. Giải pháp khắc phục (Mitigation & Fix):

1. **Escape HTML trước khi render:** Viết hàm `escapeHtml` chuyển đổi `& < >` thành thực thể HTML an toàn, áp dụng cho mọi nội dung trước khi đưa vào `innerHTML`:
```javascript
function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;")
                  .replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
```
2. **Lấy lịch sử TRƯỚC khi push câu hỏi mới:** Sửa lại thứ tự trong `send()` — đọc và cắt `history` (10 tin gần nhất) **trước**, rồi mới `push` câu hỏi hiện tại vào hội thoại. Nhờ đó payload gửi lên đúng dạng `{ question, history }` không trùng lặp, và Agent giữ đúng mạch hội thoại đa lượt.

Sau khi sửa, giao diện hiển thị ổn định mọi nội dung, các câu hỏi tiếp nối được Agent hiểu đúng ngữ cảnh, và phản hồi trả về mượt mà kèm chỉ số latency.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Suy ngẫm từ góc nhìn người xây dựng tầng giao diện & tích hợp.*

### 1. Năng lực Lập luận (Reasoning):

Khi tự tay đưa cả hai mô hình ra cùng một khung chat, tôi thấy rõ sự khác biệt: với Chatbot thuần, câu trả lời đến gần như tức thì nhưng **không có khả năng truy cập dữ liệu thật** của con (điểm số, chuyên cần) nên dễ trả lời chung chung hoặc bịa số. Ngược lại, ReAct Agent dùng khối `Thought` như một bộ định tuyến: nó tự xác định "thiếu dữ liệu gì → gọi tool nào" rồi mới kết luận. Từ phía Frontend, điều này thể hiện ra là độ trễ cao hơn (nên tôi phải thêm trạng thái "Đang trả lời...") nhưng đổi lại câu trả lời **bám sát dữ liệu thực và cá nhân hóa** đúng từng học sinh.

### 2. Độ tin cậy (Reliability):

ReAct Agent hoạt động **kém hơn** Chatbot ở các tình huống giao tiếp đơn giản: lời chào ("Chào em"), cảm ơn, hỏi xã giao. Với những câu này, một Chatbot trả lời trong < 200ms, còn Agent vẫn cố chạy vòng `Thought → Action`, làm tăng latency và token một cách lãng phí — điều mà tôi quan sát trực tiếp qua chỉ số `latency_ms` hiển thị dưới mỗi bong bóng chat trong giao diện.

### 3. Phản hồi Môi trường (Observation Influence):

Kết quả từ tool (`Observation`) định hình trực tiếp bước kế tiếp của Agent. Ví dụ khi tool trả về điểm Ngữ văn 6.0 kèm nhận xét "chưa tập trung văn tả cảnh", Agent lập tức gọi thêm công cụ RAG để lấy lời khuyên ôn tập đúng chủ đề — một chuỗi hành động mà Chatbot tĩnh không thể làm. Việc tôi gửi kèm `history` 10 tin nhắn cũng chính là cung cấp thêm "môi trường ngữ cảnh" để Agent quyết định chính xác hơn trong hội thoại đa lượt.

---

## IV. Future Improvements (5 Points)

*Đề xuất nâng cấp tầng Web & trải nghiệm lên cấp độ Production.*

1. **Streaming phản hồi (Server-Sent Events / WebSocket):**
   * *Hiện trạng:* Endpoint `/api/chat` chờ Agent chạy xong toàn bộ vòng lặp mới trả về một cục JSON, khiến phụ huynh phải chờ lâu trước màn hình "Đang trả lời...".
   * *Cải tiến:* Dùng `StreamingResponse` của FastAPI để stream từng token (và cả từng bước `Thought/Action`) về giao diện theo thời gian thực, giảm cảm giác chờ đợi và tăng độ tin cậy.

2. **Xác thực & Bảo mật học bạ (Authentication & Privacy):**
   * *Hiện trạng:* `/api/chat` chưa xác thực, ai cũng có thể hỏi về bất kỳ học sinh nào; lịch sử chỉ lưu ở `localStorage` của trình duyệt.
   * *Cải tiến:* Thêm đăng nhập phụ huynh (JWT/OTP), gắn token vào mỗi request để Agent chỉ truy cập đúng dữ liệu con của người dùng, và lưu hội thoại an toàn ở phía server.

3. **Lưu trữ hội thoại & quan sát phía server (Persistence & Observability):**
   * *Cải tiến:* Thay `localStorage` bằng cơ sở dữ liệu (PostgreSQL) để đồng bộ lịch sử đa thiết bị; xây dashboard giám sát telemetry (latency, token, tỷ lệ lỗi, số bước ReAct trung bình) để theo dõi chất lượng trợ lý ở quy mô nhiều phụ huynh.
