# src/tools/tools_resources.py
import json
from pydantic import BaseModel, Field
from typing import Optional
from src.tools.mock_db import STUDENT_TABLE, RESOURCE_TABLE

class ResourceInput(BaseModel):
    student_id: str = Field(..., description="Mã học sinh để hệ thống tự nhận diện khối lớp.")
    subject: str = Field(..., description="Môn học: 'Toán' hoặc 'Tiếng Việt'.")
    topic: Optional[str] = Field(None, description="Từ khóa chủ đề cụ thể.")

def get_learning_resources(student_id: str, subject: str, topic: Optional[str] = None) -> str:
    """Tìm kiếm tài liệu học tập bổ trợ phù hợp chính xác với khối lớp của học sinh."""
    student = STUDENT_TABLE.get(student_id)
    if not student:
        return json.dumps({"error": "Không tìm thấy học sinh để xác định khối lớp."})
        
    grade = student["grade"] # Tự động lấy khối lớp (Ví dụ: lớp 4)
    pool = RESOURCE_TABLE.get(subject, {}).get(grade, [])
    
    if topic and pool:
        pool = [r for r in pool if topic.lower() in r["topic"].lower() or topic.lower() in r["title"].lower()]
        
    return json.dumps({"student_name": student["name"], "grade": grade, "resources": pool}, ensure_ascii=False)