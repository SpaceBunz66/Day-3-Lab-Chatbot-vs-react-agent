"""
Factory: đọc cấu hình và tạo ra đúng LLM Provider.
Đây là "công tắc" nối câu hỏi của người dùng với nơi LLM sinh câu trả lời.
"""
import os
from typing import Optional
from src.core.llm_provider import LLMProvider


def get_provider(provider: Optional[str] = None,
                 model: Optional[str] = None) -> LLMProvider:
    """
    Tạo một LLMProvider dựa trên tham số hoặc biến môi trường (.env).

    Args:
        provider: "openai" | "google" | "local". Mặc định lấy từ DEFAULT_PROVIDER.
        model: tên model. Mặc định lấy từ DEFAULT_MODEL.

    Import được đặt bên trong từng nhánh (lazy import) để không bắt buộc
    cài đủ cả 3 SDK mới chạy được.
    """
    provider = (provider or os.getenv("DEFAULT_PROVIDER", "openai")).lower()

    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model_name=model or os.getenv("DEFAULT_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if provider in ("google", "gemini"):
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(
            model_name=model or os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    if provider == "local":
        from src.core.local_provider import LocalProvider
        return LocalProvider(
            model_path=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"),
        )

    if provider == "ollama":
        from src.core.ollama_provider import OllamaProvider
        return OllamaProvider(
            model_name=model or os.getenv("DEFAULT_MODEL", "llama3"),
            host=os.getenv("OLLAMA_HOST"),
        )

    raise ValueError(
        f"Provider khong ho tro: {provider!r}. Dung: openai | google | local | ollama"
    )
