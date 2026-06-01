# src/tools/__init__.py

# 1. Import các hàm và Pydantic Model từ các file tính năng riêng lẻ
from src.tools.tools_academic import (
    get_student_academic_records,
    get_daily_activity_and_wellbeing,
    verify_parent_access,
    AcademicRecordInput,
    DailyWellbeingInput,
    SecurityVerificationInput
)
from src.tools.tools_resources import (
    get_learning_resources,
    LearningResourceInput
)

# 2. Định nghĩa danh sách AVAILABLE_TOOLS để bàn giao cho Agent
AVAILABLE_TOOLS = [
    {
        "name": "get_student_academic_records",
        "description": (
            "Tra cứu điểm số, chuyên cần, nhận xét giáo viên của học sinh. "
            "Dùng khi phụ huynh hỏi về: điểm, học lực, bảng điểm, số buổi vắng/muộn, nhận xét, tình hình học tập. "
            "Đầu vào: student_id — mã học sinh (VD: 'HS001') HOẶC tên học sinh (VD: 'Nguyễn Minh Quân')."
        ),
        "function": get_student_academic_records,
        "input_model": AcademicRecordInput
    },
    {
        "name": "get_daily_activity_and_wellbeing",
        "description": (
            "Tra cứu nhật ký sinh hoạt hôm nay: thực đơn bữa ăn, tình trạng sức khỏe, tâm lý và lời dặn của giáo viên. "
            "Dùng khi phụ huynh hỏi về: ăn gì, sức khỏe, tâm lý, sinh hoạt hôm nay. "
            "Đầu vào: student_id — mã học sinh (VD: 'HS001') HOẶC tên học sinh."
        ),
        "function": get_daily_activity_and_wellbeing,
        "input_model": DailyWellbeingInput
    },
    {
        "name": "get_learning_resources",
        "description": (
            "Tìm tài liệu, bài tập bổ trợ từ thư viện nhà trường theo môn học và khối lớp. "
            "Dùng khi phụ huynh hỏi về: tài liệu, bài tập, cách học, gợi ý ôn tập cho một môn cụ thể. "
            "Đầu vào: subject (tên môn), grade (số khối), topic (chủ đề, có thể bỏ trống)."
        ),
        "function": get_learning_resources,
        "input_model": LearningResourceInput
    },
]
