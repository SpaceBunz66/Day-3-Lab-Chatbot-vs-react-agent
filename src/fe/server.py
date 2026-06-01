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

# Cho phep import "src.*"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from src.core.factory import get_provider
from src.telemetry.logger import logger

load_dotenv()

app = FastAPI(title="Lab 3 - Chat LLM")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ChatRequest(BaseModel):
    question: str
    provider: str | None = None
    model: str | None = None


# Vai tro cua tro ly: ho tro phu huynh ve viec hoc cua con
SYSTEM_PROMPT = """"""


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Nhan cau hoi -> LLM sinh cau tra loi -> tra ve JSON."""
    try:
        llm = get_provider(provider=req.provider, model=req.model or None)
        result = llm.generate(req.question, system_prompt=SYSTEM_PROMPT)
        logger.log_event("UI_CHAT", {
            "provider": req.provider or os.getenv("DEFAULT_PROVIDER", "openai"),
            "question": req.question,
        })
        return {"ok": True, **result}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# Phuc vu cac file tinh (css, js)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
