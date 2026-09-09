"""M22.1: superseded by ModelProvider/build_provider (see
model_providers/base.py, config/model_roles.py) - this pre-M21 direct
Groq/Gemini client is no longer part of any live call path. Its only
production-adjacent caller (uri_core/app/main.py) was removed in M22.1;
see test_shadow_provider_unreachable.py for the enforced proof.

Retained only for test_credential_hygiene.py's regression coverage on
environment-only credential handling (never hardcoded, never silently
substituted when absent) - see URI_M22_ARCHITECTURE.md section 18. This
module is scheduled for deletion once M22.5 (provider registry) ports
that same guarantee onto the real per-user API-key store; do not import
it from any new code."""

import os
import time
try:
    from openai import OpenAI
    from google import genai
except ImportError:
    raise ImportError("Please run 'pip install openai google-genai' in your terminal.")

class HermesService:
    def __init__(self, use_local=False):
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        self.groq_client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=self.groq_api_key)
        self.groq_model = "qwen/qwen3.8-27b"

        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)

    def draft_document(self, prompt: str) -> str:
        estimated_tokens = len(prompt) // 4
        print(f"      [Hydra] Prompt size: ~{estimated_tokens} tokens")
        
        if estimated_tokens < 6500:
            print("      [Hydra] Routing to Groq (Fast Tier)...")
            try:
                return self._call_groq(prompt)
            except Exception as e:
                print(f"      [Hydra] Groq choked! ({str(e)})")
                print("      [Hydra] Seamlessly falling back to Gemini...")
                return self._call_gemini(prompt)
        else:
            print("      [Hydra] Prompt too massive for Groq. Routing straight to Gemini (Heavy Tier)...")
            return self._call_gemini(prompt)
            
    def _call_groq(self, prompt: str) -> str:
        response = self.groq_client.chat.completions.create(
            model=self.groq_model,
            messages=[
                {"role": "system", "content": "You are the official administrative drafter for NIT Sikkim. Output ONLY the exact text of the requested document without any conversational filler."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content
        
    def _call_gemini(self, prompt: str) -> str:
        system_instruction = "You are the official administrative drafter for NIT Sikkim. Output ONLY the exact text of the requested document without any conversational filler."
        full_prompt = f"{system_instruction}\n\n{prompt}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # UPDATED: Using the active 2026 3.6 Flash model!
                response = self.gemini_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=full_prompt,
                )
                return response.text
            except Exception as e:
                error_msg = str(e)
                if '503' in error_msg and attempt < max_retries - 1:
                    print(f"      [Hydra] Gemini server busy (503). Retrying in 3 seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(3)
                else:
                    return f"[ERROR] Both brains failed. Gemini error: {error_msg}"
