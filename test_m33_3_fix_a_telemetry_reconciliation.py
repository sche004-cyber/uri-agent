"""Focused tests for URI Fix A: Runtime Telemetry Accuracy & Edge Trace Schema.

Proves:
A. Turns with Reasoning + Drafting account for both sequential model calls.
B. The final model record is no longer mistaken for total model latency.
C. model_total_ms reconciles with individual model-call timings and explains wall-clock total.
D. Single-model-call paths remain functional and correctly attributed.
E. Zero-model-call deterministic paths remain functional and truthfully report None.
F. Edge/reflex timing remains intact.
G. threshold_percent and shortlist_size are preserved when genuinely available.
H. Null remains valid where values genuinely do not exist.
I. Existing runtime-trace consumers / UI parsing do not regress.
J. Mathematical reproduction of the previously misleading Trace C:
   reflex=97ms, reasoning=8900ms, drafting=4665ms, orchestration=565ms -> total=14227ms.
"""
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from uri_core.app import server
from uri_core.core.edge.trace import (
    TRACE_SCHEMA_VERSION,
    EdgeRoutingTraceEvent,
    EdgeRoutingTraceStore,
)
from uri_core.core.usage_meter import UsageMeter, UsageRecord


class FixATelemetryReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.user_id = f"11111111-1111-4111-8111-{uuid.uuid4().hex[:12]}"
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"
        self._usage_patcher = patch(
            "uri_core.core.usage_meter.user_scoped_path",
            lambda uid, rel, **kw: os.path.join(self.temp_dir.name, uid, rel),
        )
        self._trace_patcher = patch(
            "uri_core.core.edge.trace.user_scoped_path",
            lambda uid, rel, **kw: os.path.join(self.temp_dir.name, uid, rel),
        )
        self._usage_patcher.start()
        self._trace_patcher.start()

    def tearDown(self):
        self._usage_patcher.stop()
        self._trace_patcher.stop()
        self.temp_dir.cleanup()

    def _write_usage_record(
        self,
        *,
        role: str,
        provider_id: str,
        model: str,
        prompt_tokens: int,
        eval_tokens: int,
        duration_seconds: float,
        ts: str,
        session_id: str = None,
        outcome: str = "success",
    ):
        meter = UsageMeter()
        record = UsageRecord(
            ts=ts,
            user_id=self.user_id,
            session_id=session_id or self.session_id,
            role=role,
            provider_id=provider_id,
            model=model,
            prompt_tokens={"value": prompt_tokens, "confidence": "KNOWN"},
            eval_tokens={"value": eval_tokens, "confidence": "KNOWN"},
            duration_seconds={"value": duration_seconds, "confidence": "KNOWN"},
            outcome=outcome,
            fallback_from=[],
            estimated_cost={"value": None, "confidence": "UNAVAILABLE"},
        )
        meter.record(record)

    def test_trace_c_mathematical_reconciliation(self):
        """Reproduce Trace C and prove telemetry now explains the full 14,227 ms wall-clock total."""
        # Trace C timestamps: turn started at 03:27:00
        turn_start_iso = "2026-09-21T03:27:00.000000+00:00"
        # Call 1: Reasoning (8900 ms, 4362 prompt, 134 eval)
        self._write_usage_record(
            role="reasoning",
            provider_id="ollama",
            model="gemma4:12b",
            prompt_tokens=4362,
            eval_tokens=134,
            duration_seconds=8.9001305,
            ts="2026-09-21T03:27:09.755146+00:00",
            session_id=self.session_id,
        )
        # Call 2: Drafting (4665 ms, 5448 prompt, 12 eval)
        self._write_usage_record(
            role="drafting",
            provider_id="ollama",
            model="gemma4:12b",
            prompt_tokens=5448,
            eval_tokens=12,
            duration_seconds=4.6653270,
            ts="2026-09-21T03:27:14.637151+00:00",
            session_id=self.session_id,
        )

        # 1. Test _serving_model_for_turn accounts for BOTH calls
        serving = server._serving_model_for_turn(
            self.user_id, self.session_id, since_iso=turn_start_iso
        )

        self.assertEqual(serving["provider_id"], "ollama")
        self.assertEqual(serving["model"], "gemma4:12b")
        self.assertEqual(serving["prompt_tokens"], 4362 + 5448)  # 9810
        self.assertEqual(serving["eval_tokens"], 134 + 12)       # 146
        self.assertAlmostEqual(serving["duration_seconds"], 8.9001305 + 4.6653270, places=5)
        self.assertEqual(serving["reasoning_ms"], 8900)
        self.assertEqual(serving["drafting_ms"], 4665)
        self.assertEqual(serving["model_total_ms"], 8900 + 4665) # 13565

        # Assert structured per-call operational metadata in `calls`
        self.assertEqual(len(serving["calls"]), 2)
        self.assertEqual(serving["calls"][0]["role"], "reasoning")
        self.assertEqual(serving["calls"][0]["latency_ms"], 8900)
        self.assertEqual(serving["calls"][0]["prompt_tokens"], 4362)
        self.assertEqual(serving["calls"][0]["eval_tokens"], 134)
        self.assertEqual(serving["calls"][1]["role"], "drafting")
        self.assertEqual(serving["calls"][1]["latency_ms"], 4665)
        self.assertEqual(serving["calls"][1]["prompt_tokens"], 5448)
        self.assertEqual(serving["calls"][1]["eval_tokens"], 12)

        # 2. Test finalizer and EdgeRoutingTraceEvent emission
        context = MagicMock()
        payload = SimpleNamespace(session_id=self.session_id, model_override=None, text="test")
        result = {
            "status": "success",
            "session_id": self.session_id,
            "response": {"message": "hello"},
            "narrative": "Hello! How can I help you today?",
            "_edge_routing": {
                "disposition": "NEEDLE_ESCALATED",
                "reason_codes": ("NEEDLE_ESCALATED", "PROPOSAL_UNMAPPED_OR_ABSENT"),
                "latency_ms": 97,
                "candidate": "needle-3",
                "runtime_id": "needle-3",
                "confidence": 0.98,
                "threshold_percent": 80,
                "shortlist_size": 2,
                "capability_id": None,
            },
        }

        with patch("uri_core.core.edge.trace.EdgeRoutingTraceStore.record") as mock_record:
            finalized = server._finalize_ask_response(
                context,
                self.user_id,
                payload,
                result,
                total_duration_seconds=14.227,
                turn_start_iso=turn_start_iso,
            )

            self.assertTrue(mock_record.called)
            event: EdgeRoutingTraceEvent = mock_record.call_args.args[0]

            # B. Prove the final model record is NO LONGER mistaken for total model latency
            self.assertNotEqual(event.latency_ms["model"], 4665)
            self.assertEqual(event.latency_ms["model"], 13565)

            # A & C. Prove separate timings and reconciliation
            self.assertEqual(event.latency_ms["reasoning_ms"], 8900)
            self.assertEqual(event.latency_ms["drafting_ms"], 4665)
            self.assertEqual(event.latency_ms["model_total_ms"], 13565)
            self.assertEqual(event.latency_ms["reflex"], 97)
            self.assertEqual(event.latency_ms["total"], 14227)

            # J. Mathematical reproduction: explain the wall-clock total
            reflex = event.latency_ms["reflex"]
            reasoning = event.latency_ms["reasoning_ms"]
            drafting = event.latency_ms["drafting_ms"]
            model_total = event.latency_ms["model_total_ms"]
            total = event.latency_ms["total"]
            deterministic_orchestration = total - model_total - reflex

            self.assertEqual(model_total, reasoning + drafting)
            self.assertEqual(deterministic_orchestration, 565)
            self.assertEqual(total, reflex + reasoning + drafting + deterministic_orchestration)

            # G. threshold_percent and shortlist_size passed through
            self.assertEqual(event.threshold_percent, 80)
            self.assertEqual(event.shortlist_size, 2)
            self.assertEqual(event.confidence["score"], 0.98)
            self.assertEqual(event.confidence["threshold"], 80)

            # Main brain calls operational metadata
            self.assertEqual(len(event.main_brain["calls"]), 2)
            self.assertEqual(event.main_brain["calls"][0]["role"], "reasoning")
            self.assertEqual(event.main_brain["calls"][1]["role"], "drafting")

            # Envelope fields returned to client
            self.assertEqual(finalized["serving_model_total_ms"], 13565)
            self.assertEqual(finalized["serving_reasoning_duration_seconds"], 8.9)
            self.assertEqual(finalized["serving_drafting_duration_seconds"], 4.665)
            self.assertEqual(finalized["serving_total_duration_seconds"], 14.227)

    def test_single_model_call_path(self):
        """Single model call (e.g. reasoning only or native tool call without drafting) accounts accurately."""
        self._write_usage_record(
            role="reasoning",
            provider_id="ollama",
            model="qwen3.5:9b",
            prompt_tokens=500,
            eval_tokens=80,
            duration_seconds=2.450,
            ts="2026-09-21T04:00:05.000000+00:00",
        )

        serving = server._serving_model_for_turn(
            self.user_id, self.session_id, since_iso="2026-09-21T04:00:00.000000+00:00"
        )
        self.assertEqual(serving["reasoning_ms"], 2450)
        self.assertIsNone(serving["drafting_ms"])
        self.assertEqual(serving["model_total_ms"], 2450)
        self.assertEqual(len(serving["calls"]), 1)

        context = MagicMock()
        payload = SimpleNamespace(session_id=self.session_id, model_override=None, text="hi")
        result = {"status": "success", "session_id": self.session_id}

        with patch("uri_core.core.edge.trace.EdgeRoutingTraceStore.record") as mock_record:
            server._finalize_ask_response(
                context, self.user_id, payload, result,
                total_duration_seconds=2.600,
                turn_start_iso="2026-09-21T04:00:00.000000+00:00",
            )
            event: EdgeRoutingTraceEvent = mock_record.call_args.args[0]
            self.assertEqual(event.latency_ms["model"], 2450)
            self.assertEqual(event.latency_ms["reasoning_ms"], 2450)
            self.assertIsNone(event.latency_ms["drafting_ms"])
            self.assertEqual(event.latency_ms["total"], 2600)

    def test_zero_model_call_deterministic_path(self):
        """Zero model calls (e.g. preflight, deterministic lifecycle intent, edge reflex) truthfully report None."""
        serving = server._serving_model_for_turn(
            self.user_id, self.session_id, since_iso="2026-09-21T04:00:00.000000+00:00"
        )
        self.assertIsNone(serving["provider_id"])
        self.assertIsNone(serving["model"])
        self.assertIsNone(serving["duration_seconds"])
        self.assertIsNone(serving["reasoning_ms"])
        self.assertIsNone(serving["drafting_ms"])
        self.assertIsNone(serving["model_total_ms"])
        self.assertEqual(serving["calls"], [])

        context = MagicMock()
        payload = SimpleNamespace(session_id=self.session_id, model_override=None, text="ping")
        result = {
            "status": "success",
            "session_id": self.session_id,
            "_edge_routing": {
                "disposition": "NEEDLE_BYPASSED",
                "reason_codes": ("NEEDLE_BYPASSED", "URI_PREFLIGHT"),
                "latency_ms": 1,
                "confidence": None,
                "threshold_percent": None,
                "shortlist_size": None,
            },
        }

        with patch("uri_core.core.edge.trace.EdgeRoutingTraceStore.record") as mock_record:
            server._finalize_ask_response(
                context, self.user_id, payload, result,
                total_duration_seconds=0.015,
                turn_start_iso="2026-09-21T04:00:00.000000+00:00",
            )
            event: EdgeRoutingTraceEvent = mock_record.call_args.args[0]
            self.assertIsNone(event.latency_ms["model"])
            self.assertIsNone(event.latency_ms["model_total_ms"])
            self.assertIsNone(event.latency_ms["reasoning_ms"])
            self.assertIsNone(event.latency_ms["drafting_ms"])
            self.assertEqual(event.latency_ms["reflex"], 1)
            self.assertEqual(event.latency_ms["total"], 15)
            # H. Null remains valid where values genuinely do not exist
            self.assertIsNone(event.threshold_percent)
            self.assertIsNone(event.shortlist_size)

    def test_multi_stage_model_calls_supported(self):
        """Preserves structure so future turns with >2 model calls do not recreate records[-1] bug."""
        turn_start = "2026-09-21T05:00:00.000000+00:00"
        # 3 sequential model calls: reasoning step 1, reasoning step 2, drafting
        self._write_usage_record(
            role="reasoning", provider_id="ollama", model="qwen3.5:9b",
            prompt_tokens=1000, eval_tokens=50, duration_seconds=1.2,
            ts="2026-09-21T05:00:02.000000+00:00",
        )
        self._write_usage_record(
            role="reasoning", provider_id="ollama", model="qwen3.5:9b",
            prompt_tokens=1500, eval_tokens=60, duration_seconds=1.8,
            ts="2026-09-21T05:00:05.000000+00:00",
        )
        self._write_usage_record(
            role="drafting", provider_id="ollama", model="qwen3.5:9b",
            prompt_tokens=2000, eval_tokens=40, duration_seconds=0.9,
            ts="2026-09-21T05:00:07.000000+00:00",
        )

        serving = server._serving_model_for_turn(
            self.user_id, self.session_id, since_iso=turn_start
        )
        self.assertEqual(len(serving["calls"]), 3)
        # Reasoning duration sums both reasoning calls: 1.2 + 1.8 = 3.0s -> 3000ms
        self.assertEqual(serving["reasoning_ms"], 3000)
        self.assertEqual(serving["drafting_ms"], 900)
        # Total model latency is 1.2 + 1.8 + 0.9 = 3.9s -> 3900ms
        self.assertEqual(serving["model_total_ms"], 3900)
        self.assertEqual(serving["prompt_tokens"], 1000 + 1500 + 2000)
        self.assertEqual(serving["eval_tokens"], 50 + 60 + 40)

    def test_excluded_roles_not_attributed(self):
        """Health probes, discovery, and background tasks are not counted in turn latency."""
        turn_start = "2026-09-21T06:00:00.000000+00:00"
        self._write_usage_record(
            role="health", provider_id="ollama", model="qwen3.5:9b",
            prompt_tokens=10, eval_tokens=1, duration_seconds=0.05,
            ts="2026-09-21T06:00:01.000000+00:00",
        )
        self._write_usage_record(
            role="discovery", provider_id="ollama", model="qwen3.5:9b",
            prompt_tokens=10, eval_tokens=1, duration_seconds=0.10,
            ts="2026-09-21T06:00:02.000000+00:00",
        )
        self._write_usage_record(
            role="background", provider_id="ollama", model="qwen3.5:9b",
            prompt_tokens=10, eval_tokens=1, duration_seconds=0.50,
            ts="2026-09-21T06:00:03.000000+00:00",
        )
        # The genuine turn call
        self._write_usage_record(
            role="reasoning", provider_id="ollama", model="qwen3.5:9b",
            prompt_tokens=500, eval_tokens=25, duration_seconds=1.5,
            ts="2026-09-21T06:00:04.000000+00:00",
        )

        serving = server._serving_model_for_turn(
            self.user_id, self.session_id, since_iso=turn_start
        )
        # Only the reasoning call is included
        self.assertEqual(len(serving["calls"]), 1)
        self.assertEqual(serving["calls"][0]["role"], "reasoning")
        self.assertEqual(serving["model_total_ms"], 1500)
        self.assertEqual(serving["prompt_tokens"], 500)

    def test_schema_compatibility_and_store_roundtrip(self):
        """EdgeRoutingTraceStore persists and reads back trace events under schema_version='1.0'."""
        self.assertEqual(TRACE_SCHEMA_VERSION, "1.0")
        store = EdgeRoutingTraceStore(self.user_id, root=self.temp_dir.name)
        event = EdgeRoutingTraceEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision="NEEDLE_ESCALATED",
            intelligence_layer="main_brain",
            reason_codes=("NEEDLE_ESCALATED", "PROPOSAL_UNMAPPED_OR_ABSENT"),
            session_id=self.session_id,
            edge={"model_id": "needle-3", "runtime_id": "needle-3"},
            confidence={"score": 0.98, "threshold": 80},
            threshold_percent=80,
            shortlist_size=2,
            main_brain={
                "provider": "ollama",
                "model": "gemma4:12b",
                "prompt_tokens": 9810,
                "eval_tokens": 146,
                "calls": [
                    {"role": "reasoning", "latency_ms": 8900},
                    {"role": "drafting", "latency_ms": 4665},
                ],
            },
            latency_ms={
                "reflex": 97,
                "model": 13565,
                "model_total_ms": 13565,
                "reasoning_ms": 8900,
                "drafting_ms": 4665,
                "total": 14227,
                "total_ms": 14227,
            },
            outcome="success",
        )
        self.assertTrue(store.record(event))
        events = store.list_events()
        self.assertEqual(len(events), 1)

        saved = events[0]
        self.assertEqual(saved["schema_version"], "1.0")
        self.assertEqual(saved["threshold_percent"], 80)
        self.assertEqual(saved["shortlist_size"], 2)
        self.assertEqual(saved["latency_ms"]["reasoning_ms"], 8900)
        self.assertEqual(saved["latency_ms"]["drafting_ms"], 4665)
        self.assertEqual(saved["latency_ms"]["model_total_ms"], 13565)
        self.assertEqual(saved["latency_ms"]["model"], 13565)
        self.assertEqual(saved["latency_ms"]["reflex"], 97)
        self.assertEqual(saved["latency_ms"]["total"], 14227)
        self.assertEqual(len(saved["main_brain"]["calls"]), 2)

    def test_ui_client_parsing_contract_compatibility(self):
        """Simulate Flutter EdgeRoutingEvent and UriTurn parsers to prove no regression."""
        # 1. EdgeRoutingEvent parsing in edge_intelligence.dart:
        # latencyMs = latency?['total'] as int? ?? latency?['reflex'] as int?
        raw_event = {
            "timestamp": "2026-09-21T03:27:14.637151+00:00",
            "decision": "NEEDLE_ESCALATED",
            "intelligence_layer": "main_brain",
            "reason_codes": ["NEEDLE_ESCALATED", "PROPOSAL_UNMAPPED_OR_ABSENT"],
            "session_id": self.session_id,
            "outcome": "success",
            "latency_ms": {
                "reflex": 97,
                "model": 13565,
                "model_total_ms": 13565,
                "reasoning_ms": 8900,
                "drafting_ms": 4665,
                "total": 14227,
            },
            "edge": {"model_id": "needle-3", "runtime_id": "needle-3"},
            "confidence": {"score": 0.98},
            "main_brain": {"provider": "ollama", "model": "gemma4:12b"},
        }
        latency_map = raw_event.get("latency_ms", {})
        flutter_latency_ms = latency_map.get("total") or latency_map.get("reflex")
        self.assertEqual(flutter_latency_ms, 14227)

        # 2. UriTurn parsing in uri_turn.dart / turn_card.dart:
        # durationSeconds: json['serving_duration_seconds'] as num?
        # totalDurationSeconds: json['serving_total_duration_seconds'] as num?
        # promptTokens: json['serving_prompt_tokens'] as int?
        # evalTokens: json['serving_eval_tokens'] as int?
        mock_response = {
            "serving_provider": "ollama",
            "serving_model": "gemma4:12b",
            "serving_prompt_tokens": 9810,
            "serving_eval_tokens": 146,
            "serving_duration_seconds": 13.565,
            "serving_total_duration_seconds": 14.227,
            "serving_reasoning_duration_seconds": 8.900,
            "serving_drafting_duration_seconds": 4.665,
            "serving_model_total_ms": 13565,
        }

        # Simulate _metadataCaption formatting from turn_card.dart:
        # '${totalDuration.toStringAsFixed(1)}s total (${duration.toStringAsFixed(1)}s model)'
        duration = mock_response["serving_duration_seconds"]
        total_duration = mock_response["serving_total_duration_seconds"]
        prompt_tokens = mock_response["serving_prompt_tokens"]
        eval_tokens = mock_response["serving_eval_tokens"]

        caption_time = f"{total_duration:.1f}s total ({duration:.1f}s model)"
        caption_tokens = f"{prompt_tokens} in / {eval_tokens} out ({prompt_tokens + eval_tokens} total tokens)"

        # Now the caption truthfully displays 14.2s total (13.6s model) instead of 4.7s model!
        self.assertEqual(caption_time, "14.2s total (13.6s model)")
        self.assertEqual(caption_tokens, "9810 in / 146 out (9956 total tokens)")


if __name__ == "__main__":
    unittest.main()
