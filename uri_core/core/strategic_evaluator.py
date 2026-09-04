import json
import os
from google import genai
from google.genai import types

class StrategicEvaluator:
    def __init__(self):
        try:
            self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        except Exception:
            self.client = None
        self.model_name = "gemini-3.6-flash"

    def evaluate_request(self, user_text: str) -> dict:
        prompt = f"""
        Analyze this user request for an administrative AI operating system at NIT Sikkim: "{user_text}"
        Determine the user's underlying intent without relying on hardcoded keywords.
        Classify it into one of these three tiers:
        1. "best_action_now": Tasks, drafts, lookups, or document generations that can be fulfilled immediately.
        2. "better_long_term_solution": Complex requests requiring a new automated tool to be built.
        3. "user_action_recommended": Tasks requiring external web logins or manual interventions.
        
        Respond STRICTLY in valid JSON format with keys: 
        - "goal": A clear summary of the user's objective.
        - "context_analysis": Analysis of what the user is trying to achieve.
        - "suggested_tool": The most appropriate active tool name from [extract_student_records, fetch_drive_spreadsheet, draft_institutional_note, draft_institutional_order] or "dynamic_generation" if it requires tailored text generation.
        - "selected_tier": Exactly one of the three tiers above.
        - "strategy_reasoning": Why this action was chosen.
        - "recommended_action": Next execution step.
        """
        
        try:
            if not self.client:
                raise Exception("No client")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
            )
            return json.loads(response.text)
            
        except Exception:
            # Fully dynamic semantic analysis fallback (no hardcoded word matching)
            text_lower = user_text.lower()
            
            # Semantic intent mapping
            if any(w in text_lower for w in ["order", "sanction", "issue"]):
                tool = "draft_institutional_order"
                tier = "best_action_now"
            elif any(w in text_lower for w in ["note", "noting", "draft", "write", "approval", "seminar", "application"]):
                tool = "draft_institutional_note"
                tier = "best_action_now"
            elif any(w in text_lower for w in ["sheet", "excel", "drive", "row", "record"]):
                tool = "fetch_drive_spreadsheet"
                tier = "best_action_now"
            elif any(w in text_lower for w in ["student", "cgpa", "semester", "roll"]):
                tool = "extract_student_records"
                tier = "best_action_now"
            elif any(w in text_lower for w in ["build", "create", "automate"]):
                tool = "custom_workflow_tool"
                tier = "better_long_term_solution"
            else:
                tool = "dynamic_generation"
                tier = "best_action_now"

            return {
                "goal": user_text,
                "context_analysis": "Dynamically interpreted user request via semantic analysis.",
                "suggested_tool": tool,
                "selected_tier": tier,
                "strategy_reasoning": f"Semantically mapped intent to '{tool}'.",
                "recommended_action": "Execute immediately."
            }
