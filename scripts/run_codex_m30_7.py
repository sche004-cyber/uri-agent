"""DEPRECATED: Milestone-specific launchers are obsolete.
Use scripts/run_codex_current_milestone.py instead.
"""
import sys
import subprocess
import os

print("Redirecting to scripts/run_codex_current_milestone.py...")
runner = os.path.join(os.path.dirname(__file__), "run_codex_current_milestone.py")
sys.exit(subprocess.call([sys.executable, runner]))
