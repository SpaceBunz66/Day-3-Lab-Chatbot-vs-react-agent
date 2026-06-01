import os
import re
import inspect
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Dict, Any, Optional

AGENT_TIMEOUT_SECONDS = 180   # 3 phút
TOOL_TIMEOUT_SECONDS  = 30    # 30 giây mỗi tool call
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

        normalized = re.sub(r"[_\-]+", " ", (text or "")).lower()
        # Pass 1: full name match
        for student_id, info in STUDENT_DB.items():
            name = str(info.get("name", "")).lower()
            if name and name in normalized:
                return student_id
        # Pass 2: any single word in the text matches a name token (e.g. "Phúc", "Quân")
        words = set(re.split(r"[\s,;]+", normalized))
        for student_id, info in STUDENT_DB.items():
            name_tokens = set(re.split(r"[\s]+", str(info.get("name", "")).lower()))
            if words & name_tokens:  # non-empty intersection
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
        """Detect student — current message takes priority over history."""
        # Always check current input first
        student_id = self._extract_student_id(current_input)
        if student_id:
            return student_id
        # Fall back to history only if current message has no student reference
        for _, content in reversed(history):  # most recent first
            student_id = self._extract_student_id(content)
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
            logger.log_event("TOOL_CALL", {"tool": tool_name, "args": kwargs})
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, **kwargs)
                try:
                    result = str(future.result(timeout=TOOL_TIMEOUT_SECONDS))
                    logger.log_event("TOOL_RESULT", {"tool": tool_name, "result_preview": result[:300]})
                    return result
                except FuturesTimeoutError:
                    logger.log_event("TOOL_TIMEOUT", {"tool": tool_name, "timeout": TOOL_TIMEOUT_SECONDS})
                    return json.dumps({"error": f"tool_timeout:{tool_name}"}, ensure_ascii=False)
        except Exception as exc:
            logger.log_event("TOOL_ERROR", {"tool": tool_name, "error": str(exc)})
            return json.dumps({"error": f"tool_error:{tool_name}:{exc}"}, ensure_ascii=False)

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
    _ROADMAP_KW = {
        "lộ trình", "lo trinh", "kế hoạch", "ke hoach", "hướng dẫn",
        "cải thiện", "cai thien", "nâng điểm", "nang diem", "học thế nào",
        "kèm cặp", "kem cap", "hỗ trợ học", "phương pháp", "phuong phap",
        "tài liệu", "tai lieu", "bài tập", "bai tap", "ôn tập", "on tap",
    }

    def _detect_intent(self, question: str) -> str:
        """Return 'attendance', 'scores', 'roadmap', or 'full' based on question keywords."""
        q = (question or "").lower()
        # Check roadmap first (most specific)
        if any(kw in q for kw in self._ROADMAP_KW):
            return "roadmap"
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
            err = str(data["error"])
            if err.startswith("tool_timeout:"):
                tool = err.split(":", 2)[1] if ":" in err else "công cụ"
                return (
                    f"⏱️ Yêu cầu mất quá nhiều thời gian để xử lý (>{TOOL_TIMEOUT_SECONDS}s).\n"
                    f"Vui lòng thử lại sau hoặc liên hệ nhà trường để được hỗ trợ."
                )
            if err.startswith("tool_error:"):
                return (
                    "⚠️ Hệ thống gặp lỗi khi tra cứu dữ liệu.\n"
                    "Vui lòng thử lại sau hoặc kiểm tra lại thông tin học sinh."
                )
            return err

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

            if intent == "roadmap":
                return self._build_roadmap(header, name, grade, subjects, remark)

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

    def _build_roadmap(self, header: str, name: str, grade, subjects: dict, remark: str) -> str:
        """Build a detailed weekly learning roadmap: fetches scores, calls get_learning_resources
        for each weak subject via tool, then synthesises a structured study plan."""
        grade_int = grade if isinstance(grade, int) else int(str(grade))

        # --- Step 1: Classify subjects from the fetched academic records ---
        excellent_s, good_s, weak_s, declining_s = [], [], [], []
        for subj, sc in subjects.items():
            mid = sc.get("midterm", 0)
            fin = sc.get("final", 0)
            avg = (mid + fin) / 2
            status = sc.get("status", "")
            if status == "Xuất sắc" or avg >= 8.5:
                excellent_s.append((subj, sc))
            elif status in ("Tốt", "Khá") or avg >= 6.5:
                good_s.append((subj, sc))
            else:
                weak_s.append((subj, sc))
            if isinstance(mid, (int, float)) and isinstance(fin, (int, float)) and fin < mid:
                declining_s.append(subj)

        # --- Step 2: Fetch learning resources via tool for each subject that needs attention ---
        resources_map: dict = {}
        subjects_needing_resources = [s for s, _ in weak_s] + [s for s, _ in good_s if s in declining_s]
        for subj in subjects_needing_resources:
            raw_res = self._invoke_tool("get_learning_resources", {"subject": subj, "grade": grade_int})
            if raw_res:
                try:
                    parsed = json.loads(raw_res)
                    if isinstance(parsed, list):
                        resources_map[subj] = parsed
                except Exception:
                    pass

        # --- Step 3: Build analysis section ---
        lines = [header, "", "📊 PHÂN TÍCH TOÀN BỘ ĐIỂM SỐ:"]

        for subj, sc in subjects.items():
            mid = sc.get("midterm", "?")
            fin = sc.get("final", "?")
            status = sc.get("status", "")
            trend = ""
            if isinstance(mid, (int, float)) and isinstance(fin, (int, float)):
                trend = " 📈 (cải thiện)" if fin > mid else (" 📉 (giảm sút — cần chú ý!)" if fin < mid else " ➡️ (giữ nguyên)")
            emoji = "🌟" if status == "Xuất sắc" else ("✅" if status in ("Tốt", "Khá") else "⚠️")
            lines.append(f"  {emoji} {subj}: GK {mid} → CK {fin}{trend}  [{status}]")

        # --- Step 4: Teacher remark analysis ---
        if remark:
            lines += ["", "💬 NHẬN XÉT GIÁO VIÊN:", f'  "{remark}"']
            remark_lower = remark.lower()
            if "bảng cửu chương" in remark_lower:
                lines.append("  ➡️  Điểm nghẽn: học thuộc bảng cửu chương — ưu tiên cao nhất.")
            if "mất tập trung" in remark_lower or "tập trung" in remark_lower:
                lines.append("  ➡️  Gợi ý: học vào buổi sáng sớm, mỗi lần 25 phút (kỹ thuật Pomodoro).")
            if "viết văn" in remark_lower or "sáng tạo" in remark_lower:
                lines.append("  ➡️  Điểm mạnh: kỹ năng viết văn — phát huy bằng cách luyện đề mở rộng.")
            if "tự tin" in remark_lower or "phát biểu" in remark_lower:
                lines.append("  ➡️  Gợi ý: khuyến khích con phát biểu mỗi ngày ít nhất 1 lần ở lớp.")
            if "muộn" in remark_lower or "vắng" in remark_lower:
                lines.append("  ➡️  Lưu ý: chuyên cần ảnh hưởng trực tiếp đến học lực — cần đảm bảo đi học đúng giờ.")

        # --- Step 5: Weekly roadmap using fetched resources ---
        lines += ["", "🗓️ LỘ TRÌNH KÈM CẶP ĐỀ XUẤT (THEO TUẦN):"]

        week = 1
        for subj, sc in weak_s:
            fin = sc.get("final", 0)
            note = "Ôn kiến thức nền tảng (điểm dưới 5)" if fin < 5 else "Ôn lại các dạng bài hay sai, luyện thêm bài tập"
            lines.append(f"  📌 Tuần {week}–{week + 1}: [{subj}] {note}")
            for res in resources_map.get(subj, [])[:2]:
                lines.append(f"    📚 {res['title']} ({res['type']})")
            if not resources_map.get(subj):
                lines.append(f"    📚 Liên hệ nhà trường để nhận tài liệu bổ trợ môn {subj} khối {grade_int}.")
            week += 2

        for subj, sc in good_s:
            if subj in declining_s:
                lines.append(f"  📌 Tuần {week}: [{subj}] Điểm giảm nhẹ — ôn lại bài tuần gần nhất để củng cố.")
                for res in resources_map.get(subj, [])[:1]:
                    lines.append(f"    📚 {res['title']} ({res['type']})")
                week += 1

        if excellent_s:
            names = ", ".join(s for s, _ in excellent_s)
            lines.append(f"  ⭐ Duy trì: {names} — luyện thêm đề nâng cao để giữ vững kết quả.")

        # --- Step 6: Daily habits ---
        lines += [
            "",
            "💡 THÓI QUEN HỌC TẬP HÀNG NGÀY:",
            "  • 25 phút/ngày ôn môn yếu (buổi tối sau bữa ăn, không dùng điện thoại).",
            "  • Đọc lại bài ghi chép hôm trước trước khi đi ngủ (5 phút).",
            "  • Cuối tuần làm 1 bài kiểm tra ngắn để đo tiến bộ.",
            "  • Khen ngợi khi con đạt mục tiêu nhỏ để duy trì động lực.",
        ]
        return "\n".join(lines)

    def _route_with_tools(
        self, user_input: str, history: Optional[List[tuple]] = None
    ) -> Optional[str]:
        text = (user_input or "").lower()
        # Check current message first, fall back to history for student reference
        student_id = self._extract_student_id(user_input)
        if not student_id and history:
            student_id = self._detect_student_from_conversation(user_input, history)

        logger.log_event("STUDENT_DETECT", {
            "student_id": student_id or "(none)",
            "from": "current_input" if self._extract_student_id(user_input) else "history",
        })

        academic_keywords = [
            "điểm", "hoc luc", "học lực", "bảng điểm", "chuyên cần", "nhận xét",
            "muộn", "muon", "muôn", "đi trễ", "di tre",
            "vắng", "vang", "nghỉ học", "nghi hoc",
            "điểm danh", "đúng giờ", "buổi", "buoi", "ngày nghỉ",
        ]
        wellbeing_keywords = ["sinh hoạt", "thực đơn", "sức khỏe", "tâm lý", "hôm nay", "ăn gì", "an gi"]

        if student_id and any(k in text for k in academic_keywords):
            logger.log_event("ROUTE_DECISION", {"route": "get_student_academic_records", "reason": "academic keyword match"})
            raw = self._invoke_tool("get_student_academic_records", {"student_id": student_id})
            if raw is not None:
                intent = self._detect_intent(user_input)
                logger.log_event("INTENT_DETECT", {"intent": intent, "question": user_input})
                result = self._build_tool_response(raw, question=user_input)
                logger.log_event("FINAL_ANSWER", {"intent": intent, "preview": result[:200]})
                return result

        if student_id and any(k in text for k in wellbeing_keywords):
            logger.log_event("ROUTE_DECISION", {"route": "get_daily_activity_and_wellbeing", "reason": "wellbeing keyword match"})
            raw = self._invoke_tool("get_daily_activity_and_wellbeing", {"student_id": student_id})
            if raw is not None:
                result = self._build_tool_response(raw, question=user_input)
                logger.log_event("FINAL_ANSWER", {"intent": "wellbeing", "preview": result[:200]})
                return result

        # Fallback: nếu tìm thấy học sinh mà không có keyword cụ thể,
        # vẫn trả về học bạ thay vì để LLM đoán
        if student_id and not any(k in text for k in wellbeing_keywords):
            logger.log_event("ROUTE_DECISION", {"route": "get_student_academic_records", "reason": "student found, fallback to academic"})
            raw = self._invoke_tool("get_student_academic_records", {"student_id": student_id})
            if raw is not None:
                intent = self._detect_intent(user_input)
                logger.log_event("INTENT_DETECT", {"intent": intent, "question": user_input})
                result = self._build_tool_response(raw, question=user_input)
                logger.log_event("FINAL_ANSWER", {"intent": intent, "preview": result[:200]})
                return result

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
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name, "history_turns": len(history or [])})
        _start_time = time.time()

        def _timed_out() -> bool:
            return (time.time() - _start_time) >= AGENT_TIMEOUT_SECONDS

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
            if _timed_out():
                logger.log_event("AGENT_TIMEOUT", {"steps": steps, "elapsed_s": AGENT_TIMEOUT_SECONDS})
                return (
                    f"⏱️ Yêu cầu của bạn mất quá {AGENT_TIMEOUT_SECONDS // 60} phút để xử lý.\n"
                    "Vui lòng thử lại sau hoặc đặt câu hỏi ngắn gọn hơn."
                )
            print(f"\n{'='*60}")
            print(f"[ReAct] Step {steps + 1}")
            print(f"{'='*60}")

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

            # --- Extract and log Thought / Action / Final Answer separately ---
            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|\Z)", content, re.DOTALL)
            action_match  = re.search(r"Action:\s*(\w+)\((.*?)\)", content, re.DOTALL)
            final_match   = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL)

            thought_text = thought_match.group(1).strip() if thought_match else ""
            if thought_text:
                print(f"[THOUGHT] {thought_text}")
                logger.log_event("REACT_THOUGHT", {"step": steps + 1, "thought": thought_text})

            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2)

                print(f"[ACTION]  {tool_name}({tool_args})")
                logger.log_event("REACT_ACTION", {"step": steps + 1, "tool": tool_name, "args": tool_args})

                raw_observation = self._execute_tool(tool_name, tool_args)

                print(f"[OBSERVATION] {raw_observation[:300]}{'...' if len(raw_observation) > 300 else ''}")
                logger.log_event("REACT_OBSERVATION", {"step": steps + 1, "tool": tool_name, "observation_preview": raw_observation[:300]})

                formatted = self._build_tool_response(raw_observation, question=user_input)
                print(f"[FINAL ANSWER] (formatted from tool result)")
                logger.log_event("REACT_FINAL_ANSWER", {"step": steps + 1, "source": "tool", "tool": tool_name, "preview": formatted[:200]})
                return formatted

            elif final_match:
                final_answer = final_match.group(1).strip()
                print(f"[FINAL ANSWER] {final_answer[:200]}{'...' if len(final_answer) > 200 else ''}")
                logger.log_event("REACT_FINAL_ANSWER", {"step": steps + 1, "source": "llm", "preview": final_answer[:200]})
                return self._clean_response(final_answer)
            else:
                print(f"[PARSE FAIL] Could not extract Action or Final Answer from LLM output.")
                print(f"[RAW OUTPUT] {content[:300]}")
                logger.log_event("REACT_PARSE_FAIL", {"step": steps + 1, "raw_preview": content[:300]})

                # Fallback parsing check
                if "Final Answer:" in content:
                    parts = content.split("Final Answer:")
                    final_answer = parts[-1].strip()
                    print(f"[FINAL ANSWER] (fallback split) {final_answer[:200]}")
                    logger.log_event("REACT_FINAL_ANSWER", {"step": steps + 1, "source": "fallback_split", "preview": final_answer[:200]})
                    return self._clean_response(final_answer)

                # Fallback for small/local models that return only `Thought:` text.
                if thought_text:
                    print(f"[FINAL ANSWER] (fallback thought) {thought_text[:200]}")
                    logger.log_event("REACT_FINAL_ANSWER", {"step": steps + 1, "source": "fallback_thought", "preview": thought_text[:200]})
                    return self._clean_response(thought_text)

                # Last-resort fallback to avoid UI hanging on parser mismatch.
                cleaned_content = content.strip()
                if cleaned_content:
                    print(f"[FINAL ANSWER] (fallback raw) {cleaned_content[:200]}")
                    logger.log_event("REACT_FINAL_ANSWER", {"step": steps + 1, "source": "fallback_raw", "preview": cleaned_content[:200]})
                    return self._clean_response(cleaned_content)

                # Instruct agent to correct format
                correction_note = "System Note: Your output did not match 'Action: tool_name(args)' or 'Final Answer: response'. Please follow the instructions."
                current_prompt += f"\n{content}\n{correction_note}\n"
                print(f"[SYSTEM] {correction_note}")
                
            steps += 1
            
        logger.log_event("AGENT_TIMEOUT", {"steps": steps})
        return (
            f"⏱️ Yêu cầu của bạn mất quá {AGENT_TIMEOUT_SECONDS // 60} phút để xử lý.\n"
            "Vui lòng thử lại sau hoặc đặt câu hỏi ngắn gọn hơn."
        )

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
        Wraps execution in a timeout to prevent hanging.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    parsed_args = self._parse_args(args)
                    func = tool.get('func') or tool.get('function')
                    if not callable(func):
                        return json.dumps({"error": f"tool_error:{tool_name}:function not callable"}, ensure_ascii=False)
                    sig = inspect.signature(func)
                    input_model = tool.get('input_model')

                    def _call():
                        if isinstance(parsed_args, dict):
                            valid_args = {k: v for k, v in parsed_args.items() if k in sig.parameters}
                            if input_model is not None:
                                valid_args = input_model(**valid_args).model_dump()
                            return str(func(**valid_args))
                        elif isinstance(parsed_args, list):
                            return str(func(*parsed_args))
                        else:
                            return str(func(parsed_args))

                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(_call)
                        try:
                            return future.result(timeout=TOOL_TIMEOUT_SECONDS)
                        except FuturesTimeoutError:
                            logger.log_event("TOOL_TIMEOUT", {"tool": tool_name, "timeout": TOOL_TIMEOUT_SECONDS})
                            return json.dumps({"error": f"tool_timeout:{tool_name}"}, ensure_ascii=False)
                except Exception as e:
                    logger.log_event("TOOL_ERROR", {"tool": tool_name, "error": str(e)})
                    return json.dumps({"error": f"tool_error:{tool_name}:{e}"}, ensure_ascii=False)

        return json.dumps({"error": f"tool_error:{tool_name}:not found"}, ensure_ascii=False)

