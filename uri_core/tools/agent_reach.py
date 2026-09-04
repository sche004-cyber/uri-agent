import subprocess
import requests
import re
from uri_core.tools.defuddle_tool import DefuddleTool

class AgentReach:
    @staticmethod
    def fetch_url(url: str) -> str:
        # Step 1: Try Agent Reach CLI
        try:
            pass
        except Exception:
            pass

        # Step 2: Try Defuddle
        defuddle_result = DefuddleTool.extract_clean_markdown(url)
        if not defuddle_result.startswith("Error:"):
            return defuddle_result

        # Step 3: Pure Python Fallback (requests)
        try:
            print(f"[Agent Reach] Defuddle failed. Falling back to pure Python requests for {url}...")
            
            # THE FIX: A modern User-Agent header to bypass 403 Bot Blocks
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            html_content = response.text
            html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text_content = re.sub(r'<[^>]+>', ' ', html_content)
            clean_text = ' '.join(text_content.split())
            
            return clean_text
            
        except requests.RequestException as e:
            return f"Error: Agent Reach pure Python fallback failed to retrieve URL: {str(e)}"
        except Exception as e:
            return f"Error: Agent Reach unexpected fallback failure: {str(e)}"
