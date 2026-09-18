"""scripts/m32_latency_profile.py — M32 D6.

Committed, reproducible latency/resource benchmark harness for URI's
Brain execution path (Batches A-C, D1-D5). Promotes the ad-hoc,
scratchpad-only script the original M32_LATENCY_DIAGNOSTIC_REPORT.md
and M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §7's own D6 charter
both named as a "promote to a committed, repeatable harness" item,
never previously committed to the repository - this script IS that
promotion, not a new, separate tool.

Measures against the REAL, unmocked execution stack (ApprovalGate,
ToolDispatcher, CapabilityRegistry, MultiActionDispatch, ModelRouter,
build_provider, run_native_tool_loop, stream_first_turn) - only the
Gmail SERVICE backend is faked (FakeGmailService, the same fixture
test_m32_c2_c3_native_tool_loop.py already uses for its own real,
committed regression tests), never the gate/dispatch/audit chain
itself.

Two measurement modes, run together:

  1. STRUCTURAL counts - a scripted, deterministic fake model_callable,
     zero real inference. Exact, network-noise-free counts: model calls
     per turn, CapabilityDirectory constructions per turn. Mirrors the
     D1/D2 report's own "scripted fake model, exact call counting"
     methodology (m32_d_root_cause2.py, not committed at the time).

  2. REAL-MODEL timing - the real ModelRouter against whatever model
     OLLAMA_MODEL / uri_workspace/model_roles.json actually resolves to
     on THIS machine - never a model name hardcoded here (see M32 D3's
     standing lesson: never hardcode this machine's installed models).
     Skipped, honestly, with a clear message, if that model cannot be
     reached at all - the rest of the harness (structural counts,
     dispatch-only sections) still runs and is still useful.

Usage (from repo root, with the project venv active and Ollama
running):

    python scripts/m32_latency_profile.py

Set OLLAMA_MODEL to a model actually installed on this machine with
tool-calling support (e.g. `OLLAMA_MODEL=gemma4:12b python ...`) if the
deployment default is not installed here - the SAME operator action
D3's own report recommends, not something this script decides for you.

This script makes NO production code changes and is safe to re-run
against any future milestone as the recorded baseline. Never edit
production code merely to make this script's numbers look better - if
a number is bad, fix the code and let a fresh run of this script prove
the fix, in a separate, reviewed change.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import requests

from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.model_providers.base import (
    ModelResponse,
    ProviderError,
    ToolCall,
)
from uri_core.core.model_providers.ollama_provider import OllamaProvider
from uri_core.core.model_providers.base import ModelProviderConfig
from uri_core.core.model_router import get_router
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from uri_core.core.native_tool_loop import (
    DEFAULT_MAX_PARALLEL_TOOL_WORKERS,
    MAX_PARALLEL_TOOL_WORKERS_ENV_VAR,
    ROLE_NATIVE_TOOL_LOOP,
    run_native_tool_loop,
)
from uri_core.core.state import SessionManager
from uri_core.core.stream_tool_loop import (
    DEFAULT_MAX_CONCURRENT_STREAMS,
    MAX_CONCURRENT_STREAMS_ENV_VAR,
    stream_first_turn,
)

sys.path.insert(0, _REPO_ROOT)  # test_multi_action_capabilities.py lives at repo root
from test_multi_action_capabilities import FakeGmailService  # noqa: E402

WARM_ITERATIONS = 10  # raised from 5 after the multi-tool scenario's 12-iteration re-run
# (2026-09-18) showed 5 was too few to distinguish real variance from a
# possible regression - see M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §15.8.
RESULTS: Dict[str, Any] = {"structural": {}, "real_model": {}, "notes": {}}


# ---------------------------------------------------------------------
# Fixture (mirrors test_m32_c2_c3_native_tool_loop.py's own _Fixture -
# real collaborators throughout, only the Gmail backend is faked)
# ---------------------------------------------------------------------

def make_orchestrator(connected_gmail: bool = True) -> SimpleNamespace:
    tmp = tempfile.mkdtemp()
    cap_registry = CapabilityRegistry()
    dispatcher = ToolDispatcher()
    approval_gate = ApprovalGate(
        dispatcher=dispatcher, capability_registry=cap_registry,
        approval_store=ApprovalStore(storage_path=os.path.join(tmp, "approvals.json")),
    )
    gmail_registry = MultiActionCapabilityRegistry(
        [GmailCapability(FakeGmailService(connected=connected_gmail))]
    )
    mad = MultiActionDispatch(
        registry=gmail_registry, capability_registry=cap_registry,
        permission_checker=lambda *_: True,
    )
    session_manager = SessionManager(storage_path=os.path.join(tmp, "sessions"))
    return SimpleNamespace(
        session_manager=session_manager, capability_registry=cap_registry,
        multi_action_dispatch=mad, approval_gate=approval_gate, conversation_history=None,
    )


def counting_directory_init():
    """Wraps CapabilityDirectory.__init__ to count real constructions,
    without disabling construction - the real object is still built,
    only the count is observed (mirrors D2DirectoryReuseTests)."""
    original_init = CapabilityDirectory.__init__
    calls = {"n": 0}

    def counting_init(self, *args, **kwargs):
        calls["n"] += 1
        return original_init(self, *args, **kwargs)

    return calls, counting_init


def median_min_max(values: List[float]) -> Dict[str, float]:
    return {
        "median": round(statistics.median(values), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "n": len(values),
    }


# ---------------------------------------------------------------------
# SECTION 1: structural counts - scripted fake model, exact, no network
# ---------------------------------------------------------------------

def _scripted_model(responses: List[ModelResponse], call_counter: Dict[str, int]) -> Callable[..., Any]:
    it = iter(responses)

    def _call(*, system: str, user: str, tools=None):
        call_counter["n"] += 1
        return next(it)

    return _call


def run_structural_section() -> None:
    print("=== SECTION 1: structural counts (scripted fake model, exact, no network) ===")
    scenarios = {
        "tier0_no_tool": [
            ModelResponse(content="Paris.", model="fake", provider="fake"),
        ],
        "tier1_legacy_remember_fact": [
            ModelResponse(
                content="", model="fake", provider="fake",
                tool_calls=(ToolCall(id="c1", name="remember_fact", arguments={"request_text": "office is room 204"}),),
            ),
            ModelResponse(content="Noted.", model="fake", provider="fake"),
        ],
        "tier1_native_single_gmail": [
            ModelResponse(
                content="", model="fake", provider="fake",
                tool_calls=(ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "renewal"}),),
            ),
            ModelResponse(content="Found it.", model="fake", provider="fake"),
        ],
        "multi_tool_two_branch": [
            ModelResponse(
                content="", model="fake", provider="fake",
                tool_calls=(
                    ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "renewal"}),
                    ToolCall(id="c2", name="gmail_search_messages", arguments={"query": "invoice"}),
                ),
            ),
            ModelResponse(content="Found both.", model="fake", provider="fake"),
        ],
    }

    for label, responses in scenarios.items():
        orchestrator = make_orchestrator(connected_gmail=True)
        calls, counting_init = counting_directory_init()
        call_counter = {"n": 0}
        model_callable = _scripted_model(responses, call_counter)

        with patch.object(CapabilityDirectory, "__init__", counting_init):
            result = run_native_tool_loop(
                orchestrator=orchestrator, session_id=f"struct-{label}", user_text="probe",
                principal=None, model_callable=model_callable,
            )

        entry = {
            "model_calls": call_counter["n"],
            "capability_directory_constructions": calls["n"],
            "tier": result["tier"] if result else None,
            "status": result.get("status") if result else None,
        }
        RESULTS["structural"][label] = entry
        print(f"  {label}: model_calls={entry['model_calls']} "
              f"capability_directory_constructions={entry['capability_directory_constructions']} "
              f"tier={entry['tier']}")
    print()


# ---------------------------------------------------------------------
# SECTION 2: real-model availability check
# ---------------------------------------------------------------------

def real_model_available() -> Optional[str]:
    """Returns None if reachable, else a short reason string. Never
    guesses a model name of its own - uses whatever ModelProviderConfig.
    from_env() already resolves to (OLLAMA_MODEL env override, else the
    packaged default), exactly like production."""
    try:
        provider = OllamaProvider(config=ModelProviderConfig.from_env())
        status = provider.describe()
        if not status.available:
            return f"Ollama server unreachable: {status.detail}"
        provider.complete(system="Reply with one word.", user="ping", max_tokens=5)
        return None
    except ProviderError as exc:
        return f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"


def evict_model(config: ModelProviderConfig) -> None:
    """Forces Ollama to unload the model (keep_alive: 0), so the NEXT
    call is a genuine cold load - confirmed live: done_reason: "unload"
    in the response, and the following call measured ~12s vs ~0.2s warm
    on this machine."""
    try:
        requests.post(
            f"{config.base_url.rstrip('/')}/api/generate",
            json={"model": config.model, "keep_alive": 0},
            timeout=30,
        )
    except requests.exceptions.RequestException:
        pass


# ---------------------------------------------------------------------
# SECTION 3: real-model cold + warm timing
# ---------------------------------------------------------------------

def timed_real_turn(orchestrator, session_id: str, user_text: str) -> Dict[str, Any]:
    router = get_router()
    model_time = {"seconds": 0.0}
    call_count = {"n": 0}

    def model_callable(*, system, user, tools):
        call_count["n"] += 1
        t0 = time.monotonic()
        resp = router.attempt(ROLE_NATIVE_TOOL_LOOP, None, system=system, user=user, tools=tools, max_tokens=400)
        model_time["seconds"] += time.monotonic() - t0
        return resp

    t0 = time.monotonic()
    result = run_native_tool_loop(
        orchestrator=orchestrator, session_id=session_id, user_text=user_text,
        principal=None, model_callable=model_callable,
    )
    total = time.monotonic() - t0
    return {
        "total_seconds": total,
        "model_seconds": model_time["seconds"],
        "uri_overhead_seconds": total - model_time["seconds"],
        "model_calls": call_count["n"],
        "tier": result["tier"] if result else None,
        "status": result.get("status") if result else None,
    }


def run_real_model_section(config: ModelProviderConfig) -> None:
    print("=== SECTION 2/3: real-model timing (cold, then warm x%d) ===" % WARM_ITERATIONS)

    # --- cold: force eviction, one Tier 0 turn, recorded separately ---
    evict_model(config)
    orchestrator = make_orchestrator(connected_gmail=True)
    cold = timed_real_turn(orchestrator, "cold-tier0", "What is the capital of France?")
    RESULTS["real_model"]["cold_tier0"] = cold
    print(f"  COLD tier0: total={cold['total_seconds']:.3f}s model={cold['model_seconds']:.3f}s "
          f"overhead={cold['uri_overhead_seconds']:.3f}s")

    scenarios = {
        "tier0_no_tool": "What is the capital of France?",
        "tier1_legacy_remember_fact": "Remember that my office is room 204.",
        "tier1_native_single_gmail": "Search my Gmail for messages about renewal.",
        # Matches D1+D2's own original multi-tool scenario text verbatim
        # (M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §10.4) - keep
        # this identical to that baseline's wording so every future run
        # of this script stays a true apples-to-apples comparison. An
        # earlier D6 run used different wording ("search twice") here,
        # which produced a real ~40% higher total that turned out to be
        # explained entirely by the different prompt content, not a
        # regression - confirmed by re-running with this exact text.
        "multi_tool_two_branch": "Search my Gmail for messages about the quarterly renewal, then read the first result.",
    }

    for label, text in scenarios.items():
        totals, models, overheads = [], [], []
        for i in range(WARM_ITERATIONS):
            orchestrator = make_orchestrator(connected_gmail=True)
            r = timed_real_turn(orchestrator, f"warm-{label}-{i}", text)
            totals.append(r["total_seconds"])
            models.append(r["model_seconds"])
            overheads.append(r["uri_overhead_seconds"])

        entry = {
            "total_seconds": median_min_max(totals),
            "model_seconds": median_min_max(models),
            "uri_overhead_seconds": median_min_max(overheads),
        }
        RESULTS["real_model"][label] = entry
        print(f"  WARM {label}: total median={entry['total_seconds']['median']:.3f}s "
              f"(min={entry['total_seconds']['min']:.3f}s max={entry['total_seconds']['max']:.3f}s) "
              f"model median={entry['model_seconds']['median']:.3f}s "
              f"overhead median={entry['uri_overhead_seconds']['median']:.3f}s")
    print()


# ---------------------------------------------------------------------
# SECTION 4: streaming TTFT
# ---------------------------------------------------------------------

def run_streaming_section() -> None:
    print("=== SECTION 4: streaming TTFT (warm x%d) ===" % WARM_ITERATIONS)
    ttfts, totals = [], []
    for i in range(WARM_ITERATIONS):
        orchestrator = make_orchestrator(connected_gmail=True)
        t0 = time.monotonic()
        events = list(stream_first_turn(
            orchestrator=orchestrator, session_id=f"stream-ttft-{i}",
            user_text="Say hello in exactly five words.", principal=None,
        ))
        total = time.monotonic() - t0
        done = events[-1]
        if done.kind == "done" and done.ttft_seconds is not None:
            ttfts.append(done.ttft_seconds)
            totals.append(total)

    if ttfts:
        entry = {"ttft_seconds": median_min_max(ttfts), "total_seconds": median_min_max(totals)}
        RESULTS["real_model"]["streaming_ttft"] = entry
        print(f"  TTFT median={entry['ttft_seconds']['median']:.3f}s "
              f"(min={entry['ttft_seconds']['min']:.3f}s max={entry['ttft_seconds']['max']:.3f}s), "
              f"total median={entry['total_seconds']['median']:.3f}s")
    else:
        RESULTS["notes"]["streaming_ttft"] = "no successful streamed turn - see real_model availability check"
        print("  SKIPPED - no successful streamed turn")
    print()


# ---------------------------------------------------------------------
# SECTION 5: approval/dispatch overhead (isolated, no model call)
# ---------------------------------------------------------------------

def run_approval_section() -> None:
    print("=== SECTION 5: approval/grants/audit dispatch overhead (isolated, no model call) ===")
    orchestrator = make_orchestrator(connected_gmail=True)
    durations = []
    for i in range(WARM_ITERATIONS):
        t0 = time.monotonic()
        result = orchestrator.approval_gate.execute_tool("system_performance", session_id=f"appr-{i}")
        durations.append(time.monotonic() - t0)
    entry = median_min_max(durations)
    RESULTS["real_model"]["approval_dispatch_overhead"] = entry
    RESULTS["notes"]["approval_dispatch_overhead_caveat"] = (
        "'system_performance' (the probe tool used above) deliberately blocks for "
        "~0.2s per call in its OWN business logic (psutil.cpu_percent(interval=0.2), "
        "uri_core/tools/system_performance.py) - a real CPU-sampling window, not "
        "ApprovalGate/ToolDispatcher/AuditTrail overhead. The pure gate/dispatch/audit "
        "cost is therefore closer to (median - 0.2s), not the raw median above. Disclosed "
        "here rather than silently attributing a tool's own sampling delay to framework "
        "overhead."
    )
    RESULTS["notes"]["approval_resume"] = (
        "The dispatch/grants/audit overhead for a zero-approval-required tool is measured "
        "above. A genuine approval-REQUIRED round trip (propose -> ApprovalStore persist -> "
        "separate later POST /approve -> ApprovalGate.decide()) spans two separate HTTP "
        "requests with a real human decision in between; the human-decision interval is not "
        "a system latency and is not measured. The system-side halves (the initial dispatch "
        "that reaches 'requires approval', and decide()'s own post-approval execute) are the "
        "same ApprovalGate/ToolDispatcher/AuditTrail code path measured here for the "
        "zero-approval case - no separate code path exists for the approval-required case "
        "that this harness has not already exercised."
    )
    print(f"  median={entry['median']:.4f}s (min={entry['min']:.4f}s max={entry['max']:.4f}s)")
    print()


# ---------------------------------------------------------------------
# SECTION 6: concurrency/resource + OAuth notes (structural, no timing)
# ---------------------------------------------------------------------

def run_notes_section() -> None:
    print("=== SECTION 6: concurrency/resource + OAuth notes (structural) ===")
    parallel_cap = os.environ.get(MAX_PARALLEL_TOOL_WORKERS_ENV_VAR)
    stream_cap = os.environ.get(MAX_CONCURRENT_STREAMS_ENV_VAR)
    RESULTS["notes"]["parallel_tool_worker_cap"] = (
        f"Bounded since D4: default {DEFAULT_MAX_PARALLEL_TOOL_WORKERS}, "
        f"env-configurable via {MAX_PARALLEL_TOOL_WORKERS_ENV_VAR} "
        f"(currently {'unset -> default' if parallel_cap is None else parallel_cap}). "
        "Before D4 this was unbounded (max_workers=len(eligible))."
    )
    RESULTS["notes"]["concurrent_stream_cap"] = (
        f"Bounded since D5: default {DEFAULT_MAX_CONCURRENT_STREAMS}, "
        f"env-configurable via {MAX_CONCURRENT_STREAMS_ENV_VAR} "
        f"(currently {'unset -> default' if stream_cap is None else stream_cap})."
    )
    RESULTS["notes"]["oauth_refresh"] = (
        "Not measurable in this environment - no real Google OAuth credential is configured "
        "here (Gmail is exercised via FakeGmailService in this harness, as in the committed "
        "test suite). D1's persist-after-refresh fix is unit-tested "
        "(test_gmail_connection_truth.py::LoadUsableCredentialsTests) and unchanged since "
        "D1 - nothing in D2-D5 touched google_auth_common.py. See "
        "M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §10.4 for D1's own real before/after "
        "(.refresh() call count 1 -> still 1 on a persisted-valid token)."
    )
    print(f"  {RESULTS['notes']['parallel_tool_worker_cap']}")
    print(f"  {RESULTS['notes']['concurrent_stream_cap']}")
    print(f"  {RESULTS['notes']['oauth_refresh']}")
    print()


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    run_structural_section()

    config = ModelProviderConfig.from_env()
    reason = real_model_available()
    if reason is not None:
        RESULTS["notes"]["real_model_skipped"] = (
            f"Real-model sections skipped: {reason}. Set OLLAMA_MODEL to a model actually "
            "installed on this machine (see M32 D3) and ensure Ollama is running, then re-run."
        )
        print(f"!! Real-model sections SKIPPED: {reason}")
        print(f"   Configured model: {config.model} @ {config.base_url}")
        print()
    else:
        run_real_model_section(config)
        run_streaming_section()

    run_approval_section()
    run_notes_section()

    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "m32_latency_profile_results.json")
    with open(results_path, "w", encoding="utf-8") as handle:
        json.dump(RESULTS, handle, indent=2)
    print(f"Results written to {results_path}")


if __name__ == "__main__":
    main()
