import json
from pydantic import BaseModel, Field
from src.tools.mock_db import SECURITY_OTP_DB

class SecurityVerificationInput(BaseModel):
    student_id: str = Field(..., description="Mã số định danh của học sinh. Ví dụ: 'HS001'.")
    otp_code: str = Field(..., description="Mã OTP gồm 6 chữ số do phụ huynh cung cấp để xác thực quyền truy cập.")

def verify_parent_access(student_id: str, otp_code: str) -> str:
    """
    Xác thực quyền truy cập của phụ huynh thông qua mã OTP. 
    BẮT BUỘC phải gọi tool này và nhận kết quả 'SUCCESS' trước khi tiết lộ bất kỳ thông tin nào về điểm số hoặc nhật ký sinh hoạt của học sinh.
    """
    record = SECURITY_OTP_DB.get(student_id)
    if not record:
        return json.dumps({"status": "FAILED", "message": f"Mã học sinh {student_id} không tồn tại trên hệ thống bảo mật."})
    
    if otp_code == record["correct_otp"]:
        return json.dumps({
            "status": "SUCCESS",
            "message": f"Xác thực thành công! Phụ huynh hợp pháp của học sinh {student_id} đã được cấp quyền truy cập dữ liệu."
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "FAILED", 
            "message": "Mã OTP không chính xác. Quyền truy cập bị từ chối bới hệ thống."
        }, ensure_ascii=False)