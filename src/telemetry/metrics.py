import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from src.telemetry.logger import logger

# Bảng giá USD per 1K tokens (input / output)
PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o":               {"input": 0.005,   "output": 0.015},
    "gpt-4o-mini":          {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo":          {"input": 0.01,    "output": 0.03},
    "gpt-3.5-turbo":        {"input": 0.0005,  "output": 0.0015},
    # Google Gemini
    "gemini-1.5-flash":     {"input": 0.000075,"output": 0.0003},
    "gemini-1.5-pro":       {"input": 0.00125, "output": 0.005},
    "gemini-2.0-flash":     {"input": 0.0001,  "output": 0.0004},
    # Ollama / local — free (zero cost)
    "_default_local":       {"input": 0.0,     "output": 0.0},
}

COST_LOG_DIR = "logs"
COST_LOG_FILE = os.path.join(COST_LOG_DIR, "cost_metrics.json")


def _load_log() -> List[Dict[str, Any]]:
    if os.path.exists(COST_LOG_FILE):
        try:
            with open(COST_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_log(records: List[Dict[str, Any]]) -> None:
    os.makedirs(COST_LOG_DIR, exist_ok=True)
    with open(COST_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


class PerformanceTracker:
    """Tracking industry-standard metrics for LLMs and persisting to JSON."""

    def __init__(self):
        self.session_metrics: List[Dict[str, Any]] = []

    def track_request(
        self,
        provider: str,
        model: str,
        usage: Dict[str, int],
        latency_ms: int,
    ) -> None:
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens
        input_cost, output_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        metric = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "cost_input_usd": round(input_cost, 8),
            "cost_output_usd": round(output_cost, 8),
            "cost_total_usd": round(input_cost + output_cost, 8),
        }

        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

        # Persist to JSON file
        records = _load_log()
        records.append(metric)
        _save_log(records)

    def get_session_summary(self) -> Dict[str, Any]:
        """Tổng kết chi phí & token của toàn session hiện tại."""
        if not self.session_metrics:
            return {}
        return {
            "total_requests": len(self.session_metrics),
            "total_input_tokens": sum(m["input_tokens"] for m in self.session_metrics),
            "total_output_tokens": sum(m["output_tokens"] for m in self.session_metrics),
            "total_tokens": sum(m["total_tokens"] for m in self.session_metrics),
            "total_latency_ms": sum(m["latency_ms"] for m in self.session_metrics),
            "avg_latency_ms": int(sum(m["latency_ms"] for m in self.session_metrics) / len(self.session_metrics)),
            "total_cost_usd": round(sum(m["cost_total_usd"] for m in self.session_metrics), 8),
        }

    def _calculate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> tuple[float, float]:
        price = PRICING.get(model) or PRICING.get("_default_local")
        input_cost = (prompt_tokens / 1000) * price["input"]
        output_cost = (completion_tokens / 1000) * price["output"]
        return input_cost, output_cost


# Global tracker instance
tracker = PerformanceTracker()
