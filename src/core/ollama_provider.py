import json
import time
from typing import Dict, Any, Optional, Generator
import urllib.request
import urllib.error

from src.core.llm_provider import LLMProvider


class OllamaProvider(LLMProvider):
    """
    LLM provider for local models served by Ollama.
    """

    def __init__(
        self,
        model_name: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")
        self.options = options or {}

    def _post_json(self, path: str, payload: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if self.options:
            payload["options"] = self.options

        data = self._post_json("/api/generate", payload, timeout=120)
        end_time = time.time()

        total_duration_ns = data.get("total_duration")
        if isinstance(total_duration_ns, (int, float)):
            latency_ms = int(total_duration_ns / 1_000_000)
        else:
            latency_ms = int((end_time - start_time) * 1000)

        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or 0)

        return {
            "content": (data.get("response") or "").strip(),
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "latency_ms": latency_ms,
            "provider": "ollama",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if self.options:
            payload["options"] = self.options

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = chunk.get("response")
                if token:
                    yield token

                if chunk.get("done"):
                    break
