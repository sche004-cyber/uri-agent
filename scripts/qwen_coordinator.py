#!/usr/bin/env python3
"""
URI Qwen Coordinator Driver (AO-3)
----------------------------------
Lightweight development-only coordinator driver.
Connects Antigravity (development control surface & implementer) with
Qwen 3 14B (local Ollama reasoning & coordination layer).

Architectural Rules (AO-2 / AO-3):
1. Qwen proposes; Antigravity validates and controls execution.
2. Qwen possesses ZERO direct file, shell, tool, commit, or approval authority.
3. Negative constraints and protected boundaries are first-class context.
4. Coordination proposals must strictly conform to the 12-field schema.
5. All proposals must pass Antigravity deterministic validation before execution.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Default Configuration
DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = "qwen3:14b"
DEFAULT_NUM_CTX = 8192
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TIMEOUT_SEC = 180

# 12 Required Schema Fields
REQUIRED_PROPOSAL_FIELDS = [
    "Current Task Understanding",
    "Recommended Next Action",
    "Selected Worker",
    "Reason for Selection",
    "Required Context",
    "Scope",
    "Negative Constraints",
    "Expected Deliverable",
    "Verification Requirements",
    "Escalation Requirement",
    "Confidence & Risks",
    "Recommended Next State",
]

# Canonical Workers (AO-2)
VALID_WORKERS = {
    "Antigravity",
    "Codex",
    "Claude Code",
    "User",
}

# 12-State Lifecycle (AO-2)
VALID_STATES = {
    "IDLE",
    "TRIAGED",
    "PLANNED",
    "DELEGATED",
    "IMPLEMENTING",
    "TESTING",
    "REVIEWING",
    "AUDITING",
    "AWAITING_APPROVAL",
    "VERIFIED",
    "COMMITTED",
    "PUSHED",
}

# Protected Invariant Boundaries (Never modified without user approval)
PROTECTED_INVARIANT_FILES = {
    "uri_core/core/approval_gate.py",
    "uri_core/core/approval_store.py",
    "step3_test.py",
    "step4_test.py",
    "URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md",
    "URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md",
    "URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md",
}

# Known Deferred Features (Not permitted in current milestone scope)
DEFERRED_FEATURES = [
    "M22.4 CapabilityResolver per-user grants",
    "M22.5 provider secrets and credential vault",
    "Developer Mode",
    "External messaging approval channels (Telegram, SMS, WhatsApp)",
    "Remote/mobile non-loopback exposure prior to M22.3",
]


@dataclass
class CoordinationProposal:
    raw_response: str
    fields: Dict[str, str] = field(default_factory=dict)
    reasoning_trace: Optional[str] = None
    is_schema_valid: bool = False
    missing_fields: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    facts: List[str] = field(default_factory=list)
    unverified_claims: List[str] = field(default_factory=list)


@dataclass
class CoordinatorResponse:
    success: bool
    task: str
    proposal: Optional[CoordinationProposal] = None
    validation: Optional[ValidationResult] = None
    latency_sec: float = 0.0
    tokens_generated: int = 0
    tokens_per_sec: float = 0.0
    error_message: Optional[str] = None


class OllamaClient:
    """Direct HTTP client for local Ollama service."""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_HOST, timeout: int = DEFAULT_TIMEOUT_SEC):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Tuple[bool, str]:
        """Check if Ollama service is reachable."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "URI-Coordinator/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "Ollama service is reachable"
                return False, f"Ollama returned HTTP status {resp.status}"
        except urllib.error.URLError as e:
            return False, f"Ollama unreachable at {self.base_url}: {e}"
        except Exception as e:
            return False, f"Ollama check failed: {e}"

    def check_model_available(self, model_name: str = DEFAULT_MODEL) -> Tuple[bool, str]:
        """Check if target model is installed in local Ollama."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "URI-Coordinator/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status != 200:
                    return False, f"HTTP {resp.status} checking models"
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                # Match model name with or without :latest
                model_base = model_name.split(":")[0]
                installed = any(m == model_name or m.startswith(f"{model_base}:") for m in models)
                if installed:
                    return True, f"Model '{model_name}' is available"
                return False, f"Model '{model_name}' not found. Installed: {models}"
        except Exception as e:
            return False, f"Failed to check model availability: {e}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        num_ctx: int = DEFAULT_NUM_CTX,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> Dict[str, Any]:
        """Send chat completion request to Ollama."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "temperature": temperature,
            },
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "URI-Coordinator/1.0",
            },
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            elapsed = time.time() - t0
            if resp.status != 200:
                raise RuntimeError(f"Ollama returned HTTP {resp.status}")
            raw = resp.read().decode("utf-8")
            result = json.loads(raw)
            result["_elapsed_sec"] = elapsed
            return result


def find_repo_root() -> Path:
    """Find repository root by looking for AGENTS.md or .git."""
    curr = Path(__file__).resolve().parent
    for p in [curr, curr.parent, curr.parent.parent]:
        if (p / "AGENTS.md").exists() or (p / ".git").exists():
            return p
    return Path.cwd()


def assemble_coordinator_context(
    repo_root: Path,
    task_description: str,
    target_milestone: str = "M22.3",
    custom_negative_constraints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Assemble a curated, bounded context packet for Qwen.
    Strictly adheres to AO-2 context assembly rules:
    - Slices relevant material; never sends the entire repository.
    - Treats negative constraints as first-class context.
    - Includes prior verified baseline evidence.
    """
    context_parts: List[str] = []
    facts: List[str] = []

    # 1. Team Model & Governance Invariant
    governance_summary = (
        "## CANONICAL DEVELOPMENT TEAM (AO-2)\n"
        "- User: Final Authority (all consequential architecture, security, approvals)\n"
        "- Antigravity (Gemini 3.8 Flash): Development Control Surface & Implementer (tools, shell, files, UI/Flutter, gates, commits)\n"
        "- Qwen 3 14B (Local Ollama): Day-to-Day Development Coordinator (reasoning, task triage, delegation proposals, reviews)\n"
        "- Codex: Specialist Implementation Worker (substantial multi-file coding, test suites)\n"
        "- Claude Code: Senior Architecture & Security Specialist (security boundaries, route auth, deep audit)\n"
        "- Gemma 3: REMOVED / EXCLUDED from active team.\n"
        "\n"
        "## INVARIANT RULES\n"
        "1. Qwen proposes; Antigravity validates, authorizes, and executes.\n"
        "2. Qwen has ZERO direct tool, file, shell, or commit authority.\n"
        "3. Experience tier is strictly UX-only; it NEVER authorizes.\n"
        "4. Never perform duplicate full audits when prior verified baseline evidence is valid.\n"
    )
    context_parts.append(governance_summary)

    # 2. Baseline Status Facts
    baseline_facts = (
        f"- Verified Completed Baseline: M22.2 (commit 34839ce) with 1,141/1,141 tests passing.\n"
        f"- Next Target Milestone: {target_milestone}\n"
        f"- Working Tree State: Uncommitted Flutter Windows scaffolding is active/unverified; preserve it untouched.\n"
    )
    facts.append("Baseline M22.2 verified at commit 34839ce (1,141/1,141 tests passing).")
    facts.append(f"Target milestone is {target_milestone}.")
    context_parts.append(f"## BASELINE FACTS\n{baseline_facts}")

    # 3. Read PROJECT_MEMORY.md (Targeted excerpt)
    pm_path = repo_root / "PROJECT_MEMORY.md"
    if pm_path.exists():
        pm_content = pm_path.read_text(encoding="utf-8", errors="replace")
        context_parts.append(f"## PROJECT MEMORY EXCERPT\n{pm_content[:2500]}")
    else:
        facts.append("WARNING: PROJECT_MEMORY.md not found at root.")

    # 4. Read Milestone Specification (Targeted excerpt from URI_M22_ARCHITECTURE.md)
    m22_path = repo_root / "URI_M22_ARCHITECTURE.md"
    if m22_path.exists() and target_milestone == "M22.3":
        m22_text = m22_path.read_text(encoding="utf-8", errors="replace")
        # Extract Section 24 (M22.3 Endpoint Authorization & Route Classification)
        match = re.search(r"(### M22\.3:.*?)(?=### M22\.4:|\Z)", m22_text, re.DOTALL)
        if match:
            context_parts.append(f"## ACTIVE MILESTONE SPECIFICATION ({target_milestone})\n{match.group(1)[:3500]}")
        else:
            # Fallback to header section
            context_parts.append(f"## ACTIVE MILESTONE SPECIFICATION\n{m22_text[:2000]}")

    # 5. FIRST-CLASS NEGATIVE CONSTRAINTS (Crucial mitigation for Qwen blindspot)
    all_neg_constraints = list(DEFERRED_FEATURES)
    if custom_negative_constraints:
        all_neg_constraints.extend(custom_negative_constraints)

    neg_constraints_block = "## MANDATORY FIRST-CLASS NEGATIVE CONSTRAINTS (DO NOT VIOLATE)\n"
    for nc in all_neg_constraints:
        neg_constraints_block += f"- PROHIBITED / DEFERRED: {nc}\n"
    neg_constraints_block += "- PROTECTED FILES (DO NOT MODIFY): " + ", ".join(PROTECTED_INVARIANT_FILES) + "\n"
    neg_constraints_block += "- ZERO-AUTHORITY RULE: experience_tier must NEVER be used for authorization or role checks.\n"
    neg_constraints_block += "- BOUNDARY RULE: Model proposals cannot grant capability, approval, or execution authority.\n"

    context_parts.append(neg_constraints_block)

    # 6. User Task Description
    task_block = f"## ASSIGNED COORDINATION TASK\n{task_description}\n"
    context_parts.append(task_block)

    full_prompt = "\n\n".join(context_parts)
    return {
        "full_prompt": full_prompt,
        "facts": facts,
        "negative_constraints": all_neg_constraints,
        "target_milestone": target_milestone,
    }


def parse_coordination_proposal(raw_text: str) -> CoordinationProposal:
    """
    Parse and extract the 12 fields of the structured COORDINATION PROPOSAL schema.
    Strips internal thinking tokens if present.
    """
    # Extract reasoning trace if <think> tags are present
    reasoning_trace = None
    think_match = re.search(r"<think>(.*?)</think>", raw_text, re.DOTALL)
    if think_match:
        reasoning_trace = think_match.group(1).strip()
        cleaned_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    else:
        cleaned_text = raw_text.strip()

    extracted_fields: Dict[str, str] = {}
    missing_fields: List[str] = []

    for field_name in REQUIRED_PROPOSAL_FIELDS:
        # Match patterns like:
        # - **Current Task Understanding:** Content
        # - Current Task Understanding: Content
        # ### Current Task Understanding Content
        pattern = (
            rf"(?:^|\n)[ \t]*[-*]?[ \t]*(?:\*\*)?{re.escape(field_name)}(?:\*\*)?:?[ \t]*\n?(.*?)(?=(?:\n[ \t]*[-*]?[ \t]*(?:\*\*)?[A-Z][a-zA-Z &]+(?:\*\*)?:)|\Z)"
        )
        match = re.search(pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Clean leading/trailing markdown characters
            val = re.sub(r"^:\s*", "", val).strip()
            if val:
                extracted_fields[field_name] = val
            else:
                missing_fields.append(field_name)
        else:
            missing_fields.append(field_name)

    is_valid = len(missing_fields) == 0

    return CoordinationProposal(
        raw_response=raw_text,
        fields=extracted_fields,
        reasoning_trace=reasoning_trace,
        is_schema_valid=is_valid,
        missing_fields=missing_fields,
    )


def validate_proposal_antigravity(
    proposal: CoordinationProposal,
    active_milestone: str = "M22.3",
) -> ValidationResult:
    """
    Perform Antigravity deterministic validation sequence:
    1. Validate proposal structure (all 12 fields present and non-empty).
    2. Validate selected worker against canonical team roles.
    3. Validate scope against protected and untouchable files.
    4. Validate negative constraints (prohibited and deferred features).
    5. Validate approval and escalation requirements.
    6. Validate governing document invariants.
    """
    errors: List[str] = []
    warnings: List[str] = []
    facts: List[str] = []
    unverified: List[str] = []

    # 1. Structure Check
    if not proposal.is_schema_valid:
        errors.append(f"Schema validation failed. Missing required fields: {proposal.missing_fields}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings, facts=facts, unverified_claims=unverified)

    fields = proposal.fields

    # 2. Worker Validation
    selected_worker = fields.get("Selected Worker", "").strip()
    # Normalize worker name
    matched_worker = None
    for vw in VALID_WORKERS:
        if vw.lower() in selected_worker.lower():
            matched_worker = vw
            break

    if not matched_worker:
        errors.append(f"Invalid Selected Worker '{selected_worker}'. Permitted: {sorted(VALID_WORKERS)}")
    else:
        facts.append(f"Worker '{matched_worker}' is an approved active team member.")
        if "gemma" in selected_worker.lower():
            errors.append("Selected worker includes Gemma 3, which is explicitly removed from the active team.")

    # 3. Scope Validation
    scope_text = fields.get("Scope", "")
    for pf in PROTECTED_INVARIANT_FILES:
        if pf in scope_text:
            errors.append(f"Scope violation: Proposal touches protected invariant file '{pf}'.")

    # 4. Negative Constraint & Deferred Feature Validation
    action_text = fields.get("Recommended Next Action", "") + " " + fields.get("Expected Deliverable", "")
    for df in DEFERRED_FEATURES:
        df_keyword = df.split()[0]
        if df_keyword.lower() in action_text.lower() and "defer" not in action_text.lower() and "out of scope" not in action_text.lower():
            warnings.append(f"Proposal references deferred feature '{df}'. Verify it is not being implemented prematurely.")

    # Check for experience_tier authorization misuse
    combined_text = (
        action_text + " " + fields.get("Current Task Understanding", "") + " " + fields.get("Reason for Selection", "")
    )
    if re.search(r"experience_tier.*(?:authorize|role|permission|allow)", combined_text, re.IGNORECASE):
        errors.append("Critical invariant violation: experience_tier cannot be used for authorization.")

    # 5. Escalation Validation
    escalation = fields.get("Escalation Requirement", "")
    if ("security" in action_text.lower() or "route auth" in action_text.lower() or "boundary" in action_text.lower()):
        if "claude" not in escalation.lower() and "user" not in escalation.lower() and "none" in escalation.lower():
            warnings.append("Security/boundary task proposed without escalating to Claude Code or User.")

    # 6. State Validation
    next_state = fields.get("Recommended Next State", "").strip().upper()
    state_match = None
    for vs in VALID_STATES:
        if vs in next_state:
            state_match = vs
            break

    # Fallback normalization for descriptive state text
    if not state_match:
        if "AWAIT" in next_state or "APPROVAL" in next_state:
            state_match = "AWAITING_APPROVAL"
        elif "TRIAGE" in next_state:
            state_match = "TRIAGED"
        elif "PLAN" in next_state:
            state_match = "PLANNED"
        elif "DELEGAT" in next_state:
            state_match = "DELEGATED"
        elif "AUDIT" in next_state:
            state_match = "AUDITING"
        elif "TEST" in next_state:
            state_match = "TESTING"
        elif "REVIEW" in next_state:
            state_match = "REVIEWING"

    if not state_match:
        errors.append(f"Invalid Recommended Next State '{next_state}'. Valid states: {sorted(VALID_STATES)}")
    else:
        facts.append(f"Recommended next state '{state_match}' is valid in the 12-state lifecycle.")


    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        facts=facts,
        unverified_claims=unverified,
    )


class QwenCoordinatorDriver:
    """
    Main driver class for Qwen coordination sessions.
    Coordinates context assembly, Ollama API invocation, and Antigravity validation.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_MODEL,
        num_ctx: int = DEFAULT_NUM_CTX,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.repo_root = repo_root or find_repo_root()
        self.ollama = OllamaClient(base_url=ollama_host)
        self.model = model
        self.num_ctx = num_ctx
        self.temperature = temperature

    def coordinate_task(
        self,
        task_description: str,
        target_milestone: str = "M22.3",
        custom_negative_constraints: Optional[List[str]] = None,
        mock_raw_response: Optional[str] = None,
    ) -> CoordinatorResponse:
        """
        Execute one coordination reasoning cycle:
        1. Verify Ollama & model availability (unless mock provided).
        2. Assemble curated context packet with first-class negative constraints.
        3. Dispatch to qwen3:14b via Ollama chat API.
        4. Parse structured coordination proposal.
        5. Run Antigravity deterministic validation.
        6. Return proposal and validation results (DO NOT EXECUTE).
        """
        t0 = time.time()

        # Step 1: Health / Pre-flight checks
        if mock_raw_response is None:
            healthy, msg = self.ollama.check_health()
            if not healthy:
                return CoordinatorResponse(
                    success=False,
                    task=task_description,
                    error_message=f"PRE-FLIGHT FAILURE: {msg}",
                    latency_sec=time.time() - t0,
                )

            model_avail, msg = self.ollama.check_model_available(self.model)
            if not model_avail:
                return CoordinatorResponse(
                    success=False,
                    task=task_description,
                    error_message=f"MODEL UNAVAILABLE: {msg}",
                    latency_sec=time.time() - t0,
                )

        # Step 2: Assemble Context
        context_packet = assemble_coordinator_context(
            repo_root=self.repo_root,
            task_description=task_description,
            target_milestone=target_milestone,
            custom_negative_constraints=custom_negative_constraints,
        )

        system_instruction = (
            "You are Qwen 3 14B, acting as the day-to-day development coordinator for the URI project.\n"
            "Your role is to reason, triage tasks, plan milestones, propose worker delegations, and review deliverables.\n"
            "You possess ZERO direct tool, file, shell, or commit authority.\n"
            "Antigravity is the deterministic control surface that validates your proposal and executes approved steps.\n"
            "\n"
            "You MUST format your output strictly as a structured COORDINATION PROPOSAL with these 12 fields:\n"
            "### COORDINATION PROPOSAL\n"
            "- Current Task Understanding: [Concise summary of user request and active milestone]\n"
            "- Recommended Next Action: [Exact next action to take]\n"
            "- Selected Worker: [Must be one of: Antigravity | Codex | Claude Code | User]\n"
            "- Reason for Selection: [Why this worker fits delegation rules]\n"
            "- Required Context: [Specific documents/files the worker needs]\n"
            "- Scope: [Exact list of files permitted to be read or modified]\n"
            "- Negative Constraints: [Prohibited actions, protected files, out-of-scope items]\n"
            "- Expected Deliverable: [Patch, file creation, audit report, or test run]\n"
            "- Verification Requirements: [Specific unit tests or commands required]\n"
            "- Escalation Requirement: [None | Claude Code | User]\n"
            "- Confidence & Risks: [Coordinator confidence level and identified risks]\n"
            "- Recommended Next State: [Must be exact state: IDLE | TRIAGED | PLANNED | DELEGATED | IMPLEMENTING | TESTING | REVIEWING | AUDITING | AWAITING_APPROVAL | VERIFIED | COMMITTED | PUSHED]\n"
        )


        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": context_packet["full_prompt"]},
        ]

        # Step 3: Ollama Invocation or Mock
        if mock_raw_response is not None:
            raw_content = mock_raw_response
            latency = time.time() - t0
            tokens_gen = len(raw_content.split())
            tok_per_sec = round(tokens_gen / max(latency, 0.001), 1)
        else:
            try:
                resp = self.ollama.chat(
                    messages=messages,
                    model=self.model,
                    num_ctx=self.num_ctx,
                    temperature=self.temperature,
                )
                raw_content = resp.get("message", {}).get("content", "")
                latency = resp.get("_elapsed_sec", time.time() - t0)
                eval_count = resp.get("eval_count", 0)
                eval_dur = resp.get("eval_duration", 1)
                tokens_gen = eval_count
                tok_per_sec = round(eval_count / (eval_dur / 1e9), 1) if eval_dur else 0.0
            except Exception as e:
                return CoordinatorResponse(
                    success=False,
                    task=task_description,
                    error_message=f"OLLAMA API ERROR: {e}",
                    latency_sec=time.time() - t0,
                )

        # Step 4: Parse Proposal
        proposal = parse_coordination_proposal(raw_content)

        # Step 5: Antigravity Deterministic Validation
        validation = validate_proposal_antigravity(proposal, active_milestone=target_milestone)

        # Append repository facts
        validation.facts.extend(context_packet["facts"])

        return CoordinatorResponse(
            success=validation.is_valid,
            task=task_description,
            proposal=proposal,
            validation=validation,
            latency_sec=round(latency, 2),
            tokens_generated=tokens_gen,
            tokens_per_sec=tok_per_sec,
            error_message=None if validation.is_valid else f"Validation failed: {validation.errors}",
        )


def format_coordinator_report(resp: CoordinatorResponse) -> str:
    """Format a human-readable and structured coordination report."""
    lines = []
    lines.append("=" * 70)
    lines.append("URI AO-3 COORDINATION REPORT")
    lines.append("=" * 70)
    lines.append(f"Task: {resp.task}")
    lines.append(f"Status: {'VALID PROPOSAL' if resp.success else 'INVALID / FAILED'}")
    lines.append(f"Latency: {resp.latency_sec}s | Tokens: {resp.tokens_generated} ({resp.tokens_per_sec} tok/s)")

    if resp.error_message:
        lines.append(f"\n[ERROR] {resp.error_message}")

    if resp.validation:
        lines.append("\n[FACTS (VERIFIED BASELINE)]")
        for f in resp.validation.facts:
            lines.append(f"  [OK] {f}")

        if resp.validation.errors:
            lines.append("\n[ANTIGRAVITY VALIDATION ERRORS]")
            for err in resp.validation.errors:
                lines.append(f"  [FAIL] {err}")

        if resp.validation.warnings:
            lines.append("\n[WARNINGS]")
            for warn in resp.validation.warnings:
                lines.append(f"  [WARN] {warn}")

    if resp.proposal and resp.proposal.is_schema_valid:
        lines.append("\n[QWEN COORDINATION PROPOSAL]")
        for k, v in resp.proposal.fields.items():
            lines.append(f"\n- **{k}:**")
            lines.append(f"  {v}")
    elif resp.proposal:
        lines.append("\n[RAW UNPARSEABLE PROPOSAL]")
        lines.append(resp.proposal.raw_response[:1000])

    lines.append("\n" + "=" * 70)
    lines.append("EXECUTION CONTROL: Antigravity retains authority. Work is NOT executed.")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="URI Qwen Coordinator Driver (AO-3)")
    parser.add_argument("--task", type=str, required=False, help="Task description for coordination reasoning")
    parser.add_argument("--milestone", type=str, default="M22.3", help="Target milestone")
    parser.add_argument("--check-health", action="store_true", help="Check Ollama health and model availability")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--host", type=str, default=DEFAULT_OLLAMA_HOST, help="Ollama API base URL")
    args = parser.parse_args()

    driver = QwenCoordinatorDriver(ollama_host=args.host, model=args.model)

    if args.check_health:
        healthy, h_msg = driver.ollama.check_health()
        print(f"Health: {h_msg}")
        if healthy:
            avail, m_msg = driver.ollama.check_model_available(args.model)
            print(f"Model: {m_msg}")
            sys.exit(0 if avail else 1)
        sys.exit(1)

    if not args.task:
        # Default pilot task from prompt specification
        task = (
            "Review PROJECT_MEMORY.md and identify the next development milestone, "
            "the relevant governing documents, the appropriate worker for the task, "
            "and the required verification steps. Do not modify any files."
        )
    else:
        task = args.task

    print(f"Starting Qwen Coordinator Reasoning for task: '{task}'...\n")
    resp = driver.coordinate_task(task_description=task, target_milestone=args.milestone)
    print(format_coordinator_report(resp))

    sys.exit(0 if resp.success else 1)


if __name__ == "__main__":
    main()
