# src/tools/__init__.py

# 1. Import các hàm và Pydantic Model từ các file tính năng riêng lẻ
from src.tools.tools_academic import (
    get_student_academic_records,
    get_daily_activity_and_wellbeing,
    AcademicRecordInput,
    DailyWellbeingInput
)
from src.tools.tools_resources import (
    get_learning_resources,
    LearningResourceInput
)

# 2. Định nghĩa danh sách AVAILABLE_TOOLS để bàn giao cho Agent
AVAILABLE_TOOLS = [
    {
        "name": "get_student_academic_records",
        "description": "Tra cứu bảng điểm chi tiết, nhận xét định kỳ từ giáo viên và chuyên cần của học sinh. Đầu vào: student_id (str).",
        "function": get_student_academic_records,
        "input_model": AcademicRecordInput
    },
    {
        "name": "get_daily_activity_and_wellbeing",
        "description": "Tra cứu nhật ký sinh hoạt hôm nay tại trường: thực đơn, sức khỏe, tâm lý và lời dặn của giáo viên. Đầu vào: student_id (str).",
        "function": get_daily_activity_and_wellbeing,
        "input_model": DailyWellbeingInput
    },
    {
        "name": "get_learning_resources",
        "description": "Tìm kiếm kho bài tập bổ trợ, phương pháp học tập tư duy từ thư viện nhà trường. Đầu vào: subject (str), grade (int), topic (str hoặc bỏ trống).",
        "function": get_learning_resources,
        "input_model": LearningResourceInput
    }
]