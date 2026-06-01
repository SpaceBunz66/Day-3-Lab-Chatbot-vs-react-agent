"""
Tests for tools and agent logic — no real LLM required.

Run with:
    python -m pytest tests/test_tools_and_agent.py -v
or:
    python tests/test_tools_and_agent.py
"""

import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Tool imports ─────────────────────────────────────────────────────────────
from src.tools.tools_academic import get_student_academic_records, get_daily_activity_and_wellbeing
from src.tools.tools_resources import get_learning_resources
from src.tools import AVAILABLE_TOOLS

# ─── Agent + LLMProvider imports ──────────────────────────────────────────────
from typing import Optional, Generator, Dict, Any
from src.core.llm_provider import LLMProvider
from src.agent.agent import ReActAgent


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Tool Unit Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_academic_records_valid():
    result = json.loads(get_student_academic_records("HS001"))
    assert result["name"] == "Nguyễn Minh Quân"
    assert "subjects" in result["records"]
    print("PASS test_academic_records_valid passed")

def test_academic_records_invalid():
    result = json.loads(get_student_academic_records("HS999"))
    assert "error" in result
    print("PASS test_academic_records_invalid passed")

def test_daily_activity_valid():
    result = json.loads(get_daily_activity_and_wellbeing("HS002"))
    assert result["name"] == "Trần Tuệ Lâm"
    assert "meals" in result["daily_life"]
    print("PASS test_daily_activity_valid passed")

def test_daily_activity_invalid():
    result = json.loads(get_daily_activity_and_wellbeing("HS000"))
    assert "error" in result
    print("PASS test_daily_activity_invalid passed")

def test_learning_resources_with_subject():
    result = json.loads(get_learning_resources("HS001", "Toán"))
    assert result["grade"] == 4
    assert len(result["resources"]) > 0
    print("PASS test_learning_resources_with_subject passed")

def test_learning_resources_with_topic_filter():
    result = json.loads(get_learning_resources("HS001", "Toán", topic="cửu chương"))
    assert len(result["resources"]) > 0
    print("PASS test_learning_resources_with_topic_filter passed")

def test_learning_resources_topic_no_match():
    result = json.loads(get_learning_resources("HS001", "Toán", topic="lượng giác"))
    assert result["resources"] == []
    print("PASS test_learning_resources_topic_no_match passed")

def test_available_tools_structure():
    assert len(AVAILABLE_TOOLS) == 3
    for tool in AVAILABLE_TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "function" in tool
        assert "input_model" in tool
    print("PASS test_available_tools_structure passed")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Mock LLM Provider
# ══════════════════════════════════════════════════════════════════════════════

class MockLLMProvider(LLMProvider):
    """
    Fake LLM trả về các response được viết sẵn theo thứ tự.
    Dùng để test ReAct loop mà không cần model thật.
    """
    def __init__(self, scripted_responses: list):
        super().__init__(model_name="mock-llm")
        self._responses = scripted_responses
        self._call_count = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if self._call_count >= len(self._responses):
            content = "Final Answer: Hết script."
        else:
            content = self._responses[self._call_count]
        self._call_count += 1
        return {
            "content": content,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "latency_ms": 10
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt)["content"]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Agent Integration Tests (no real LLM)
# ══════════════════════════════════════════════════════════════════════════════

def test_agent_single_tool_call():
    """Agent gọi 1 tool rồi trả Final Answer."""
    mock = MockLLMProvider([
        'Thought: Cần tra điểm của học sinh.\nAction: get_student_academic_records({"student_id": "HS001"})',
        'Final Answer: Con bạn học khá tốt môn Tiếng Việt.'
    ])
    agent = ReActAgent(llm=mock, tools=AVAILABLE_TOOLS)
    result = agent.run("Con tôi học thế nào?")
    assert "Final Answer" not in result  # agent đã strip prefix
    assert len(result) > 0
    print("PASS test_agent_single_tool_call passed")

def test_agent_multi_tool_call():
    """Agent gọi 2 tool khác nhau trước khi ra Final Answer."""
    mock = MockLLMProvider([
        'Thought: Cần điểm trước.\nAction: get_student_academic_records({"student_id": "HS001"})',
        'Thought: Cần thêm thông tin sinh hoạt.\nAction: get_daily_activity_and_wellbeing({"student_id": "HS001"})',
        'Final Answer: Con bạn hôm nay ăn tốt và điểm Toán cần cải thiện.'
    ])
    agent = ReActAgent(llm=mock, tools=AVAILABLE_TOOLS)
    result = agent.run("Hôm nay con tôi thế nào?")
    assert mock._call_count == 3
    assert len(result) > 0
    print("PASS test_agent_multi_tool_call passed (3 LLM calls)")

def test_agent_parser_error_recovery():
    """Agent nhận lỗi parse format rồi tự sửa ở bước sau."""
    mock = MockLLMProvider([
        'Thought: ...\nAction: get_student_academic_records(student_id=HS001)',  # sai format
        'Thought: Sửa lại đúng JSON.\nAction: get_student_academic_records({"student_id": "HS001"})',
        'Final Answer: Đây là kết quả.'
    ])
    agent = ReActAgent(llm=mock, tools=AVAILABLE_TOOLS)
    result = agent.run("Điểm học sinh HS001?")
    assert len(result) > 0
    print("PASS test_agent_parser_error_recovery passed")

def test_agent_timeout():
    """Agent vượt max_steps mà không ra Final Answer → trả về thông báo timeout."""
    mock = MockLLMProvider([
        'Thought: ...\nAction: get_student_academic_records({"student_id": "HS001"})',
        'Thought: ...\nAction: get_student_academic_records({"student_id": "HS001"})',
        'Thought: ...\nAction: get_student_academic_records({"student_id": "HS001"})',
    ])
    agent = ReActAgent(llm=mock, tools=AVAILABLE_TOOLS, max_steps=3)
    result = agent.run("Câu hỏi không có hồi kết?")
    assert "Xin lỗi" in result
    print("PASS test_agent_timeout passed")

def test_agent_hallucinated_tool():
    """Agent gọi tool không tồn tại → nhận error observation, xử lý tiếp."""
    mock = MockLLMProvider([
        'Thought: ...\nAction: get_exam_schedule({"student_id": "HS001"})',  # tool không có
        'Final Answer: Xin lỗi, không có thông tin lịch thi.'
    ])
    agent = ReActAgent(llm=mock, tools=AVAILABLE_TOOLS)
    result = agent.run("Lịch thi của con?")
    assert len(result) > 0
    print("PASS test_agent_hallucinated_tool passed")


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n=== SECTION 1: Tool Unit Tests ===")
    test_academic_records_valid()
    test_academic_records_invalid()
    test_daily_activity_valid()
    test_daily_activity_invalid()
    test_learning_resources_with_subject()
    test_learning_resources_with_topic_filter()
    test_learning_resources_topic_no_match()
    test_available_tools_structure()

    print("\n=== SECTION 2: Agent Integration Tests (Mock LLM) ===")
    test_agent_single_tool_call()
    test_agent_multi_tool_call()
    test_agent_parser_error_recovery()
    test_agent_timeout()
    test_agent_hallucinated_tool()

    print("\nAll tests passed!")
