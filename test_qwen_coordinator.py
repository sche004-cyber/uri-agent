#!/usr/bin/env python3
"""
Unit Tests for Qwen Coordinator Driver (AO-3)
---------------------------------------------
Tests context assembly, negative-constraint inclusion, structured proposal parsing,
Antigravity deterministic validation, and safety error handling.
Does not require live Ollama service (mocked for deterministic unit testing).
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.qwen_coordinator import (
    DEFERRED_FEATURES,
    PROTECTED_INVARIANT_FILES,
    REQUIRED_PROPOSAL_FIELDS,
    VALID_STATES,
    VALID_WORKERS,
    CoordinationProposal,
    OllamaClient,
    QwenCoordinatorDriver,
    ValidationResult,
    assemble_coordinator_context,
    parse_coordination_proposal,
    validate_proposal_antigravity,
)

SAMPLE_VALID_PROPOSAL_TEXT = """
<think>
Evaluating task: Review PROJECT_MEMORY.md.
Worker selection: This is a documentation/review task, suited for Antigravity direct or local review.
</think>

### COORDINATION PROPOSAL
- **Current Task Understanding:** Review PROJECT_MEMORY.md to determine next milestone and governing documents.
- **Recommended Next Action:** TRIAGE the next milestone requirements and plan the step.
- **Selected Worker:** Antigravity
- **Reason for Selection:** Direct documentation and inspection task within the control surface.
- **Required Context:** PROJECT_MEMORY.md, AGENTS.md, URI_M22_ARCHITECTURE.md.
- **Scope:** Read-only inspection of markdown files. No code modifications permitted.
- **Negative Constraints:** Do not modify runtime code, do not implement deferred M22.4 or M22.5 features.
- **Expected Deliverable:** A clear milestone review summary.
- **Verification Requirements:** None required for read-only documentation review.
- **Escalation Requirement:** None
- **Confidence & Risks:** High confidence; read-only low-risk task.
- **Recommended Next State:** TRIAGED
"""

SAMPLE_MALFORMED_PROPOSAL_TEXT = """
I think we should do this task by having Codex write some code.
Here is what we should do:
1. Update files
2. Run tests
"""


class TestQwenCoordinatorDriver(unittest.TestCase):

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent

    def test_context_assembly_contains_governance_and_baseline(self):
        """Test that context packet contains AO-2 team model, baseline facts, and active milestone."""
        context = assemble_coordinator_context(
            repo_root=self.repo_root,
            task_description="Review milestone state",
            target_milestone="M22.3",
        )
        prompt = context["full_prompt"]
        self.assertIn("CANONICAL DEVELOPMENT TEAM (AO-2)", prompt)
        self.assertIn("Antigravity", prompt)
        self.assertIn("Qwen 3 14B", prompt)
        self.assertIn("Codex", prompt)
        self.assertIn("Claude Code", prompt)
        self.assertIn("Gemma 3: REMOVED / EXCLUDED", prompt)
        self.assertIn("34839ce", prompt)
        self.assertIn("1,141/1,141", prompt)
        self.assertIn("M22.3", prompt)

    def test_negative_constraints_are_first_class(self):
        """Test that negative constraints, deferred features, and protected files are explicitly injected."""
        custom_neg = ["DO NOT TOUCH DATABASE", "NO EXTERNAL HTTP CALLS"]
        context = assemble_coordinator_context(
            repo_root=self.repo_root,
            task_description="Test task",
            target_milestone="M22.3",
            custom_negative_constraints=custom_neg,
        )
        prompt = context["full_prompt"]
        self.assertIn("MANDATORY FIRST-CLASS NEGATIVE CONSTRAINTS", prompt)
        for df in DEFERRED_FEATURES:
            self.assertIn(df, prompt)
        for pf in PROTECTED_INVARIANT_FILES:
            self.assertIn(pf, prompt)
        for cn in custom_neg:
            self.assertIn(cn, prompt)
        self.assertIn("experience_tier must NEVER be used for authorization", prompt)

    def test_proposal_parsing_valid_schema(self):
        """Test parsing of a complete 12-field proposal."""
        proposal = parse_coordination_proposal(SAMPLE_VALID_PROPOSAL_TEXT)
        self.assertTrue(proposal.is_schema_valid)
        self.assertEqual(len(proposal.missing_fields), 0)
        self.assertIsNotNone(proposal.reasoning_trace)
        self.assertIn("Evaluating task", proposal.reasoning_trace)
        for f in REQUIRED_PROPOSAL_FIELDS:
            self.assertIn(f, proposal.fields)
            self.assertTrue(len(proposal.fields[f]) > 0)

    def test_proposal_parsing_malformed_schema(self):
        """Test that malformed or missing fields are detected."""
        proposal = parse_coordination_proposal(SAMPLE_MALFORMED_PROPOSAL_TEXT)
        self.assertFalse(proposal.is_schema_valid)
        self.assertGreater(len(proposal.missing_fields), 0)

    def test_antigravity_validation_success(self):
        """Test Antigravity validation on a valid proposal."""
        proposal = parse_coordination_proposal(SAMPLE_VALID_PROPOSAL_TEXT)
        val = validate_proposal_antigravity(proposal, active_milestone="M22.3")
        self.assertTrue(val.is_valid)
        self.assertEqual(len(val.errors), 0)
        self.assertTrue(any("Antigravity" in f for f in val.facts))
        self.assertTrue(any("TRIAGED" in f for f in val.facts))

    def test_antigravity_validation_rejects_gemma(self):
        """Test Antigravity validation rejects Gemma 3 as selected worker."""
        proposal = parse_coordination_proposal(SAMPLE_VALID_PROPOSAL_TEXT)
        proposal.fields["Selected Worker"] = "Gemma 3"
        val = validate_proposal_antigravity(proposal, active_milestone="M22.3")
        self.assertFalse(val.is_valid)
        self.assertTrue(any("Gemma 3" in e for e in val.errors))

    def test_antigravity_validation_rejects_unknown_worker(self):
        """Test Antigravity validation rejects arbitrary unapproved worker."""
        proposal = parse_coordination_proposal(SAMPLE_VALID_PROPOSAL_TEXT)
        proposal.fields["Selected Worker"] = "ChatGPT 4o"
        val = validate_proposal_antigravity(proposal, active_milestone="M22.3")
        self.assertFalse(val.is_valid)
        self.assertTrue(any("Invalid Selected Worker" in e for e in val.errors))

    def test_antigravity_validation_rejects_protected_file_in_scope(self):
        """Test Antigravity validation rejects modifying protected files."""
        proposal = parse_coordination_proposal(SAMPLE_VALID_PROPOSAL_TEXT)
        proposal.fields["Scope"] = "Modify uri_core/core/approval_gate.py to bypass checks"
        val = validate_proposal_antigravity(proposal, active_milestone="M22.3")
        self.assertFalse(val.is_valid)
        self.assertTrue(any("Scope violation" in e for e in val.errors))

    def test_antigravity_validation_rejects_experience_tier_authorization(self):
        """Test Antigravity validation rejects experience_tier authorization misuse."""
        proposal = parse_coordination_proposal(SAMPLE_VALID_PROPOSAL_TEXT)
        proposal.fields["Recommended Next Action"] = "Check experience_tier to authorize route"
        val = validate_proposal_antigravity(proposal, active_milestone="M22.3")
        self.assertFalse(val.is_valid)
        self.assertTrue(any("experience_tier" in e for e in val.errors))

    def test_antigravity_validation_rejects_invalid_state(self):
        """Test Antigravity validation rejects states outside the 12-state lifecycle."""
        proposal = parse_coordination_proposal(SAMPLE_VALID_PROPOSAL_TEXT)
        proposal.fields["Recommended Next State"] = "RANDOM_CUSTOM_STATE"
        val = validate_proposal_antigravity(proposal, active_milestone="M22.3")
        self.assertFalse(val.is_valid)
        self.assertTrue(any("Invalid Recommended Next State" in e for e in val.errors))

    def test_mock_coordination_run_no_execution(self):
        """Test that driver runs end-to-end with mock and guarantees NO code execution."""
        driver = QwenCoordinatorDriver(repo_root=self.repo_root)
        resp = driver.coordinate_task(
            task_description="Review milestone state",
            target_milestone="M22.3",
            mock_raw_response=SAMPLE_VALID_PROPOSAL_TEXT,
        )
        self.assertTrue(resp.success)
        self.assertIsNotNone(resp.proposal)
        self.assertTrue(resp.proposal.is_schema_valid)
        self.assertIsNotNone(resp.validation)
        self.assertTrue(resp.validation.is_valid)

    def test_health_check_failure_handling(self):
        """Test that driver fails safely when Ollama is unreachable."""
        with patch.object(OllamaClient, "check_health", return_value=(False, "Connection refused")):
            driver = QwenCoordinatorDriver(repo_root=self.repo_root)
            resp = driver.coordinate_task("Sample task")
            self.assertFalse(resp.success)
            self.assertIn("PRE-FLIGHT FAILURE", resp.error_message)

    def test_model_unavailable_handling(self):
        """Test that driver fails safely when target model is not installed."""
        with patch.object(OllamaClient, "check_health", return_value=(True, "OK")), \
             patch.object(OllamaClient, "check_model_available", return_value=(False, "Model not found")):
            driver = QwenCoordinatorDriver(repo_root=self.repo_root)
            resp = driver.coordinate_task("Sample task")
            self.assertFalse(resp.success)
            self.assertIn("MODEL UNAVAILABLE", resp.error_message)


if __name__ == "__main__":
    unittest.main()
