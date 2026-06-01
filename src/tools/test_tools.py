import json
from src.tools import AVAILABLE_TOOLS

def run_tool_tests():
    print("=== 🔍 BẮT ĐẦU KIỂM THỬ CÁC TOOLS ===")

    # Test 1: Kiểm tra lấy điểm học sinh HS001
    print("\n[Test 1] Gọi tool: get_student_academic_records")
    academic_tool = next(t for t in AVAILABLE_TOOLS if t["name"] == "get_student_academic_records")
    # Giả lập input mà LLM sẽ truyền vào
    input_data = {"student_id": "HS001"} 
    
    # Validate bằng Pydantic Model trước khi chạy
    validated_input = academic_tool["input_model"](**input_data)
    result = academic_tool["function"](**validated_input.model_dump())
    print(f"Kết quả trả về:\n{json.dumps(json.loads(result), indent=4, ensure_ascii=False)}")

    # Test 2: Kiểm tra tìm tài liệu học tập lớp 4 môn Toán
    print("\n[Test 2] Gọi tool: get_learning_resources")
    resource_tool = next(t for t in AVAILABLE_TOOLS if t["name"] == "get_learning_resources")
    input_data_2 = {"subject": "Toán", "grade": 4, "topic": "Phép nhân"}
    
    validated_input_2 = resource_tool["input_model"](**input_data_2)
    result_2 = resource_tool["function"](**validated_input_2.model_dump())
    print(f"Kết quả trả về:\n{json.dumps(json.loads(result_2), indent=4, ensure_ascii=False)}")
    
    print("\n=== ✅ HOÀN THÀNH KIỂM THỬ TOOL ===")

if __name__ == "__main__":
    run_tool_tests()