import os
import re
import inspect
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

try:
    from src.tools.mock_db import STUDENT_DB, DAILY_LIFE_DB, RESOURCE_DB
except Exception:
    STUDENT_DB = {}
    DAILY_LIFE_DB = {}
    RESOURCE_DB = {}

class ReActAgent:
    """
    A robust ReAct-style Agent that follows the Thought-Action-Observation loop.
    Supports dynamic tool execution, argument parsing, and detailed log telemetry.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def _is_greeting(self, user_input: str) -> bool:
        """Detect short greeting-only messages to avoid unnecessary ReAct loops."""
        text = (user_input or "").strip().lower()
        if not text:
            return False

        greeting_keywords = {
            "chao", "chào", "xin chao", "xin chào", "hello", "hi", "alo", "hey"
        }
        if text in greeting_keywords:
            return True

        # Accept simple greeting variants with punctuation.
        normalized = re.sub(r"[!?.\s]+", " ", text).strip()
        return normalized in greeting_keywords

    def _build_greeting_response(self) -> str:
        return (
            "Chào bạn, mình là trợ lý học tập của phụ huynh. "
            "Mình có thể hỗ trợ theo dõi điểm, chuyên cần, thời khóa biểu và gợi ý cách kèm con học hiệu quả."
        )

    def _clean_response(self, text: str) -> str:
        """Xóa các nhãn nội bộ Thought: / Action: / Final Answer: trước khi trả về FE."""
        # Xóa toàn bộ các dòng bắt đầu bằng Thought:
        text = re.sub(r"(?im)^Thought:.*?(?=\nFinal Answer:|\nAction:|\Z)", "", text, flags=re.DOTALL)
        # Xóa tiền tố Final Answer:
        text = re.sub(r"(?i)^Final Answer:\s*", "", text.strip())
        # Xóa các dòng Action: ... (artifact của ReAct)
        text = re.sub(r"(?im)^Action:\s*\S+.*$", "", text)
        text = re.sub(r"(?im)^Action Input:\s*.*$", "", text)
        text = re.sub(r"(?im)^Observation:\s*.*$", "", text)
        # Xóa các dòng trống thừa
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_student_id(self, text: str) -> Optional[str]:
        match = re.search(r"\bHS\d{3}\b", text or "", flags=re.IGNORECASE)
        if match:
            return match.group(0).upper()

        normalized = (text or "").lower()
        for student_id, info in STUDENT_DB.items():
            name = str(info.get("name", "")).lower()
            if name and name in normalized:
                return student_id
        return None

    def _load_student_profile(self, student_id: str) -> str:
        """Load full student data (academic + daily) into a readable context block."""
        lines = []
        student = STUDENT_DB.get(student_id)
        if student:
            name = student.get("name", student_id)
            grade = student.get("grade", "?")
            cls = student.get("class", "?")
            attendance = student.get("attendance_rate", "?")
            remark = student.get("teacher_remark", "")
            lines.append(f"HỌC SINH: {name} | Lớp {cls} | Khối {grade} | Chuyên cần: {attendance}")
            for subject, score in student.get("subjects", {}).items():
                lines.append(
                    f"  - {subject}: giữa kỳ {score.get('midterm','?')}, "
                    f"cuối kỳ {score.get('final','?')} → {score.get('status','?')}"
                )
            if remark:
                lines.append(f"  Nhận xét GV: {remark}")

        daily = DAILY_LIFE_DB.get(student_id)
        if daily:
            meals = daily.get("meals", {})
            lines.append(f"SINH HOẠT HÔM NAY ({daily.get('date', '?')})")
            lines.append(f"  - Bữa sáng: {meals.get('breakfast', '?')}")
            lines.append(f"  - Bữa trưa: {meals.get('lunch', '?')}")
            lines.append(f"  - Bữa phụ: {meals.get('snack', '?')}")
            lines.append(f"  - Sức khỏe: {daily.get('health_status', '?')}")
            lines.append(f"  - Tâm lý: {daily.get('psychology_status', '?')}")
            note = daily.get("teacher_note", "")
            if note:
                lines.append(f"  - Lưu ý GV: {note}")

        return "\n".join(lines) if lines else ""

    def _detect_student_from_conversation(
        self, current_input: str, history: List[tuple]
    ) -> Optional[str]:
        """Detect student from current message or any previous turn in history."""
        all_texts = [current_input] + [content for _, content in history]
        for text in all_texts:
            student_id = self._extract_student_id(text)
            if student_id:
                return student_id
        return None

    def _find_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        for tool in self.tools:
            if tool.get("name") == tool_name:
                return tool
        return None

    def _invoke_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> Optional[str]:
        tool = self._find_tool(tool_name)
        if not tool:
            return None
        try:
            func = tool.get("func") or tool.get("function")
            if not callable(func):
                return None
            input_model = tool.get("input_model")
            if input_model is not None:
                validated = input_model(**kwargs)
                kwargs = validated.model_dump()
            return str(func(**kwargs))
        except Exception as exc:
            return f"Error executing tool '{tool_name}': {exc}"

    # --- keyword sets for intent detection ---
    _ATTENDANCE_KW = {
        "muộn", "muon", "muôn", "trễ", "tre", "vắng", "vang",
        "nghỉ", "nghi", "buổi", "buoi", "điểm danh", "chuyên cần",
        "đúng giờ", "ngày nghỉ",
    }
    _SCORE_KW = {
        "điểm", "diem", "học lực", "hoc luc", "bảng điểm", "môn",
        "toán", "văn", "anh", "tiếng việt",
    }
    _FULL_KW = {
        "tình hình", "tinh hinh", "kết quả", "ket qua", "học tập",
        "hoc tap", "tổng hợp", "nhận xét", "nhan xet", "gợi ý", "goi y",
    }

    def _detect_intent(self, question: str) -> str:
        """Return 'attendance', 'scores', or 'full' based on question keywords."""
        q = (question or "").lower()
        tokens = set(re.split(r"[\s,;]+", q))
        # Check multi-word phrases first
        if any(kw in q for kw in self._FULL_KW):
            return "full"
        if any(kw in q for kw in self._ATTENDANCE_KW):
            return "attendance"
        if any(kw in q for kw in self._SCORE_KW):
            return "scores"
        return "full"

    def _build_tool_response(self, raw: str, question: str = "") -> str:
        try:
            data = json.loads(raw)
        except Exception:
            return raw

        if isinstance(data, dict) and data.get("error"):
            return str(data["error"])

        # --- Academic records ---
        if isinstance(data, dict) and data.get("name") and data.get("subjects"):
            name = data.get("name", "Học sinh")
            grade = data.get("grade", "?")
            cls = data.get("class", "?")
            attendance = data.get("attendance_rate", "?")
            remark = data.get("teacher_remark", "")
            subjects = data.get("subjects", {})
            late_days = data.get("late_days")
            absent_days = data.get("absent_days")
            total_sessions = data.get("total_sessions")

            intent = self._detect_intent(question)
            header = f"📋 {name}  (Lớp {cls} · Khối {grade})\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

            # Build attendance block
            def attendance_block():
                attend_line = f"📅 Tỉ lệ chuyên cần: {attendance}"
                if total_sessions is not None:
                    attend_line += f"  (/{total_sessions} buổi)"
                lines = [header, attend_line]
                if late_days is not None:
                    icon = "⚠️" if late_days > 5 else ("🟡" if late_days > 0 else "✅")
                    lines.append(f"  {icon} Đi học muộn: {late_days} buổi")
                if absent_days is not None:
                    icon = "🔴" if absent_days > 10 else ("⚠️" if absent_days > 3 else "✅")
                    lines.append(f"  {icon} Nghỉ học: {absent_days} buổi")
                return lines

            # Build scores block
            def scores_block():
                excellent, good, weak = [], [], []
                for subj, score in subjects.items():
                    avg = (score.get("midterm", 0) + score.get("final", 0)) / 2
                    status = score.get("status", "")
                    if status == "Xuất sắc" or avg >= 8.5:
                        excellent.append((subj, score))
                    elif status in ("Tốt", "Khá") or avg >= 6.5:
                        good.append((subj, score))
                    else:
                        weak.append((subj, score))

                lines = ["📊 ĐIỂM SỐ TỪNG MÔN:"]
                for subject, score in subjects.items():
                    midterm = score.get("midterm", "?")
                    final = score.get("final", "?")
                    status = score.get("status", "")
                    trend = ""
                    if isinstance(midterm, (int, float)) and isinstance(final, (int, float)):
                        trend = " 📈" if final > midterm else (" 📉" if final < midterm else " ➡️")
                    emoji = "🌟" if status == "Xuất sắc" else ("✅" if status in ("Tốt", "Khá") else "⚠️")
                    lines.append(f"  {emoji} {subject}: GK {midterm} → CK {final}{trend}  [{status}]")
                return lines, weak

            if intent == "attendance":
                return "\n".join(attendance_block())

            if intent == "scores":
                score_lines, _ = scores_block()
                return "\n".join([header] + score_lines)

            # intent == "full"
            lines = attendance_block()
            lines.append("")

            score_lines, weak = scores_block()
            lines += score_lines

            # Phân tích học lực
            excellent_s = [s for s, sc in subjects.items() if (sc.get("midterm",0)+sc.get("final",0))/2 >= 8.5 or sc.get("status") == "Xuất sắc"]
            good_s     = [s for s, sc in subjects.items() if s not in excellent_s and ((sc.get("midterm",0)+sc.get("final",0))/2 >= 6.5)]
            weak_s     = [s for s, sc in subjects.items() if s not in excellent_s and s not in good_s]

            lines += ["", "📝 NHẬN XÉT HỌC LỰC:"]
            if excellent_s:
                lines.append(f"  🌟 Thế mạnh: {', '.join(excellent_s)}")
            if good_s:
                lines.append(f"  ✅ Ổn định: {', '.join(good_s)}")
            if weak_s:
                lines.append(f"  ⚠️ Cần tập trung: {', '.join(weak_s)}")

            if remark:
                lines += ["", f"💬 Giáo viên nhận xét:", f"  \"{remark}\""]

            # Gợi ý tài liệu cho môn yếu
            resource_lines = []
            for subj in weak_s:
                grade_int = grade if isinstance(grade, int) else int(str(grade))
                for res in RESOURCE_DB.get(subj, {}).get(grade_int, [])[:2]:
                    resource_lines.append(f"  📚 [{res['type']}] {res['title']}")
            if resource_lines:
                lines += ["", "🎯 TÀI LIỆU GỢI Ý:"]
                lines += resource_lines

            lines += [
                "",
                "💡 Gợi ý: Dành 20–30 phút/ngày ôn môn còn yếu, theo dõi tiến bộ sau 2 tuần.",
            ]
            return "\n".join(lines)

        return json.dumps(data, ensure_ascii=False)

    def _route_with_tools(
        self, user_input: str, history: Optional[List[tuple]] = None
    ) -> Optional[str]:
        text = (user_input or "").lower()
        # Check current message first, fall back to history for student reference
        student_id = self._extract_student_id(user_input)
        if not student_id and history:
            student_id = self._detect_student_from_conversation(user_input, history)

        academic_keywords = [
            "điểm", "hoc luc", "học lực", "bảng điểm", "chuyên cần", "nhận xét",
            "muộn", "muon", "muôn", "đi trễ", "di tre",
            "vắng", "vang", "nghỉ học", "nghi hoc",
            "điểm danh", "đúng giờ", "buổi", "buoi", "ngày nghỉ",
        ]
        wellbeing_keywords = ["sinh hoạt", "thực đơn", "sức khỏe", "tâm lý", "hôm nay", "ăn gì", "an gi"]

        if student_id and any(k in text for k in academic_keywords):
            raw = self._invoke_tool("get_student_academic_records", {"student_id": student_id})
            if raw is not None:
                return self._build_tool_response(raw)

        if student_id and any(k in text for k in wellbeing_keywords):
            raw = self._invoke_tool("get_daily_activity_and_wellbeing", {"student_id": student_id})
            if raw is not None:
                return self._build_tool_response(raw)

        # Fallback: nếu tìm thấy học sinh mà không có keyword cụ thể,
        # vẫn trả về học bạ thay vì để LLM đoán
        if student_id and not any(k in text for k in wellbeing_keywords):
            raw = self._invoke_tool("get_student_academic_records", {"student_id": student_id})
            if raw is not None:
                return self._build_tool_response(raw)

        return None

    def get_system_prompt(self, student_context: str = "") -> str:
        """
        Generates the system prompt instructing the agent on the ReAct loop and formatting.
        Includes descriptions of all available tools and optional student context.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        student_section = (
            f"\nDỮ LIỆU HỌC SINH ĐANG ĐƯỢC HỎI (đã tra cứu sẵn, dùng trực tiếp không cần gọi tool):\n"
            f"{student_context}\n"
            if student_context else ""
        )
        return f"""{student_section}
Bạn là Trợ lý AI Đồng hành cùng Phụ huynh học sinh (E-School Parent Assistant). Nhiệm vụ của bạn là hỗ trợ phụ huynh theo dõi sát sao tình hình học lực, chuyên cần, thời khóa biểu của con và đưa ra các lời khuyên kèm cặp học tập thực tế từ giáo trình nhà trường (RAG).

KIỂM SOÁT PHẠM VI & NỘI DUNG NHẠY CẢM (GUARDRAILS & OFF-TOPIC CONTROLS):
- Bạn CHỈ được phép trả lời các câu hỏi liên quan trực tiếp đến học tập, điểm số, chuyên cần, thời khóa biểu và các lời khuyên kèm cặp học tập của học sinh.
- Ngoại lệ đối với lời chào hỏi và giao tiếp xã giao thông thường (như "xin chào", "chào bạn", "hello", "chào em", v.v.): Bạn ĐƯỢC PHÉP chào hỏi lại một cách thân thiện, ân cần, tự giới thiệu mình là trợ lý học tập và chủ động hỏi phụ huynh cần hỗ trợ thông tin gì về con (ở bước này bạn có thể đi thẳng tới 'Final Answer' mà không cần gọi công cụ).
- Đối với các yêu cầu hoàn toàn nằm ngoài phạm vi giáo dục (như nấu ăn, thời tiết, giải trí, thể thao, game, chính trị, công nghệ chung, v.v.) hoặc các câu hỏi có chứa từ ngữ thô tục, nhạy cảm: Bạn BẮT BUỘC phải dừng lập luận ngay tại Bước 1, TUYỆT ĐỐI không gọi bất kỳ công cụ nào và đi thẳng tới 'Final Answer' để từ chối một cách lịch sự, ân cần (ví dụ: giải thích rằng bạn là trợ lý học tập nên không thể trả lời các chủ đề khác).

QUY TẮC NHẬN XÉT & ĐÁNH GIÁ CHI TIẾT DỰA TRÊN ĐIỂM SỐ (DETAILED ASSESSMENT RULES):
Khi phụ huynh hỏi về "tình hình học tập", "kết quả học tập" hoặc "điểm số" của con, bạn KHÔNG ĐƯỢC chỉ liệt kê các con số một cách khô khan. Thay vào đó, hãy thực hiện đánh giá sâu sắc và chi tiết theo các tiêu chí sau:
1. Phân loại & So sánh Học lực: Xác định rõ môn học nào là thế mạnh của con (các môn đạt điểm xuất sắc/giỏi từ 8.0 - 10) và những môn học nào con cần chú ý cải thiện (các môn đạt điểm trung bình/khá từ 5.0 - 7.9, hoặc yếu dưới 5.0).
2. Phân tích chi tiết từng con điểm: Đánh giá ý nghĩa của từng mức điểm số cụ thể (ví dụ: điểm chuyên cần đạt tối đa thể hiện sự chăm chỉ, điểm kiểm tra định kỳ phản ánh đúng năng lực hiểu bài trên lớp, nhận xét của giáo viên đi kèm chỉ ra điểm nghẽn kiến thức nào).
3. Đề xuất Lộ trình & Lời khuyên thiết thực (RAG): Sử dụng thông tin từ tài liệu giáo trình và bài học của trường (RAG) để gợi ý lộ trình kèm cặp cụ thể (ví dụ: con cần ôn tập lại kiến thức tuần mấy, chủ đề nào, làm thêm dạng bài tập nào để củng cố).
4. Giọng văn động viên, xây dựng: Luôn giữ phong cách ân cần, đồng cảm, ghi nhận sự nỗ lực của học sinh trước khi đưa ra các giải pháp khắc phục điểm số thấp để phụ huynh không cảm thấy quá áp lực mà có động lực cùng con tiến bộ.

PHONG CÁCH PHẢN HỒI (TONE & VOICE):
- Luôn giữ thái độ lịch sự, ân cần, đồng cảm và có tính xây dựng cao (constructive).
- Tránh đưa ra điểm số hoặc thông báo lỗi chuyên cần một cách khô khan. Hãy giải thích ý nghĩa điểm số, ghi nhận sự cố gắng của học sinh và gợi ý phương án cải thiện cụ thể bằng tiếng Việt rõ ràng.

DANH SÁCH CÔNG CỤ HIỆN CÓ:
{tool_descriptions}

QUY TẮC LẬP LUẬN (ReAct Framework):
Để giải quyết yêu cầu của phụ huynh, bạn BẮT BUỘC phải tuân thủ nghiêm ngặt quy trình ReAct.
Với mỗi bước, bạn chỉ được phép đưa ra đúng một trong hai định dạng sau:

Thought: dòng suy nghĩ lập luận của bạn (bằng tiếng Anh).
Action: tên_công_cụ(các_tham_số)

HOẶC

I have gathered all necessary information from the tools and database. I am ready to formulate a comprehensive, empathetic and constructive response to the parent in Vietnamese.
 câu trả lời hoàn chỉnh, chi tiết và đầy tính xây dựng gửi tới phụ huynh (bằng tiếng Việt).

LƯU Ý QUAN TRỌNG:
1. LUÔN LUÔN bắt đầu mỗi lượt phản hồi bằng 'Thought:'.
2. Không tự ý viết dòng 'Observation:' - dòng này sẽ do hệ thống tự động cung cấp ngay sau khi thực thi công cụ.
3. Chỉ gọi DUY NHẤT một công cụ tại một thời điểm.
4. Khi gọi công cụ ở dòng 'Action', dùng đúng định dạng hàm lập trình, ví dụ: get_student_academic_records(student_id="HS001") hoặc get_learning_resources(subject="Toán", grade=4, topic="Phép nhân").
5. Nếu không cần dùng công cụ nào nữa để trả lời câu hỏi, hãy đi thẳng tới định dạng 'Final Answer'.
"""

    def _build_history_context(self, history: List[tuple]) -> str:
        """Convert (role, content) list to a readable conversation context string."""
        if not history:
            return ""
        lines = ["=== LỊCH SỬ HỘI THOẠI ==="]
        for role, content in history:
            label = "Phụ huynh" if role == "user" else "Trợ lý"
            # Truncate long bot responses to avoid token overflow
            display = content if len(content) <= 300 else content[:300] + "..."
            lines.append(f"[{label}]: {display}")
        lines.append("=== KẾT THÚC LỊCH SỬ ===")
        return "\n".join(lines) + "\n"

    def run(self, user_input: str, history: Optional[List[tuple]] = None) -> str:
        """
        Executes the ReAct loop logic.
        1. Generates Thought + Action.
        2. Parses Action and executes Tool.
        3. Appends Observation to prompt and repeats until Final Answer or max_steps.
        """
        history = history or []
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        if self._is_greeting(user_input):
            greeting_response = self._build_greeting_response()
            logger.log_event("AGENT_END", {
                "status": "greeting_shortcut",
                "steps": 0,
                "final_answer": greeting_response,
            })
            return greeting_response

        # Detect student anywhere in conversation for profile injection
        active_student_id = self._detect_student_from_conversation(user_input, history)
        student_context = self._load_student_profile(active_student_id) if active_student_id else ""

        history_context = self._build_history_context(history)
        current_prompt = f"{history_context}Câu hỏi hiện tại: {user_input}\n"
        steps = 0

        while steps < self.max_steps:
            logger.log_event("AGENT_STEP", {"step": steps + 1})
            
            # Generate LLM response
            res = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt(student_context))
            content = res["content"].strip()
            
            # Track metrics
            tracker.track_request(
                provider=res.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=res.get("usage", {}),
                latency_ms=res.get("latency_ms", 0)
            )
            
            logger.log_event("LLM_RESPONSE", {"content": content})
            
            # Print intermediate reasoning to terminal
            print(f"\n[Step {steps + 1}]")
            print(content)
            
            # Regex to match Action and Final Answer
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", content)
            final_match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL)
            
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2)

                # Execute tool
                raw_observation = self._execute_tool(tool_name, tool_args)
                print(f"\nObservation: {raw_observation}")

                # Format the raw tool result into a rich response and return immediately
                # (avoid LLM synthesis step which can drop data on small models)
                formatted = self._build_tool_response(raw_observation, question=user_input)
                logger.log_event("AGENT_END", {
                    "status": "tool_success",
                    "tool": tool_name,
                    "steps": steps + 1,
                    "final_answer": formatted,
                })
                logger.log_event("TOOL_EXECUTION", {
                    "tool": tool_name,
                    "arguments": tool_args,
                    "observation": raw_observation,
                })
                return formatted

            elif final_match:
                final_answer = final_match.group(1).strip()
                logger.log_event("AGENT_END", {"status": "success", "steps": steps + 1, "final_answer": final_answer})
                return self._clean_response(final_answer)
            else:
                logger.log_event("PARSER_ERROR", {"content": content})
                
                # Fallback parsing check
                if "Final Answer:" in content:
                    parts = content.split("Final Answer:")
                    final_answer = parts[-1].strip()
                    logger.log_event("AGENT_END", {"status": "success_fallback", "steps": steps + 1})
                    return self._clean_response(final_answer)

                # Fallback for small/local models that return only `Thought:` text.
                thought_match = re.search(r"Thought:\s*(.*)", content, re.DOTALL)
                if thought_match:
                    final_answer = thought_match.group(1).strip()
                    if final_answer:
                        logger.log_event("AGENT_END", {
                            "status": "success_thought_fallback",
                            "steps": steps + 1,
                            "final_answer": final_answer,
                        })
                        return self._clean_response(final_answer)

                # Last-resort fallback to avoid UI hanging on parser mismatch.
                cleaned_content = content.strip()
                if cleaned_content:
                    logger.log_event("AGENT_END", {
                        "status": "success_raw_fallback",
                        "steps": steps + 1,
                        "final_answer": cleaned_content,
                    })
                    return self._clean_response(cleaned_content)
                
                # Instruct agent to correct format
                correction_note = "System Note: Your output did not match 'Action: tool_name(args)' or 'Final Answer: response'. Please follow the instructions."
                current_prompt += f"\n{content}\n{correction_note}\n"
                print(f"\n[SYSTEM] {correction_note}")
                
            steps += 1
            
        logger.log_event("AGENT_TIMEOUT", {"steps": steps})
        return f"Timeout: Exceeded max steps ({self.max_steps}). Current prompt state: {current_prompt}"

    def _parse_args(self, args_str: str) -> Any:
        """
        Cleans and parses tool arguments from string format (key=value, list, or single value).
        """
        args_str = args_str.strip()
        if not args_str:
            return {}

        # 1. Check for key=value format (dictionary-like)
        if '=' in args_str:
            parsed = {}
            # Split by comma but respect quotes if any (simplified comma splitting)
            parts = re.split(r',\s*(?=(?:[^\'"]*[\'"][^\'"]*[\'"])*[^\'"]*$)', args_str)
            for part in parts:
                if '=' in part:
                    k, v = part.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    # Type conversion
                    try:
                        if '.' in v:
                            parsed[k] = float(v)
                        else:
                            parsed[k] = int(v)
                    except ValueError:
                        parsed[k] = v
            return parsed
            
        # 2. Check for comma-separated positional args (list-like)
        elif ',' in args_str:
            parts = re.split(r',\s*(?=(?:[^\'"]*[\'"][^\'"]*[\'"])*[^\'"]*$)', args_str)
            parsed_list = []
            for part in parts:
                part = part.strip().strip('"').strip("'")
                try:
                    if '.' in part:
                        parsed_list.append(float(part))
                    else:
                        parsed_list.append(int(part))
                except ValueError:
                    parsed_list.append(part)
            return parsed_list
            
        # 3. Single argument
        else:
            cleaned = args_str.strip('"').strip("'")
            try:
                if '.' in cleaned:
                    return float(cleaned)
                else:
                    return int(cleaned)
            except ValueError:
                return cleaned

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name with robust argument mapping.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    parsed_args = self._parse_args(args)
                    func = tool.get('func') or tool.get('function')
                    if not callable(func):
                        return f"Error executing tool '{tool_name}': function not callable."
                    sig = inspect.signature(func)
                    input_model = tool.get('input_model')
                    
                    if isinstance(parsed_args, dict):
                        # Filter arguments to avoid unexpected keyword errors
                        valid_args = {k: v for k, v in parsed_args.items() if k in sig.parameters}
                        if input_model is not None:
                            valid_args = input_model(**valid_args).model_dump()
                        return str(func(**valid_args))
                    elif isinstance(parsed_args, list):
                        return str(func(*parsed_args))
                    else:
                        if len(sig.parameters) == 1:
                            return str(func(parsed_args))
                        else:
                            return str(func(parsed_args))
                except Exception as e:
                    return f"Error executing tool '{tool_name}': {str(e)}"
                    
        return f"Tool '{tool_name}' not found."

