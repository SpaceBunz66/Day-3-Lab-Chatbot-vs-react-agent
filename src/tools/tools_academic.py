# src/tools/tools_academic.py
import json
from pydantic import BaseModel, Field
from src.tools.mock_db import STUDENT_TABLE, ACADEMIC_TABLE, DAILY_LIFE_TABLE

class StudentIdInput(BaseModel):
    student_id: str = Field(..., description="Mã số định danh học sinh (ví dụ: 'HS001').")

def get_student_academic_records(student_id: str) -> str:
    """Tra cứu điểm số và nhận xét từ giáo viên chủ nhiệm."""
    student = STUDENT_TABLE.get(student_id)
    records = ACADEMIC_TABLE.get(student_id)
    if not student or not records:
        return json.dumps({"error": "Không tìm thấy dữ liệu học tập."})
    
    # Thực tế: Gộp thông tin từ bảng Student và bảng Academic
    response = {"name": student["name"], "class": student["class"], "records": records}
    return json.dumps(response, ensure_ascii=False)

def get_daily_activity_and_wellbeing(student_id: str) -> str:
    """Tra cứu tình hình thực đơn, sức khỏe và tâm lý hôm nay tại trường."""
    student = STUDENT_TABLE.get(student_id)
    daily = DAILY_LIFE_TABLE.get(student_id)
    if not student or not daily:
        return json.dumps({"error": "Không tìm thấy nhật ký sinh hoạt."})
        
    response = {"name": student["name"], "daily_life": daily}
    return json.dumps(response, ensure_ascii=False)