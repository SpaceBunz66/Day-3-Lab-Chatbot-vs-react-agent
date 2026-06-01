# src/tools/tools_academic.py

import json
import re
from pydantic import BaseModel, Field
from src.tools.mock_db import STUDENT_DB, DAILY_LIFE_DB


def _resolve_student_id(identifier: str) -> str | None:
    """Resolve student_id from either an ID (HS001) or a full/partial name."""
    if not identifier:
        return None
    # Direct ID match
    key = identifier.strip().upper()
    if re.match(r"^HS\d+$", key) and key in STUDENT_DB:
        return key
    # Normalize: replace underscores/hyphens with spaces, strip extra whitespace
    normalized = re.sub(r"[_\-]+", " ", identifier).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    for sid, info in STUDENT_DB.items():
        name = re.sub(r"\s+", " ", str(info.get("name", "")).lower())
        if normalized in name or name in normalized:
            return sid
    return None


class AcademicRecordInput(BaseModel):
    student_id: str = Field(..., description="Mã học sinh (HS001) hoặc tên học sinh (ví dụ: 'Nguyễn Minh Quân').")


def get_student_academic_records(student_id: str) -> str:
    """Tra cứu bảng điểm chi tiết, nhận xét định kỳ từ giáo viên và chuyên cần của học sinh."""
    resolved = _resolve_student_id(student_id)
    if not resolved:
        return json.dumps({"error": f"Không tìm thấy học sinh '{student_id}' trong hệ thống."}, ensure_ascii=False)
    return json.dumps(STUDENT_DB[resolved], ensure_ascii=False)


class DailyWellbeingInput(BaseModel):
    student_id: str = Field(..., description="Mã học sinh (HS001) hoặc tên học sinh (ví dụ: 'Trần Tuệ Lâm').")


def get_daily_activity_and_wellbeing(student_id: str) -> str:
    """Tra cứu nhật ký sinh hoạt hôm nay tại trường: thực đơn, sức khỏe, tâm lý và lời dặn của giáo viên."""
    resolved = _resolve_student_id(student_id)
    if not resolved:
        return json.dumps({"error": f"Không tìm thấy học sinh '{student_id}' trong hệ thống."}, ensure_ascii=False)
    daily_data = DAILY_LIFE_DB.get(resolved)
    if not daily_data:
        return json.dumps(
            {"error": f"Không có nhật ký sinh hoạt hôm nay cho học sinh {resolved}."},
            ensure_ascii=False,
        )
    return json.dumps(daily_data, ensure_ascii=False)


class SecurityVerificationInput(BaseModel):
    student_id: str = Field(..., description="Mã học sinh (HS001) hoặc tên học sinh.")
    otp_code: str = Field(..., description="Mã OTP 6 chữ số do phụ huynh nhập.")


def verify_parent_access(student_id: str, otp_code: str) -> str:
    """Xác thực mã OTP của phụ huynh trước khi truy xuất dữ liệu nhạy cảm."""
    resolved = _resolve_student_id(student_id)
    if not resolved:
        return json.dumps({"verified": False, "error": f"Không tìm thấy học sinh '{student_id}'."}, ensure_ascii=False)
    # Demo: mọi OTP 6 chữ số đều hợp lệ (thay bằng logic thật khi production)
    if len(otp_code) == 6 and otp_code.isdigit():
        return json.dumps({"verified": True, "student_id": resolved}, ensure_ascii=False)
    return json.dumps({"verified": False, "error": "Mã OTP không hợp lệ."}, ensure_ascii=False)
