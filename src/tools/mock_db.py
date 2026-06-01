# src/tools/mock_db.py

# Bảng 1: Thông tin học sinh cơ bản (Bảng Student)
STUDENT_TABLE = {
    "HS001": {"name": "Nguyễn Minh Quân", "grade": 4, "class": "4A1", "attendance_rate": "95%"},
    "HS002": {"name": "Trần Tuệ Lâm", "grade": 5, "class": "5B", "attendance_rate": "100%"}
}

# Bảng 2: Kết quả học tập (Bảng AcademicRecords)
ACADEMIC_TABLE = {
    "HS001": {
        "teacher_remark": "Quân thông minh, năng nổ nhưng dạo gần đây hay mất tập trung trong giờ Toán, chưa thuộc bảng cửu chương 7, 8, 9.",
        "subjects": {
            "Toán": {"midterm": 6.0, "final": 5.5, "status": "Cần cải thiện"},
            "Tiếng Việt": {"midterm": 8.5, "final": 8.0, "status": "Tốt"}
        }
    },
    "HS002": {
        "teacher_remark": "Tuệ Lâm học đều các môn, kỹ năng viết văn sáng tạo tốt. Cần phát huy thêm sự tự tin khi phát biểu.",
        "subjects": {
            "Toán": {"midterm": 9.0, "final": 9.5, "status": "Xuất sắc"},
            "Tiếng Việt": {"midterm": 7.0, "final": 8.5, "status": "Khá"}
        }
    }
}

# Bảng 3: Nhật ký sinh hoạt, sức khỏe hằng ngày (Bảng DailyWellbeing)
DAILY_LIFE_TABLE = {
    "HS001": {
        "date": "2026-06-01",
        "meals": {"breakfast": "Bánh mì sốt vang", "lunch": "Cơm cá, thịt kho trứng, canh cải", "snack": "Sữa chua"},
        "health_status": "Bình thường, ngủ trưa đủ giấc.",
        "psychology_status": "Có chút uể oải vào đầu giờ chiều. Trong giờ ra chơi có tranh giành bóng với bạn nhưng đã được cô giáo giải quyết.",
        "teacher_note": "Nhờ phụ huynh tối nay nhắc con chuẩn bị sẵn compa và thước kẻ cho tiết Hình học ngày mai."
    },
    "HS002": {
        "date": "2026-06-01",
        "meals": {"breakfast": "Phở gà", "lunch": "Cơm, cá sốt cà chua, canh bí đao", "snack": "Trái cây mùa hè"},
        "health_status": "Hơi húng hắng ho nhẹ vào cuối buổi chiều, đã được cô giáo cho uống nước ấm.",
        "psychology_status": "Vui vẻ, tích cực xung phong phát biểu bài môn Tiếng Việt.",
        "teacher_note": "Phụ huynh theo dõi thêm tình trạng ho của con tối nay ở nhà."
    }
}

# Bảng 4: Kho tài liệu dùng chung toàn trường, chia theo Khối và Môn (Bảng LearningResources)
RESOURCE_TABLE = {
    "Toán": {
        4: [{"topic": "Phép nhân", "title": "Mẹo học thuộc nhanh bảng cửu chương 7, 8, 9 qua bài hát", "type": "Video"}],
        5: [{"topic": "Số thập phân", "title": "Trò chơi luyện tập tính toán Số thập phân", "type": "Interactive"}]
    },
    "Tiếng Việt": {
        4: [{"topic": "Tập làm văn", "title": "50 bài văn mẫu tả cảnh và sơ đồ tư duy dàn ý lớp 4", "type": "Ebook"}],
        5: [{"topic": "Tập làm văn", "title": "Phương pháp mở bài gián tiếp lớp 5", "type": "PDF"}]
    }
}