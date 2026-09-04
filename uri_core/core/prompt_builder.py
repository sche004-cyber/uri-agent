class PromptBuilder:
    def __init__(self):
        pass

    def build_execution_prompt(self, evaluated_strategy: dict) -> str:
        # Extract fields from the evaluated JSON
        goal = evaluated_strategy.get("goal", "Unknown Goal")
        tier = evaluated_strategy.get("selected_tier", "best_action_now")
        reasoning = evaluated_strategy.get("strategy_reasoning", "No reasoning provided.")
        recommended = evaluated_strategy.get("recommended_action", "")
        
        # Format a high-density, token-optimized instruction block based on the tier
        if tier == "user_action_recommended":
            return (f"SYSTEM DIRECTIVE: USER ACTION REQUIRED.\n"
                    f"Reasoning: {reasoning}\n"
                    f"Recommended Action: {recommended}\n"
                    f"Inform the user they must complete this step manually.")
            
        elif tier == "better_long_term_solution":
            return (f"SYSTEM DIRECTIVE: SKILL FORGE TRIGGERED.\n"
                    f"Goal: {goal}\n"
                    f"Reasoning: {reasoning}\n"
                    f"Prepare to draft a new capability for the URI Hermes Agent.")
            
        else:
            return (f"SYSTEM DIRECTIVE: EXECUTE IMMEDIATELY.\n"
                    f"Goal: {goal}\n"
                    f"Strategy: {reasoning}\n"
                    f"Execute this task using active capabilities in the registry.")
