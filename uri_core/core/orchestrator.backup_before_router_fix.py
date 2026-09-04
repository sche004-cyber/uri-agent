from uri_core.core.strategic_evaluator import StrategicEvaluator
from uri_core.core.prompt_builder import PromptBuilder
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.rost_evaluator import ROSTEvaluator
from uri_core.core.hermes_forge import HermesForge
import re

class UriOrchestrator:
    def __init__(self):
        self.strategic_evaluator = StrategicEvaluator()
        self.prompt_builder = PromptBuilder()
        self.dispatcher = ToolDispatcher()
        self.rost = ROSTEvaluator()
        self.forge = HermesForge()

    def process_user_input(self, session_id: str, user_text: str) -> dict:
        try:
            strategy = self.strategic_evaluator.evaluate_request(user_text)
            execution_prompt = self.prompt_builder.build_execution_prompt(strategy)
            tier = strategy.get("selected_tier")
            
            response_html = ""
            text_lower = user_text.lower()
            is_simple_lookup = any(w in text_lower for w in ["student record", "cgpa", "spreadsheet", "drive row"])
            
            if tier == "best_action_now" and is_simple_lookup:
                tool_to_run = "fetch_drive_spreadsheet" if "spreadsheet" in text_lower else "extract_student_records"
                dispatch_result = self.dispatcher.execute_tool(tool_to_run, request_text=user_text)
                response_html = f"<b style='color:green;'>Data Retrieval Result:</b><br><pre>{dispatch_result.get('data', dispatch_result)}</pre>"
            
            else:
                words = re.findall(r'\w+', user_text.lower())
                tool_slug = "_".join(words[:4]) if len(words) >= 4 else "custom_admin_task"
                tool_name = f"tool_{tool_slug}"
                
                response_html += f"<b style='color:purple;'>Hermes Agent Brain:</b> Analyzing requirement and self-building custom execution module...<br>"
                
                rost_result = self.rost.evaluate_skill_proposal(tool_name, user_text)
                forge_res = self.forge.forge_tool(tool_name, f"Fulfill user objective adhering to institutional norms: {user_text}")
                
                if forge_res.get("status") == "success":
                    # Correctly scope and assign execution result
                    exec_res = self.dispatcher.execute_tool(tool_name, user_text=user_text)
                    
                    if exec_res.get("status") == "success":
                        data = exec_res.get("data")
                        if isinstance(data, dict) and "result" in data:
                            content = data["result"]
                        else:
                            content = str(data)
                        response_html += f"<br><b style='color:green;'>Self-Built Execution Success (Module: {tool_name}.py):</b><br><pre>{content}</pre>"
                    else:
                        response_html += f"<br><b style='color:orange;'>Tool Built, but execution returned:</b> {exec_res.get('message')}"
                else:
                    response_html += f"<br><b style='color:red;'>Hermes Forge Error:</b> {forge_res.get('message')}"

            return {
                "status": "success",
                "strategy": strategy,
                "instructions": execution_prompt,
                "response": response_html
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
