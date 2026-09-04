import subprocess
import os

class DefuddleTool:
    @staticmethod
    def extract_clean_markdown(url: str) -> str:
        try:
            npx_executable = "npx.cmd" if os.name == "nt" else "npx"
            # We added '--yes' to automatically accept the package installation!
            command = [npx_executable, "--yes", "defuddle", "parse", url, "--md"]
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True, 
                timeout=45 # Giving it 45 seconds just for the first-time download
            )
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            return f"Error: Defuddle extraction timed out for URL: {url}"
        except FileNotFoundError:
            return "Error: Node.js (npx) is not installed on this system. Please install Node.js."
        except subprocess.CalledProcessError as e:
            return f"Error: Defuddle failed to parse URL. (Code: {e.returncode})\nOutput: {e.stderr}"
        except Exception as e:
            return f"Error: Unexpected failure in DefuddleTool: {str(e)}"
