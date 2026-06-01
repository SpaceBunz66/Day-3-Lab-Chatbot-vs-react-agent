# src/tools/__init__.py

from src.tools.tools_academic import (
    get_student_academic_records,
    get_daily_activity_and_wellbeing,
    StudentIdInput
)
from src.tools.tools_resources import (
    get_learning_resources,
    ResourceInput
)

AVAILABLE_TOOLS = [
    {
        "name": "get_student_academic_records",
        "description": "Tra cứu điểm số chi tiết và nhận xét định kỳ từ giáo viên. Đầu vào: student_id (str).",
        "function": get_student_academic_records,
        "input_model": StudentIdInput
    },
    {
        "name": "get_daily_activity_and_wellbeing",
        "description": "Tra cứu nhật ký hôm nay tại trường: thực đơn ăn uống, sức khỏe, tâm lý và dặn dò của giáo viên. Đầu vào: student_id (str).",
        "function": get_daily_activity_and_wellbeing,
        "input_model": StudentIdInput
    },
    {
        "name": "get_learning_resources",
        "description": "Tìm kiếm kho bài tập bổ trợ, phương pháp học tập độc quyền phù hợp với khối lớp của học sinh. Đầu vào: student_id (str), subject (str), topic (str hoặc bỏ trống).",
        "function": get_learning_resources,
        "input_model": ResourceInput
    }
]