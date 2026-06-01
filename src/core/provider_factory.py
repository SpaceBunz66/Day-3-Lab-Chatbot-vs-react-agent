import os
from typing import Optional

from src.core.llm_provider import LLMProvider


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def create_provider_from_env() -> LLMProvider:
    provider = os.getenv("DEFAULT_PROVIDER", "openai").strip().lower()

    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider

        model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIProvider(model_name=model_name, api_key=api_key)

    if provider in ("google", "gemini"):
        from src.core.gemini_provider import GeminiProvider

        model_name = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
        api_key = os.getenv("GEMINI_API_KEY")
        return GeminiProvider(model_name=model_name, api_key=api_key)

    if provider == "local":
        from src.core.local_provider import LocalProvider

        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        n_ctx = int(os.getenv("LOCAL_N_CTX", "4096"))
        n_threads = _parse_optional_int(os.getenv("LOCAL_N_THREADS"))
        return LocalProvider(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads)

    if provider == "ollama":
        from src.core.ollama_provider import OllamaProvider

        model_name = os.getenv("OLLAMA_MODEL") or os.getenv("DEFAULT_MODEL", "llama3.1:8b")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaProvider(model_name=model_name, base_url=base_url)

    raise ValueError(
        f"Unsupported DEFAULT_PROVIDER='{provider}'. Use one of: openai, google, local, ollama."
    )
