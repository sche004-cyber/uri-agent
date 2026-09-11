"""Gemma 4 12B Implementation Worker Driver (AO-4).

Interfaces with local Ollama to invoke Gemma 4 12B under the qualified configuration:
temperature=1.0, top_k=64, top_p=0.95, repeat_penalty=1.1, num_ctx=16384.

Role & Invariants (ORCHESTRATION.md §1.2, §10.1, §10.2):
- Gemma has NO Git authority and NO architectural authority.
- Gemma implements strictly the accepted plan's scope (backend and UI when required).
- Gemma produces the structured GEMMA RETURN REPORT for Antigravity audit.
- No silent model substitution: Qwen or Codex cannot be used without explicit user authorization.

Boundary Guarantee: Development-only tooling. Not part of URI runtime.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.dev_workflow.state_machine import (
    InvariantViolationError,
    WorkflowActor,
)
from scripts.dev_workflow.state_manager import GemmaReturnReport

# Qualified Gemma 4 12B Hyperparameters
QUALIFIED_GEMMA_CONFIG = {
    "model": "gemma4:12b",
    "temperature": 1.0,
    "top_k": 64,
    "top_p": 0.95,
    "repeat_penalty": 1.1,
    "num_ctx": 16384,
}

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class TaskBrief:
    milestone_id: str
    objective: str
    scope: str
    out_of_scope_protected: str
    acceptance_criteria: str
    test_plan: str
    security_considerations: str
    ui_impact: str
    raw_markdown: str


class GemmaDriver:
    """Invokes and coordinates Gemma 4 12B for milestone implementation."""

    def __init__(
        self,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
        model_name: str = QUALIFIED_GEMMA_CONFIG["model"],
        timeout_sec: int = 300,
    ):
        self.ollama_host = ollama_host.rstrip("/")
        self.model_name = model_name
        self.timeout_sec = timeout_sec

    def extract_task_brief(self, plan_file: Path, milestone_id: str) -> TaskBrief:
        """Extract the canonical task brief sections from an accepted plan document."""
        if not plan_file.exists():
            raise FileNotFoundError(f"Plan file not found: {plan_file}")

        text = plan_file.read_text(encoding="utf-8")

        def extract_section(keyword: str) -> str:
            # First attempt: heading split
            parts = re.split(r"\n(?=##?\s+)", text)
            for p in parts:
                first_line = p.splitlines()[0] if p.splitlines() else ""
                if keyword.lower() in first_line.lower():
                    return "\n".join(p.splitlines()[1:]).strip()
            # Second attempt: bold keyword or markdown subhead
            pattern = rf"(?:###|\*\*)\s*{re.escape(keyword)}:?\s*\*\*?(.*?)(?=(?:###|\*\*)[A-Za-z0-9 _-]+:?|\Z)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        first_line = text.splitlines()[0] if text.splitlines() else ""
        objective = extract_section("Goal Description") or extract_section("Objective") or first_line
        scope = extract_section("Scope")
        protected = extract_section("Out-of-Scope / Protected Files") or extract_section("Out-of-Scope") or extract_section("Protected")
        criteria = extract_section("Acceptance Criteria")
        test_plan = extract_section("Test Plan")
        security = extract_section("Security Considerations") or extract_section("Security")
        ui_impact_match = re.search(r"UI\s*IMPACT[:\s]+(\w+)", text, re.IGNORECASE)
        ui_impact = ui_impact_match.group(1).upper() if ui_impact_match else (extract_section("UI IMPACT") or "NONE")

        return TaskBrief(
            milestone_id=milestone_id,
            objective=objective,
            scope=scope,
            out_of_scope_protected=protected,
            acceptance_criteria=criteria,
            test_plan=test_plan,
            security_considerations=security,
            ui_impact=ui_impact,
            raw_markdown=text,
        )

    def build_prompt(self, brief: TaskBrief) -> str:
        """Construct the execution prompt injecting negative constraints and reporting requirements."""
        prompt = (
            f"You are Gemma 4 12B, the primary implementer for the URI agent development team.\n"
            f"You are implementing accepted milestone: {brief.milestone_id}\n\n"
            f"NON-NEGOTIABLE BOUNDARIES (ORCHESTRATION.md):\n"
            f"- You have ZERO Git authority (no commits, no pushes, no branch creation).\n"
            f"- You have ZERO architecture authority: implement exactly what was accepted.\n"
            f"- Respect all Out-of-Scope and Protected Files. Do NOT modify them.\n"
            f"- If UI IMPACT is REQUIRED, UI implementation must be included with backend contracts.\n\n"
            f"TASK BRIEF:\n"
            f"- Milestone: {brief.milestone_id}\n"
            f"- Objective: {brief.objective}\n"
            f"- Scope: {brief.scope}\n"
            f"- Protected / Out-of-Scope Files: {brief.out_of_scope_protected}\n"
            f"- Acceptance Criteria:\n{brief.acceptance_criteria}\n"
            f"- Test Plan:\n{brief.test_plan}\n"
            f"- Security Considerations:\n{brief.security_considerations}\n"
            f"- UI Impact: {brief.ui_impact}\n\n"
            f"FILE-WRITE FORMAT:\n"
            f"If you produce new code or modify existing code within your authorized scope, output each file as:\n"
            f"### FILE: <relative_path_from_repo_root>\n"
            f"```<language>\n"
            f"<complete file content>\n"
            f"```\n\n"
            f"OUTPUT FORMAT REQUIREMENT:\n"
            f"You must summarize your work strictly in the following GEMMA RETURN REPORT format:\n"
            f"```markdown\n"
            f"### GEMMA RETURN REPORT\n"
            f"- **Milestone ID:** {brief.milestone_id}\n"
            f"- **Summary of Actions:** <Concrete summary of code changes implemented>\n"
            f"- **Files Modified/Created:** <List of modified or new files with line counts>\n"
            f"- **Tests Performed:** <Exact test commands run and pass/fail counts>\n"
            f"- **Assumptions & Decisions:** <Bounded decisions made within accepted scope>\n"
            f"- **Known Issues / Gaps:** <Any remaining gaps or unverified edges>\n"
            f"```\n"
        )
        return prompt

    def query_ollama(
        self,
        prompt: str,
        system_instruction: str = "You are a precise AI coding assistant implementing an accepted milestone specification.",
        worker_actor: WorkflowActor = WorkflowActor.GEMMA,
        user_authorized_fallback: bool = False,
    ) -> str:
        """Send prompt to Ollama with qualified hyperparameters and anti-substitution check."""
        if worker_actor != WorkflowActor.GEMMA and not user_authorized_fallback:
            raise InvariantViolationError(
                f"Model Substitution Invariant: Cannot invoke worker '{worker_actor.value}' without "
                "explicit User authorization."
            )

        endpoint = f"{self.ollama_host}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            "options": {
                "temperature": QUALIFIED_GEMMA_CONFIG["temperature"],
                "top_k": QUALIFIED_GEMMA_CONFIG["top_k"],
                "top_p": QUALIFIED_GEMMA_CONFIG["top_p"],
                "repeat_penalty": QUALIFIED_GEMMA_CONFIG["repeat_penalty"],
                "num_ctx": QUALIFIED_GEMMA_CONFIG["num_ctx"],
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to communicate with Ollama at {self.ollama_host}: {e}")

    def extract_code_blocks(self, response_text: str) -> List[tuple[str, str]]:
        """Extract (file_path, content) blocks from Gemma's response."""
        results: List[tuple[str, str]] = []

        # Pattern 1: ### FILE: <path>\n```<lang>\n<content>\n```
        p1 = re.compile(
            r"(?:###|\*\*)\s*(?:FILE|File):\s*`?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)`?\s*\n```[a-zA-Z0-9_-]*\s*\n(.*?)\n```",
            re.DOTALL,
        )
        for m in p1.finditer(response_text):
            path = m.group(1).strip()
            content = m.group(2)
            results.append((path, content))

        # Pattern 2: ```<lang> (?:path|file)="<path>"\n<content>\n```
        p2 = re.compile(
            r"```[a-zA-Z0-9_-]*\s+(?:path|file)=[\"']([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)[\"']\s*\n(.*?)\n```",
            re.DOTALL,
        )
        for m in p2.finditer(response_text):
            path = m.group(1).strip()
            content = m.group(2)
            if not any(r[0] == path for r in results):
                results.append((path, content))

        return results

    def parse_return_report(self, response_text: str, milestone_id: str) -> GemmaReturnReport:
        """Parse Gemma's response into a structured GemmaReturnReport."""
        report = GemmaReturnReport(milestone_id=milestone_id)

        match = re.search(r"### GEMMA RETURN REPORT\s*\n(.*?)(?=```|\Z)", response_text, re.DOTALL)
        body = match.group(1) if match else response_text

        def extract_field(name: str) -> str:
            m = re.search(rf"- \*\*{re.escape(name)}:\*\*\s*(.*?)(?=\n- \*\*|\Z)", body, re.DOTALL)
            return m.group(1).strip() if m else ""

        report.summary_of_actions = extract_field("Summary of Actions") or "Implementation executed."
        report.files_modified_created = extract_field("Files Modified/Created") or "None reported."
        report.tests_performed = extract_field("Tests Performed") or "None reported."
        report.assumptions_decisions = extract_field("Assumptions & Decisions") or "None."
        report.known_issues_gaps = extract_field("Known Issues / Gaps") or "None."

        return report
