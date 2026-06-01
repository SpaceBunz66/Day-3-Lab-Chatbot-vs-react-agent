import json
from pydantic import BaseModel, Field
from typing import Optional
from src.tools.mock_db import RESOURCE_DB

class LearningResourceInput(BaseModel):
    subject: str = Field(..., description="Tên môn học cần tìm tài liệu. Chỉ nhận các giá trị: 'Toán', 'Tiếng Việt'.")
    grade: int = Field(..., description="Khối lớp của học sinh. Ví dụ: 4 hoặc 5.")
    topic: Optional[str] = Field(None, description="Từ khóa chủ đề cụ thể (ví dụ: 'Phép nhân', 'Tập làm văn'). Có thể bỏ trống.")

def get_learning_resources(subject: str, grade: int, topic: Optional[str] = None) -> str:
    """Tìm kiếm kho bài tập bổ trợ, phương pháp học tập tư duy hoặc trò chơi tương tác từ thư viện nhà trường."""
    subject_resources = RESOURCE_DB.get(subject, {})
    grade_resources = subject_resources.get(grade, [])
    
    if not grade_resources:
        return json.dumps({"message": f"Chưa có dữ liệu trực tuyến cho môn {subject} lớp {grade}."})
    
    if topic:
        filtered = [res for res in grade_resources if topic.lower() in res["topic"].lower() or topic.lower() in res["title"].lower()]
        if filtered:
            return json.dumps(filtered, ensure_ascii=False)
            
    return json.dumps(grade_resources, ensure_ascii=False)