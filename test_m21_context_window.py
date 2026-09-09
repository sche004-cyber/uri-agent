"""M21 CRITICAL REGRESSION TEST (deterministic, no live model): the
assembled reasoning request must remain under the configured model
context window.

This is the deterministic counterpart to test_m21_context_window_live.py
(which proves the same thing against a real running Ollama server and is
skipped when one isn't reachable). This file never touches the network -
it exercises the exact same real code path
(UriOrchestrator._build_model_session_context ->
ModelReasoningGateway.build_reasoning_request ->
OllamaReasoningAdapter.__call__) against a worst-case, realistic session
(a 65,000+ character execution_history, mirroring the real session
measured during the M21 audit - see test_m21_prompt_budget.py's identical
fixture) and a fake provider that only records what was actually
transmitted, so it can run in any environment and in CI.

Before M21: this exact shape (a long-running workflow's unbounded
execution_history, plus system_policy duplicated inside the variable user
payload on every call) produced a reasoning prompt of ~4935+ tokens against
Ollama's silent 4096-token runtime default - see ollama_provider.py's and
model_reasoning_adapter.py's M21 comments for the measured numbers. After
M21, the same worst-case session must fit comfortably under
ModelProviderConfig's configured context_tokens.
"""

import json
import unittest

from uri_core.core.context_budget import estimate_tokens
from uri_core.core.model_providers.base import ModelProviderConfig
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.state import SessionState


class _CapturingProvider:
    """Records exactly what system/user text OllamaReasoningAdapter sends,
    without making any real network call."""

    def __init__(self):
        self.last_system = None
        self.last_user = None

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        from uri_core.core.model_providers.base import ModelResponse

        self.last_system = system
        self.last_user = user
        return ModelResponse(content="{}", model="fake", provider="fake")


def _worst_case_session_context():
    """Mirrors test_m21_prompt_budget.py's realistic 65k-character
    execution_history fixture - the single largest real prompt-bloat
    source measured during the M21 audit."""

    orchestrator = UriOrchestrator(enable_model_reasoning_shadow=False)

    history = [
        {
            "step_id": f"step_{i}",
            "capability": "retrieve_evidence",
            "status": "completed",
            "result": {"data": "y" * 1600},
        }
        for i in range(40)
    ]
    workflow = {"workflow_id": "wf1", "steps": [], "execution_history": history}
    session = SessionState(
        session_id="m21-worst-case",
        task="draft",
        active_workflow=workflow,
        current_facts={"blob": "q" * 5000},
        evidence_facts={"blob": "r" * 5000},
    )

    session_context = orchestrator._build_model_session_context(session)

    assert len(json.dumps(history)) > 65000, "fixture must mirror the real audit case"

    return session_context


class AssembledRequestFitsContextWindowTests(unittest.TestCase):
    """The CRITICAL regression check the M21 audit exists to fix."""

    def test_worst_case_reasoning_request_fits_configured_context_window(self):
        config = ModelProviderConfig.from_env()

        gateway = ModelReasoningGateway()
        request = gateway.build_reasoning_request(
            user_text=(
                "Find the emails from the registrar about the extension "
                "request and draft a reply."
            ),
            session_context=_worst_case_session_context(),
            evidence_context={},
            query_context={
                "identity": "",
                "soul": "",
                "personalization": {"preferences": ["formal tone"]},
                "session": {},
                "verified_facts": {},
                "capabilities": [],
                "diagnostics": {
                    "last_operation": {},
                    "recent_events": [],
                    "known_gaps": [],
                },
                "experience": [],
                "attachments": [],
            },
        )
        request_json = json.dumps(request, ensure_ascii=False)

        capturing = _CapturingProvider()
        adapter = OllamaReasoningAdapter(provider=capturing)
        adapter(request_json)

        self.assertIsNotNone(capturing.last_system)
        self.assertIsNotNone(capturing.last_user)

        transmitted_tokens = estimate_tokens(
            capturing.last_system
        ) + estimate_tokens(capturing.last_user)

        self.assertLess(
            transmitted_tokens,
            config.context_tokens,
            f"assembled request (~{transmitted_tokens} estimated tokens) "
            f"does not fit the configured context window "
            f"(context_tokens={config.context_tokens}) - this is the exact "
            "silent-truncation defect the M21 audit found.",
        )

    def test_system_policy_appears_once_not_duplicated(self):
        # M21: system_policy must move into `system` and be emptied out of
        # the transmitted `user` JSON, never sent in both places - see
        # model_reasoning_adapter.py's M21 comment (measured at 58.8% of
        # one real reasoning payload when duplicated).
        gateway = ModelReasoningGateway()
        policy_text = gateway.load_policy()
        self.assertTrue(
            policy_text.strip(), "fixture assumes a real, non-empty policy file"
        )

        request = gateway.build_reasoning_request(
            user_text="draft a reply",
            session_context={},
            evidence_context={},
            query_context={},
        )
        request_json = json.dumps(request, ensure_ascii=False)

        capturing = _CapturingProvider()
        adapter = OllamaReasoningAdapter(provider=capturing)
        adapter(request_json)

        # A short, distinctive slice of the real policy text - present in
        # `system` (where it now lives) but absent from `user` (where it
        # used to be duplicated).
        marker = policy_text.strip()[:80]
        self.assertIn(marker, capturing.last_system)
        self.assertNotIn(marker, capturing.last_user)

    def test_execution_history_no_longer_dominates_the_request(self):
        session_context = _worst_case_session_context()
        history_size = len(
            json.dumps(
                session_context["active_workflow"]["execution_history"],
                ensure_ascii=False,
            )
        )
        total_size = len(json.dumps(session_context, ensure_ascii=False))

        # Before M21, execution_history alone (65,634 chars in the real
        # measured session) vastly exceeded the entire rest of the
        # request. After bounding, it must be a small, bounded slice of
        # the (also-bounded) session context - never the dominant part.
        self.assertLess(history_size, 5000)
        self.assertLess(history_size, total_size)


class CapabilitiesEndpointReportsRealContextWindowTests(unittest.TestCase):
    """GET /capabilities must report the real, configured context window
    (M21 item 1's last requirement) - not the previous hardcoded None."""

    def test_capabilities_context_window_matches_configured_reasoning_role(self):
        from unittest.mock import MagicMock, patch

        from fastapi.testclient import TestClient

        from uri_core.app import server
        from uri_core.config.model_roles import ROLE_REASONING, build_provider

        expected_context_tokens = build_provider(ROLE_REASONING).config.context_tokens

        client = TestClient(server.app)

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=MagicMock(status_code=200, json=lambda: {"models": []}),
        ):
            response = client.get("/capabilities")

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(
            body["model"]["context_window"], expected_context_tokens
        )


if __name__ == "__main__":
    unittest.main()
