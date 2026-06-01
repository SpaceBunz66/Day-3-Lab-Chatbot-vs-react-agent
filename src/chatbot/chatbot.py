import os
import sys
from typing import Dict, Any, Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


SYSTEM_PROMPT = """Bạn là Trợ lý AI hỗ trợ Phụ huynh học sinh tiểu học.
Hãy trả lời câu hỏi của phụ huynh một cách nhẹ nhàng, thân thiện và dễ hiểu.
Nếu không biết thông tin cụ thể (điểm số, bữa ăn, lịch học...), hãy thành thật nói rõ
rằng bạn không có dữ liệu thực tế và đề nghị phụ huynh liên hệ trực tiếp nhà trường."""


class SimpleChatbot:
    """
    Chatbot không có tool, không có loop.
    Mỗi câu hỏi = 1 lần gọi LLM → 1 câu trả lời.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.history: list = []

    def chat(self, user_input: str) -> str:
        """Gửi câu hỏi tới LLM và trả về câu trả lời."""
        logger.log_event("CHATBOT_REQUEST", {
            "input": user_input,
            "model": self.llm.model_name
        })

        # Xây dựng context gồm toàn bộ lịch sử hội thoại
        context = self._build_context(user_input)

        result = self.llm.generate(context, system_prompt=SYSTEM_PROMPT)

        tracker.track_request(
            provider=getattr(self.llm, "provider_name", "unknown"),
            model=self.llm.model_name,
            usage=result["usage"],
            latency_ms=result["latency_ms"]
        )

        response = result["content"].strip()

        # Lưu lịch sử để hỗ trợ hội thoại nhiều lượt
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response})

        logger.log_event("CHATBOT_RESPONSE", {
            "output": response,
            "latency_ms": result["latency_ms"],
            "total_tokens": result["usage"]["total_tokens"]
        })

        return response

    def reset(self):
        """Xóa lịch sử — bắt đầu cuộc hội thoại mới."""
        self.history = []

    def _build_context(self, user_input: str) -> str:
        """Ghép lịch sử hội thoại + câu hỏi hiện tại thành một chuỗi context."""
        lines = []
        for turn in self.history:
            prefix = "Phụ huynh" if turn["role"] == "user" else "Trợ lý"
            lines.append(f"{prefix}: {turn['content']}")
        lines.append(f"Phụ huynh: {user_input}")
        return "\n".join(lines)


# ─── Demo CLI ──────────────────────────────────────────────────────────────────

TEST_CASES = [
    # Câu đơn giản — chatbot có thể xử lý được
    "Xin chào, tôi cần hỏi về tình hình học tập của con.",
    # Câu đa bước — chatbot sẽ không có dữ liệu thực, bộc lộ giới hạn
    "Con tôi mã HS001. Hôm nay con ăn gì và điểm Toán gần nhất là bao nhiêu?",
    # Câu yêu cầu tra cứu cụ thể — chatbot đành đoán hoặc từ chối
    "Cho tôi biết tài liệu ôn Toán phù hợp với khối lớp của con HS002.",
]


def run_demo(llm: LLMProvider):
    """Chạy chatbot qua bộ test cases mẫu và in kết quả."""
    bot = SimpleChatbot(llm)

    print("=" * 60)
    print("CHATBOT BASELINE — Không có tool, không có vòng lặp")
    print("=" * 60)

    for i, question in enumerate(TEST_CASES, 1):
        print(f"\n[Test {i}] Phụ huynh: {question}")
        print("-" * 40)
        answer = bot.chat(question)
        print(f"Chatbot: {answer}")

    print("\n" + "=" * 60)
    print("Kết thúc demo. Xem logs/ để so sánh với ReAct Agent.")
    print("=" * 60)


if __name__ == "__main__":
    # Ví dụ chạy với LocalProvider (không cần API key)
    # Thay bằng OpenAIProvider hoặc GeminiProvider nếu có key.
    try:
        from src.core.local_provider import LocalProvider

        model_path = os.environ.get(
            "LOCAL_MODEL_PATH",
            "models/phi-3-mini-4k-instruct-q4.gguf"
        )
        llm = LocalProvider(model_path=model_path)
        run_demo(llm)

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print("Đặt biến môi trường LOCAL_MODEL_PATH=<đường dẫn file .gguf> rồi chạy lại.")
        sys.exit(1)
    except ImportError:
        print("[ERROR] llama-cpp-python chưa được cài. Chạy: pip install llama-cpp-python")
        sys.exit(1)
