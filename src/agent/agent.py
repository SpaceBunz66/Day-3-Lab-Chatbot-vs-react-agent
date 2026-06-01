import os
import re
import inspect
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class ReActAgent:
    """
    A robust ReAct-style Agent that follows the Thought-Action-Observation loop.
    Supports dynamic tool execution, argument parsing, and detailed log telemetry.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Generates the system prompt instructing the agent on the ReAct loop and formatting.
        Includes descriptions of all available tools.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
Bạn là Trợ lý AI Đồng hành cùng Phụ huynh học sinh (E-School Parent Assistant). Nhiệm vụ của bạn là hỗ trợ phụ huynh theo dõi sát sao tình hình học lực, chuyên cần, thời khóa biểu của con và đưa ra các lời khuyên kèm cặp học tập thực tế từ giáo trình nhà trường (RAG).

KIỂM SOÁT PHẠM VI & NỘI DUNG NHẠY CẢM (GUARDRAILS & OFF-TOPIC CONTROLS):
- Bạn CHỈ được phép trả lời các câu hỏi liên quan trực tiếp đến học tập, điểm số, chuyên cần, thời khóa biểu và các lời khuyên kèm cặp học tập của học sinh.
- Ngoại lệ đối với lời chào hỏi và giao tiếp xã giao thông thường (như "xin chào", "chào bạn", "hello", "chào em", v.v.): Bạn ĐƯỢC PHÉP chào hỏi lại một cách thân thiện, ân cần, tự giới thiệu mình là trợ lý học tập và chủ động hỏi phụ huynh cần hỗ trợ thông tin gì về con (ở bước này bạn có thể đi thẳng tới 'Final Answer' mà không cần gọi công cụ).
- Đối với các yêu cầu hoàn toàn nằm ngoài phạm vi giáo dục (như nấu ăn, thời tiết, giải trí, thể thao, game, chính trị, công nghệ chung, v.v.) hoặc các câu hỏi có chứa từ ngữ thô tục, nhạy cảm: Bạn BẮT BUỘC phải dừng lập luận ngay tại Bước 1, TUYỆT ĐỐI không gọi bất kỳ công cụ nào và đi thẳng tới 'Final Answer' để từ chối một cách lịch sự, ân cần (ví dụ: giải thích rằng bạn là trợ lý học tập nên không thể trả lời các chủ đề khác).

QUY TẮC NHẬN XÉT & ĐÁNH GIÁ CHI TIẾT DỰA TRÊN ĐIỂM SỐ (DETAILED ASSESSMENT RULES):
Khi phụ huynh hỏi về "tình hình học tập", "kết quả học tập" hoặc "điểm số" của con, bạn KHÔNG ĐƯỢC chỉ liệt kê các con số một cách khô khan. Thay vào đó, hãy thực hiện đánh giá sâu sắc và chi tiết theo các tiêu chí sau:
1. Phân loại & So sánh Học lực: Xác định rõ môn học nào là thế mạnh của con (các môn đạt điểm xuất sắc/giỏi từ 8.0 - 10) và những môn học nào con cần chú ý cải thiện (các môn đạt điểm trung bình/khá từ 5.0 - 7.9, hoặc yếu dưới 5.0).
2. Phân tích chi tiết từng con điểm: Đánh giá ý nghĩa của từng mức điểm số cụ thể (ví dụ: điểm chuyên cần đạt tối đa thể hiện sự chăm chỉ, điểm kiểm tra định kỳ phản ánh đúng năng lực hiểu bài trên lớp, nhận xét của giáo viên đi kèm chỉ ra điểm nghẽn kiến thức nào).
3. Đề xuất Lộ trình & Lời khuyên thiết thực (RAG): Sử dụng thông tin từ tài liệu giáo trình và bài học của trường (RAG) để gợi ý lộ trình kèm cặp cụ thể (ví dụ: con cần ôn tập lại kiến thức tuần mấy, chủ đề nào, làm thêm dạng bài tập nào để củng cố).
4. Giọng văn động viên, xây dựng: Luôn giữ phong cách ân cần, đồng cảm, ghi nhận sự nỗ lực của học sinh trước khi đưa ra các giải pháp khắc phục điểm số thấp để phụ huynh không cảm thấy quá áp lực mà có động lực cùng con tiến bộ.

PHONG CÁCH PHẢN HỒI (TONE & VOICE):
- Luôn giữ thái độ lịch sự, ân cần, đồng cảm và có tính xây dựng cao (constructive).
- Tránh đưa ra điểm số hoặc thông báo lỗi chuyên cần một cách khô khan. Hãy giải thích ý nghĩa điểm số, ghi nhận sự cố gắng của học sinh và gợi ý phương án cải thiện cụ thể bằng tiếng Việt rõ ràng.

DANH SÁCH CÔNG CỤ HIỆN CÓ:
{tool_descriptions}

QUY TẮC LẬP LUẬN (ReAct Framework):
Để giải quyết yêu cầu của phụ huynh, bạn BẮT BUỘC phải tuân thủ nghiêm ngặt quy trình ReAct.
Với mỗi bước, bạn chỉ được phép đưa ra đúng một trong hai định dạng sau:

Thought: dòng suy nghĩ lập luận của bạn (bằng tiếng Anh).
Action: tên_công_cụ(các_tham_số)

HOẶC

Thought: I have gathered all necessary information from the tools and database. I am ready to formulate a comprehensive, empathetic and constructive response to the parent in Vietnamese.
Final Answer: câu trả lời hoàn chỉnh, chi tiết và đầy tính xây dựng gửi tới phụ huynh (bằng tiếng Việt).

LƯU Ý QUAN TRỌNG:
1. LUÔN LUÔN bắt đầu mỗi lượt phản hồi bằng 'Thought:'.
2. Không tự ý viết dòng 'Observation:' - dòng này sẽ do hệ thống tự động cung cấp ngay sau khi thực thi công cụ.
3. Chỉ gọi DUY NHẤT một công cụ tại một thời điểm.
4. Khi gọi công cụ ở dòng 'Action', dùng đúng định dạng hàm lập trình, ví dụ: get_student_grades(student_name="Nguyễn Minh Anh") hoặc search_curriculum_and_advice(subject="Ngữ văn", week=10).
5. Nếu không cần dùng công cụ nào nữa để trả lời câu hỏi, hãy đi thẳng tới định dạng 'Final Answer'.
"""

    def run(self, user_input: str) -> str:
        """
        Executes the ReAct loop logic.
        1. Generates Thought + Action.
        2. Parses Action and executes Tool.
        3. Appends Observation to prompt and repeats until Final Answer or max_steps.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = f"Question: {user_input}\n"
        steps = 0

        while steps < self.max_steps:
            logger.log_event("AGENT_STEP", {"step": steps + 1})
            
            # Generate LLM response
            res = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = res["content"].strip()
            
            # Track metrics
            tracker.track_request(
                provider=res.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=res.get("usage", {}),
                latency_ms=res.get("latency_ms", 0)
            )
            
            logger.log_event("LLM_RESPONSE", {"content": content})
            
            # Print intermediate reasoning to terminal
            print(f"\n[Step {steps + 1}]")
            print(content)
            
            # Regex to match Action and Final Answer
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", content)
            final_match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL)
            
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2)
                
                # Execute tool
                observation = self._execute_tool(tool_name, tool_args)
                observation_str = f"Observation: {observation}"
                
                print(f"\n{observation_str}")
                
                # Append current generation + observation back into history
                current_prompt += f"\n{content}\n{observation_str}\n"
                
                logger.log_event("TOOL_EXECUTION", {
                    "tool": tool_name,
                    "arguments": tool_args,
                    "observation": observation
                })
            elif final_match:
                final_answer = final_match.group(1).strip()
                logger.log_event("AGENT_END", {"status": "success", "steps": steps + 1, "final_answer": final_answer})
                return final_answer
            else:
                logger.log_event("PARSER_ERROR", {"content": content})
                
                # Fallback parsing check
                if "Final Answer:" in content:
                    parts = content.split("Final Answer:")
                    final_answer = parts[-1].strip()
                    logger.log_event("AGENT_END", {"status": "success_fallback", "steps": steps + 1})
                    return final_answer
                
                # Instruct agent to correct format
                correction_note = "System Note: Your output did not match 'Action: tool_name(args)' or 'Final Answer: response'. Please follow the instructions."
                current_prompt += f"\n{content}\n{correction_note}\n"
                print(f"\n[SYSTEM] {correction_note}")
                
            steps += 1
            
        logger.log_event("AGENT_TIMEOUT", {"steps": steps})
        return f"Timeout: Exceeded max steps ({self.max_steps}). Current prompt state: {current_prompt}"

    def _parse_args(self, args_str: str) -> Any:
        """
        Cleans and parses tool arguments from string format (key=value, list, or single value).
        """
        args_str = args_str.strip()
        if not args_str:
            return {}

        # 1. Check for key=value format (dictionary-like)
        if '=' in args_str:
            parsed = {}
            # Split by comma but respect quotes if any (simplified comma splitting)
            parts = re.split(r',\s*(?=(?:[^\'"]*[\'"][^\'"]*[\'"])*[^\'"]*$)', args_str)
            for part in parts:
                if '=' in part:
                    k, v = part.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    # Type conversion
                    try:
                        if '.' in v:
                            parsed[k] = float(v)
                        else:
                            parsed[k] = int(v)
                    except ValueError:
                        parsed[k] = v
            return parsed
            
        # 2. Check for comma-separated positional args (list-like)
        elif ',' in args_str:
            parts = re.split(r',\s*(?=(?:[^\'"]*[\'"][^\'"]*[\'"])*[^\'"]*$)', args_str)
            parsed_list = []
            for part in parts:
                part = part.strip().strip('"').strip("'")
                try:
                    if '.' in part:
                        parsed_list.append(float(part))
                    else:
                        parsed_list.append(int(part))
                except ValueError:
                    parsed_list.append(part)
            return parsed_list
            
        # 3. Single argument
        else:
            cleaned = args_str.strip('"').strip("'")
            try:
                if '.' in cleaned:
                    return float(cleaned)
                else:
                    return int(cleaned)
            except ValueError:
                return cleaned

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name with robust argument mapping.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    parsed_args = self._parse_args(args)
                    func = tool['func']
                    sig = inspect.signature(func)
                    
                    if isinstance(parsed_args, dict):
                        # Filter arguments to avoid unexpected keyword errors
                        valid_args = {k: v for k, v in parsed_args.items() if k in sig.parameters}
                        return str(func(**valid_args))
                    elif isinstance(parsed_args, list):
                        return str(func(*parsed_args))
                    else:
                        if len(sig.parameters) == 1:
                            return str(func(parsed_args))
                        else:
                            return str(func(parsed_args))
                except Exception as e:
                    return f"Error executing tool '{tool_name}': {str(e)}"
                    
        return f"Tool '{tool_name}' not found."

