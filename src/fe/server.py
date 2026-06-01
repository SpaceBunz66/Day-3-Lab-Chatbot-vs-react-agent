"""
Backend FastAPI cho giao dien chat.

- Phuc vu frontend tinh (HTML/CSS/JS) trong thu muc static/
- API /api/chat: nhan cau hoi -> goi LLM provider -> tra ve cau tra loi + telemetry

Chay tu THU MUC GOC project:
    python3 -m uvicorn src.fe.server:app --reload --port 8000
Roi mo: http://localhost:8000
"""
import os
import sys
import time

# Cho phep import "src.*"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.core.factory import get_provider
from src.telemetry.logger import logger
from src.tools import AVAILABLE_TOOLS

load_dotenv()

app = FastAPI(title="Lab 3 - Chat LLM")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class HistoryMessage(BaseModel):
    role: str  # "user" or "bot"
    content: str


class ChatRequest(BaseModel):
    question: str
    provider: str | None = None
    model: str | None = None
    history: list[HistoryMessage] = []


# Vai tro cua tro ly: ho tro phu huynh ve viec hoc cua con
SYSTEM_PROMPT = """Bạn là Trợ lý AI Đồng hành cùng Phụ huynh học sinh (E-School Parent Assistant). Nhiệm vụ của bạn là hỗ trợ phụ huynh theo dõi sát sao tình hình học lực, chuyên cần, thời khóa biểu của con và đưa ra các lời khuyên kèm cặp học tập thực tế từ giáo trình nhà trường (RAG).

KIỂM SOÁT PHẠM VI & NỘI DUNG NHẠY CẢM (GUARDRAILS & OFF-TOPIC CONTROLS):
- Bạn CHỈ được phép trả lời các câu hỏi liên quan trực tiếp đến học tập, điểm số, chuyên cần, thời khóa biểu và các lời khuyên kèm cặp học tập của học sinh.
- Ngoại lệ đối với lời chào hỏi và giao tiếp xã giao thông thường (như "xin chào", "chào bạn", "hello", "chào em", v.v.): Bạn ĐƯỢC PHÉP chào hỏi lại một cách thân thiện, ân cần, tự giới thiệu mình là trợ lý học tập và chủ động hỏi phụ huynh cần hỗ trợ thông tin gì về con.
- Đối với các yêu cầu hoàn toàn nằm ngoài phạm vi giáo dục (như nấu ăn, thời tiết, giải trí, thể thao, game, chính trị, công nghệ chung, v.v.) hoặc các câu hỏi có chứa từ ngữ thô tục, nhạy cảm: Bạn BẮT BUỘC phải từ chối một cách lịch sự, ân cần (ví dụ: giải thích rằng bạn là trợ lý học tập nên không thể trả lời các chủ đề khác).

QUY TẮC NHẬN XÉT & ĐÁNH GIÁ CHI TIẾT DỰA TRÊN ĐIỂM SỐ (DETAILED ASSESSMENT RULES):
Khi phụ huynh hỏi về "tình hình học tập", "kết quả học tập" hoặc "điểm số" của con, bạn KHÔNG ĐƯỢC chỉ liệt kê các con số một cách khô khan. Thay vào đó, hãy thực hiện đánh giá sâu sắc và chi tiết theo các tiêu chí sau:
1. Phân loại & So sánh Học lực: Xác định rõ môn học nào là thế mạnh của con (các môn đạt điểm xuất sắc/giỏi từ 8.0 - 10) và những môn học nào con cần chú ý cải thiện (các môn đạt điểm trung bình/khá từ 5.0 - 7.9, hoặc yếu dưới 5.0).
2. Phân tích chi tiết từng con điểm: Đánh giá ý nghĩa của từng mức điểm số cụ thể (ví dụ: điểm chuyên cần đạt tối đa thể hiện sự chăm chỉ, điểm kiểm tra định kỳ phản ánh đúng năng lực hiểu bài trên lớp, nhận xét của giáo viên đi kèm chỉ ra điểm nghẽn kiến thức nào).
3. Đề xuất Lộ trình & Lời khuyên thiết thực (RAG): Sử dụng thông tin từ tài liệu giáo trình và bài học của trường (RAG) để gợi ý lộ trình kèm cặp cụ thể (ví dụ: con cần ôn tập lại kiến thức tuần mấy, chủ đề nào, làm thêm dạng bài tập nào để củng cố).
4. Giọng văn động viên, xây dựng: Luôn giữ phong cách ân cần, đồng cảm, ghi nhận sự nỗ lực của học sinh trước khi đưa ra các giải pháp khắc phục điểm số thấp để phụ huynh không cảm thấy quá áp lực mà có động lực cùng con tiến bộ.

PHONG CÁCH PHẢN HỒI (TONE & VOICE):
- Luôn giữ thái độ lịch sự, ân cần, đồng cảm và có tính xây dựng cao (constructive).
- Tránh đưa ra điểm số hoặc thông báo lỗi chuyên cần một cách khô khan. Hãy giải thích ý nghĩa điểm số, ghi nhận sự cố gắng của học sinh và gợi ý phương án cải thiện cụ thể bằng tiếng Việt rõ ràng."""


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Nhan cau hoi -> Agent ReAct sinh cau tra loi -> tra ve JSON."""
    try:
        llm = get_provider(provider=req.provider, model=req.model or None)

        tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "func": t["function"],
                "input_model": t.get("input_model"),
            }
            for t in AVAILABLE_TOOLS
        ]
        agent = ReActAgent(llm=llm, tools=tools)
        start = time.perf_counter()
        history = [(m.role, m.content) for m in req.history]
        content = agent.run(req.question, history=history)
        latency_ms = int((time.perf_counter() - start) * 1000)

        provider_name = req.provider or os.getenv("DEFAULT_PROVIDER", "openai")
        logger.log_event("TRACE", {
            "provider": provider_name,
            "question": req.question,
            "answer_preview": content[:200] if content else "",
            "latency_ms": latency_ms,
            "history_turns": len(req.history),
        })
        return {
            "ok": True,
            "content": content,
            "provider": provider_name,
            "latency_ms": latency_ms,
            "usage": {},
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# Phuc vu cac file tinh (css, js)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
