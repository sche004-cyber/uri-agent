"""M33 P2 verification-only evidence pass. Not a permanent test - a
scripted, reproducible live-evidence capture, mirroring D6's own
`scripts/m32_latency_profile.py` convention.

Exercises the REAL, running FastAPI app (`uri_core.app.server.app`)
through `TestClient`, using the SAME ambient-globals real-orchestrator
construction `test_m32_c_server_wiring.py` already relies on (no
Authorization header - no orchestrator/context mocking of any kind).
`run_canonical_for_ask` and `UriOrchestrator.process_user_input` are
wrapped with `unittest.mock.patch(..., wraps=<the real function>)` -
they still execute their real bodies; the wrap only lets this script
observe whether and how many times each was actually called for a
real turn against a real local model (Ollama, confirmed reachable
before running this script).

Records results only. Makes no production-code change.
"""
from __future__ import annotations

import os
import sys
import uuid
from unittest.mock import patch

sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core import canonical_execution
from uri_core.core.canonical_execution import (
    ALLOWLIST_ENV_VAR,
    LIVE_ENV_VAR,
    canonical_killswitch_enabled,
    decision_engine_live_enabled,
)
from uri_core.core.native_tool_loop import TOOL_LOOP_ENV_VAR, native_tool_loop_enabled
from uri_core.core.orchestrator import UriOrchestrator


def _reset_flags():
    os.environ.pop(LIVE_ENV_VAR, None)
    os.environ.pop(ALLOWLIST_ENV_VAR, None)
    os.environ.pop(TOOL_LOOP_ENV_VAR, None)


client = TestClient(server.app)

print("=== TASK 3: confirm canonical default-on behavior with flags unset ===")
_reset_flags()
print(f"{LIVE_ENV_VAR} unset -> decision_engine_live_enabled() = {decision_engine_live_enabled()}")
assert decision_engine_live_enabled() is True
print(f"{TOOL_LOOP_ENV_VAR} unset -> native_tool_loop_enabled() = {native_tool_loop_enabled()}")
assert native_tool_loop_enabled() is False
print(f"{ALLOWLIST_ENV_VAR} unset -> canonical_killswitch_enabled() = {canonical_killswitch_enabled()}")
assert canonical_killswitch_enabled() is False
print("TASK 3: PASS - canonical is default-on, native_tool_loop is default-off, "
      "no killswitch active, purely from unset flags.\n")


print("=== TASK 1a: live-demonstrate killswitch via EMPTY allowlist ===")
_reset_flags()
os.environ[ALLOWLIST_ENV_VAR] = ""
session_id = f"p2-evidence-{uuid.uuid4()}"
with patch(
    "uri_core.core.canonical_execution.run_canonical_for_ask", wraps=canonical_execution.run_canonical_for_ask
) as spy_canonical, patch(
    "uri_core.core.orchestrator.UriOrchestrator.process_user_input",
    wraps=UriOrchestrator.process_user_input,
    autospec=True,
) as spy_legacy:
    response = client.post("/ask", json={"session_id": session_id, "text": "Hello, how are you?"})
print(f"HTTP status: {response.status_code}")
print(f"run_canonical_for_ask call count: {spy_canonical.call_count}")
print(f"process_user_input call count: {spy_legacy.call_count}")
assert response.status_code == 200
assert spy_canonical.call_count == 0, "canonical must never be reached when the killswitch is active"
assert spy_legacy.call_count == 1, "legacy must serve the turn when the killswitch is active"
print("TASK 1a: PASS - empty allowlist killswitch bypasses canonical entirely; legacy served the real turn.\n")


print("=== TASK 1b: live-demonstrate killswitch via a NARROW (non-matching) allowlist ===")
_reset_flags()
os.environ[ALLOWLIST_ENV_VAR] = "Gmail,remember_fact"
session_id = f"p2-evidence-{uuid.uuid4()}"
with patch(
    "uri_core.core.canonical_execution.run_canonical_for_ask", wraps=canonical_execution.run_canonical_for_ask
) as spy_canonical, patch(
    "uri_core.core.orchestrator.UriOrchestrator.process_user_input",
    wraps=UriOrchestrator.process_user_input,
    autospec=True,
) as spy_legacy:
    response = client.post("/ask", json={"session_id": session_id, "text": "Hello, how are you?"})
print(f"HTTP status: {response.status_code}")
print(f"run_canonical_for_ask call count: {spy_canonical.call_count}")
print(f"process_user_input call count: {spy_legacy.call_count}")
assert response.status_code == 200
assert spy_canonical.call_count == 0, "ANY configured allowlist is a full killswitch at the server.py layer"
assert spy_legacy.call_count == 1
print(
    "TASK 1b: PASS - confirms `canonical_killswitch_enabled()`'s own contract: a NARROW allowlist "
    "is still treated as a full kill switch at server.py's outer gate, not a per-capability "
    "narrowing of live /ask traffic. `is_allowlisted()`'s own finer-grained narrowing (tested at "
    "the unit level in test_canonical_execution.py) is real code but is not reached through a live "
    "/ask call while ANY allowlist is configured - this matches `canonical_killswitch_enabled()`'s "
    "own docstring ('any concrete set... is an explicit request for legacy-first route handling') "
    "exactly. Documented here as an accurate characterization, not a defect.\n"
)


print("=== TASK 2: dedicated live observation - real default /ask -> run_canonical_for_ask, native_tool_loop disabled ===")
print("Provider: LM Studio (openai_compatible adapter), model qwen3-14b, via a real authenticated "
      "user's Active Brain config - not the anonymous ambient path, since build_provider() requires "
      "a real principal for any non-ollama provider. Nothing hardcoded in production code: the "
      "provider/model selection is a per-user config-store write (ProviderConfigStore.set_active_brain), "
      "the API key is a per-user encrypted key-store write (ProviderKeyStore.set_key), and the local "
      "API key value itself comes from the LM_STUDIO_LOCAL_KEY env var, never written into this file.")
_reset_flags()

lm_studio_key = os.environ.get("LM_STUDIO_LOCAL_KEY")
assert lm_studio_key, "LM_STUDIO_LOCAL_KEY must be set in the environment before running this script"
os.environ.setdefault("URI_PROVIDER_KEY_SECRET", f"p2-evidence-secret-{uuid.uuid4()}")

from uri_core.core.provider_registry import ProviderConfigStore
from uri_core.core.provider_keys import ProviderKeyStore

username = f"p2-evidence-{uuid.uuid4().hex[:12]}"
signup_response = client.post(
    "/auth/signup", json={"username": username, "password": "P2-Evidence-Pass-1!"}
)
assert signup_response.status_code == 200, f"signup failed: {signup_response.status_code} {signup_response.text}"
signup_body = signup_response.json()
lm_user_id = signup_body["user_id"]
lm_token = signup_body["token"]
print(f"Signed up real test user (user_id={lm_user_id}) for this evidence run only.")

ProviderConfigStore(lm_user_id).set_active_brain("lm_studio", "qwen3-14b")
ProviderKeyStore(lm_user_id).set_key("lm_studio", lm_studio_key)
lm_studio_key = None  # noqa: S105 - erase local reference once stored
print("Active Brain set to lm_studio/qwen3-14b and LM Studio key stored, both via the existing "
      "per-user config/key stores - no production code touched.")

session_id = f"p2-evidence-{uuid.uuid4()}"
assert native_tool_loop_enabled() is False
with patch(
    "uri_core.core.canonical_execution.run_canonical_for_ask", wraps=canonical_execution.run_canonical_for_ask
) as spy_canonical, patch(
    "uri_core.core.orchestrator.UriOrchestrator.process_user_input",
    wraps=UriOrchestrator.process_user_input,
    autospec=True,
) as spy_legacy:
    response = client.post(
        "/ask",
        json={"session_id": session_id, "text": "Hello, how are you?"},
        headers={"Authorization": f"Bearer {lm_token}"},
    )
body = response.json()
print(f"HTTP status: {response.status_code}")
print(f"run_canonical_for_ask call count: {spy_canonical.call_count}")
print(f"process_user_input call count: {spy_legacy.call_count}")
print(f"response status: {body.get('status')}")
print(f"response message (truncated): {str(body.get('response'))[:300]}")
assert response.status_code == 200
assert spy_canonical.call_count == 1, "canonical must be the real default path with flags unset"
assert body.get("status") != "unavailable", (
    "the model provider must genuinely answer this turn, not fail closed - "
    "an 'unavailable' status here means LM Studio was not actually reached"
)
print(
    "TASK 2: PASS - a real /ask turn, over a real local model (LM Studio, qwen3-14b), with no "
    "canonical/killswitch/tool-loop flags set and native_tool_loop off (its own default), was "
    "served by run_canonical_for_ask, and the model genuinely answered (status != 'unavailable'). "
    f"process_user_input (legacy) call count: {spy_legacy.call_count} "
    "(0 means canonical's own terminal envelope answered the turn directly; "
    "any value >0 means canonical itself internally decided to fall back for this specific turn).\n"
)

print("=== ALL TASKS COMPLETE ===")
