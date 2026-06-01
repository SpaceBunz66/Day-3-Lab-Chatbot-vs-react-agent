
import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    Hệ thống ReAct Agent hoàn chỉnh phục vụ Trợ lý Phụ huynh.
    Tự động thực hiện chu trình: Tư duy (Thought) -> Hành động (Action) -> Quan sát (Observation).
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools  # Nhận cấu trúc AVAILABLE_TOOLS từ src/tools/__init__.py
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Xây dựng System Prompt định hình tư duy ReAct bằng tiếng Việt cho LLM.
        Cung cấp danh sách công cụ và cấu trúc ép buộc đầu ra.
        """
        # Trích xuất danh sách tool và mô tả của chúng để nạp vào prompt
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        
        return f"""Bạn là một Trợ lý AI thông minh chuyên hỗ trợ Phụ huynh học sinh. 
                Bạn có quyền truy cập vào các công cụ (tools) sau để tra cứu dữ liệu:
                {tool_descriptions}

                Quy trình làm việc của bạn BẮT BUỘC phải tuân theo định dạng sau một cách nghiêm ngặt:

                Thought: Phân tích câu hỏi của phụ huynh và xác định bước đi tiếp theo (Cần thông tin gì? Gọi tool nào?).
                Action: Tên_Tool(Tham_Số_Dạng_JSON)
                Observation: Kết quả trả về từ công cụ (Bạn sẽ nhận được cái này sau khi Action kích hoạt).

                ... (Bạn có thể lặp lại chu trình Thought -> Action -> Observation nếu cần thu thập thêm dữ liệu từ các tool khác).

                Khi đã có đầy đủ thông tin để trả lời trọn vẹn cho phụ huynh, hãy kết thúc bằng định dạng:
                Final Answer: Câu trả lời tổng hợp cuối cùng bằng tiếng Việt, mạch lạc, nhẹ nhàng và mang tính hỗ trợ cao đối với phụ huynh.

                LƯU Ý QUAN TRỌNG: 
                1. Sau mỗi từ khóa 'Action:', bạn CHỈ ĐƯỢC PHÉP xuất ra tên hàm kèm JSON thô của tham số, ví dụ: get_student_academic_records({{"student_id": "HS001"}})
                2. KHÔNG bọc JSON trong ký tự markdown như ```json ... ``` để tránh lỗi phân tách.
                """

    def run(self, user_input: str) -> str:
        """
        Vòng lặp ReAct cốt lõi (The Agentic Loop).
        Kiểm soát số bước, gọi LLM, bóc tách Action, chạy Tool và trả về Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        # Khởi tạo ngữ cảnh hội thoại ban đầu bao gồm cả prompt hệ thống
        system_prompt = self.get_system_prompt()
        current_context = f"Yêu cầu từ Phụ huynh: {user_input}\n"
        
        steps = 0
        while steps < self.max_steps:
            steps += 1
            logger.log_event("AGENT_STEP_START", {"step": steps})
            
            # 1. Gọi LLM sinh ra chuỗi Thought + Action (hoặc Final Answer)
            llm_result = self.llm.generate(current_context, system_prompt=system_prompt)
            llm_output = llm_result["content"]
            logger.log_event("LLM_METRIC", {
                "step": steps,
                "prompt_tokens": llm_result["usage"]["prompt_tokens"],
                "completion_tokens": llm_result["usage"]["completion_tokens"],
                "total_tokens": llm_result["usage"]["total_tokens"],
                "latency_ms": llm_result["latency_ms"]
            })

            # Cập nhật phản hồi của LLM vào nhật ký chuỗi suy luận
            current_context += f"\n{llm_output}"
            
            # Kiểm tra xem LLM đã tìm ra câu trả lời cuối cùng chưa
            if "Final Answer:" in llm_output:
                final_answer = llm_output.split("Final Answer:")[-1].strip()
                logger.log_event("AGENT_END", {"steps": steps, "status": "SUCCESS"})
                return final_answer
                
            # 2. Phân tách (Parse) hàm Action từ LLM bằng Regex chuyên dụng
            # Khớp mẫu dạng: Action: tên_hàm({json})
            action_match = re.search(r"Action:\s*(\w+)\((\{.*?\})\)", llm_output, re.DOTALL)
            
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_args_str = action_match.group(2).strip()
                
                logger.log_event("TOOL_CALL_DETECTED", {"tool": tool_name, "args": tool_args_str})
                
                # 3. Kích hoạt thực thi công cụ
                observation_result = self._execute_tool(tool_name, tool_args_str)
                
                # 4. Đút kết quả Observation ngược lại vào ngữ cảnh để LLM đọc ở bước sau
                current_context += f"\nObservation: {observation_result}"
                logger.log_event("OBSERVATION_ADDED", {"result": observation_result})
            else:
                # Bẫy lỗi: Nếu LLM không xuất ra đúng định dạng Action mà cũng không có Final Answer
                error_msg = "Lỗi hệ thống: Định dạng phản hồi của AI không hợp lệ (Thiếu Action hoặc Final Answer)."
                current_context += f"\nObservation: {error_msg}. Vui lòng sửa lại định dạng chuẩn theo hướng dẫn."
                logger.log_event("PARSER_ERROR", {"output_failed": llm_output})

        # Nếu vượt quá số bước tối đa (max_steps) mà chưa ra kết quả
        logger.log_event("AGENT_TIMEOUT", {"steps": steps})
        return "Xin lỗi phụ huynh, hệ thống đang bận xử lý dữ liệu sâu. Vui lòng thử lại câu hỏi cụ thể hơn."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Hàm bổ trợ tìm kiếm tool theo tên, ép kiểu dữ liệu bằng Pydantic và chạy hàm.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    # Chuyển đổi chuỗi tham số thành Python Dictionary
                    parsed_args = json.loads(args) if isinstance(args, str) else args
                    
                    # Điểm mấu chốt: Dùng Pydantic Model đã thống nhất ở tầng tool để kiểm thử tính hợp lệ
                    validated_data = tool["input_model"](**parsed_args)
                    
                    # Thực thi hàm logic thực tế từ file src/tools/
                    return tool["function"](**validated_data.model_dump())
                    
                except json.JSONDecodeError:
                    return f"Lỗi: Tham số truyền vào hàm {tool_name} không phải là định dạng JSON hợp lệ."
                except Exception as e:
                    return f"Lỗi thực thi dữ liệu tại {tool_name}: {str(e)}"
                    
        return f"Lỗi: Không tìm thấy công cụ mang tên '{tool_name}' trong hệ thống."