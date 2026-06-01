import json
import os
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.ollama_provider import OllamaProvider


def _post_json(url: str, payload: dict, timeout: int = 120) -> dict:
	data = json.dumps(payload).encode("utf-8")
	req = urllib.request.Request(
		url,
		data=data,
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	with urllib.request.urlopen(req, timeout=timeout) as response:
		return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, timeout: int = 10) -> dict:
	with urllib.request.urlopen(url, timeout=timeout) as response:
		return json.loads(response.read().decode("utf-8"))


def test_ollama_local():
	load_dotenv()

	base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
	model_name = os.getenv("OLLAMA_MODEL", "llama3.1:3b")

	print("--- Testing Ollama Local ---")
	print(f"Base URL: {base_url}")
	print(f"Model: {model_name}")

	try:
		_get_json(f"{base_url}/api/tags")
	except Exception as exc:
		print(f"❌ Cannot connect to Ollama at {base_url}")
		print(f"Details: {exc}")
		print("Start Ollama first: ollama serve")
		return

	prompt = "Explain what an AI Agent is in one sentence."

	try:
		provider = OllamaProvider(model_name=model_name, base_url=base_url)
		result = provider.generate(prompt)
	except urllib.error.HTTPError as exc:
		body = exc.read().decode("utf-8", errors="replace")
		print(f"❌ Ollama API error: HTTP {exc.code}")
		print(body)
		return
	except Exception as exc:
		print(f"❌ Request failed: {exc}")
		return

	answer = (result.get("content") or "").strip()
	if not answer:
		print("❌ No response text returned by Ollama")
		print(result)
		return

	print(f"\nUser: {prompt}")
	print(f"Assistant: {answer}")
	print("\n✅ Ollama test passed")


if __name__ == "__main__":
	test_ollama_local()
