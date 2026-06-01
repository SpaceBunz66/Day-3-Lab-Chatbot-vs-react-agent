# src/tools/mock_db.py

STUDENT_DB = {
    "HS001": {
        "name": "Nguyễn Minh Quân",
        "grade": 4,
        "class": "4A1",
        "attendance_rate": "95%",
        "total_sessions": 100,
        "absent_days": 3,
        "late_days": 2,
        "teacher_remark": "Quân thông minh, năng nổ nhưng dạo gần đây hay mất tập trung trong giờ Toán, chưa thuộc bảng cửu chương 7, 8, 9.",
        "subjects": {
            "Toán": {"midterm": 6.0, "final": 5.5, "status": "Cần cải thiện"},
            "Tiếng Việt": {"midterm": 8.5, "final": 8.0, "status": "Tốt"},
            "Tiếng Anh": {"midterm": 9.0, "final": 8.7, "status": "Tốt"}
        }
    },
    "HS002": {
        "name": "Trần Tuệ Lâm",
        "grade": 5,
        "class": "5B",
        "attendance_rate": "100%",
        "total_sessions": 100,
        "absent_days": 0,
        "late_days": 0,
        "teacher_remark": "Tuệ Lâm học đều các môn, kỹ năng viết văn sáng tạo tốt. Cần phát huy thêm sự tự tin khi phát biểu.",
        "subjects": {
            "Toán": {"midterm": 9.0, "final": 9.5, "status": "Xuất sắc"},
            "Tiếng Việt": {"midterm": 7.0, "final": 8.5, "status": "Khá"},
            "Tiếng Anh": {"midterm": 8.0, "final": 8.0, "status": "Khá"}
        }
    },
    "HS003": {
        "name": "Lê Hoàng Phúc",
        "grade": 4,
        "class": "4A1",
        "attendance_rate": "72%",
        "total_sessions": 100,
        "absent_days": 18,
        "late_days": 10,
        "teacher_remark": "Phúc hay đi học muộn và vắng nhiều buổi, cần phụ huynh phối hợp nhắc nhở con đi học đúng giờ và đều đặn hơn.",
        "subjects": {
            "Toán": {"midterm": 6.0, "final": 5.5, "status": "Cần cải thiện"},
            "Tiếng Việt": {"midterm": 2.5, "final": 3.0, "status": "Kém"},
            "Tiếng Anh": {"midterm": 5.0, "final": 5.5, "status": "Cần cải thiện"}
        }
    },
}

DAILY_LIFE_DB = {
    "HS001": {
        "date": "2026-06-01",
        "meals": {"breakfast": "Bánh mì sốt vang", "lunch": "Cơm cá, thịt kho trứng, canh cải", "snack": "Sữa chua"},
        "health_status": "Bình thường, ngủ trưa đủ giấc.",
        "psychology_status": "Có chút uể oải vào đầu giờ chiều. Trong giờ ra chơi có tranh giành bóng với bạn nhưng đã được cô giáo giải quyết, cuối giờ hai bạn đã làm hòa.",
        "teacher_note": "Nhờ phụ huynh tối nay nhắc con chuẩn bị sẵn compa và thước kẻ cho tiết Hình học ngày mai."
    },
    "HS002": {
        "date": "2026-06-01",
        "meals": {"breakfast": "Phở gà", "lunch": "Cơm, cá sốt cà chua, canh bí đao", "snack": "Trái cây mùa hè"},
        "health_status": "Hơi húng hắng ho nhẹ vào cuối buổi chiều, đã được cô giáo cho uống nước ấm.",
        "psychology_status": "Vui vẻ, tích cực xung phong phát biểu bài môn Tiếng Việt.",
        "teacher_note": "Phụ huynh theo dõi thêm tình trạng ho của con tối nay ở nhà, nếu cần thiết hãy gửi thuốc cho cô vào sáng mai."
    }
}

RESOURCE_DB = {
    "Toán": {
        4: [
            {"topic": "Phép nhân và phép chia", "title": "Mẹo học thuộc nhanh bảng cửu chương 7, 8, 9 qua bài hát", "type": "Video & Bài tập"},
            {"topic": "Phân số", "title": "Bộ bài tập trực quan về Phân số kèm lời giải chi tiết lớp 4", "type": "PDF"}
        ],
        5: [
            {"topic": "Số thập phân", "title": "Trò chơi luyện tập tính toán Số thập phân", "type": "Interactive Link"}
        ]
    },
    "Tiếng Việt": {
        4: [
            {"topic": "Tập làm văn", "title": "50 bài văn mẫu tả cảnh và sơ đồ tư duy dàn ý lớp 4", "type": "Ebook"}
        ],
        5: [
            {"topic": "Tập làm văn", "title": "Phương pháp mở bài gián tiếp và kết bài mở rộng cho văn nghị luận tiểu học", "type": "Tài liệu hướng dẫn"}
        ]
    }
}

SECURITY_OTP_DB = {
    "HS001": {
        "correct_otp": "123456",       
        "parent_phone": "0912xxx345"
    },
    "HS002": {
        "correct_otp": "654321",
        "parent_phone": "0987xxx999"
    }
}