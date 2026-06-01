# src/tools/tools_academic.py
import json
from pydantic import BaseModel, Field
from src.tools.mock_db import STUDENT_DB, DAILY_LIFE_DB, RESOURCE_DB

class StudentIdInput(BaseModel):
    student_id: str = Field(..., description="Mã số định danh học sinh (ví dụ: 'HS001').")

def get_student_academic_records(student_id: str) -> str:
    """Tra cứu điểm số, tỉ lệ chuyên cần và nhận xét từ giáo viên chủ nhiệm."""
    student = STUDENT_DB.get(student_id)
    if not student:
        return json.dumps({"error": "Không tìm thấy dữ liệu học tập."})

    response = {
        "name": student["name"],
        "class": student["class"],
        "attendance_rate": student["attendance_rate"],
        "teacher_remark": student["teacher_remark"],
        "subjects": student["subjects"],
    }
    return json.dumps(response, ensure_ascii=False)

def get_daily_activity_and_wellbeing(student_id: str) -> str:
    """Tra cứu tình hình thực đơn, sức khỏe và tâm lý hôm nay tại trường."""
    student = STUDENT_DB.get(student_id)
    daily = DAILY_LIFE_DB.get(student_id)
    if not student or not daily:
        return json.dumps({"error": "Không tìm thấy nhật ký sinh hoạt."})

    response = {"name": student["name"], "daily_life": daily}
    return json.dumps(response, ensure_ascii=False)

def get_learning_resources(student_id: str) -> str:
    """Gợi ý tài liệu học tập phù hợp dựa trên môn học cần cải thiện của học sinh."""
    student = STUDENT_DB.get(student_id)
    if not student:
        return json.dumps({"error": "Không tìm thấy học sinh."})

    grade = student["grade"]
    suggestions = []
    for subject, info in student["subjects"].items():
        if info["status"] in ("Cần cải thiện", "Khá"):
            resources = RESOURCE_DB.get(subject, {}).get(grade, [])
            if resources:
                suggestions.append({"subject": subject, "status": info["status"], "resources": resources})

    if not suggestions:
        return json.dumps({"message": "Học sinh đang học tốt, chưa có gợi ý tài liệu bổ sung."}, ensure_ascii=False)

    response = {"name": student["name"], "suggestions": suggestions}
    return json.dumps(response, ensure_ascii=False)
