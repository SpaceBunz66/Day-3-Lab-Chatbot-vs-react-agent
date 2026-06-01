# src/tools/tools_academic.py

import json
from pydantic import BaseModel, Field
from src.tools.mock_db import STUDENT_DB, DAILY_LIFE_DB

class AcademicRecordInput(BaseModel):
    student_id: str = Field(..., description="Mã số định danh duy nhất của học sinh. Ví dụ: 'HS001', 'HS002'.")

def get_student_academic_records(student_id: str) -> str:
    """Tra cứu bảng điểm chi tiết, nhận xét định kỳ từ giáo viên và chuyên cần của học sinh."""
    student = STUDENT_DB.get(student_id)
    if not student:
        return json.dumps({"error": f"Không tìm thấy học sinh với mã {student_id}."})
    return json.dumps(student, ensure_ascii=False)


class DailyWellbeingInput(BaseModel):
    student_id: str = Field(..., description="Mã số định danh duy nhất của học sinh. Ví dụ: 'HS001', 'HS002'.")

def get_daily_activity_and_wellbeing(student_id: str) -> str:
    """Tra cứu nhật ký sinh hoạt hôm nay tại trường: thực đơn, sức khỏe, tâm lý và lời dặn của giáo viên."""
    daily_data = DAILY_LIFE_DB.get(student_id)
    if not daily_data:
        return json.dumps({"error": f"Không có nhật ký sinh hoạt hôm nay cho học sinh {student_id}."})
    return json.dumps(daily_data, ensure_ascii=False)