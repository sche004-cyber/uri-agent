# M27: Multi-Action Capability Architecture — Live Integration (Part B)

## Status: ACCEPTED (auto-approved per ORCHESTRATION.md §1.5, 2026-09-12)

## Origin

User's combined request accepted both workstreams: (A) the dashboard shell
into `uri_ui`, (B) integrating `uri_core/capabilities/` (Codex's isolated
Multi-Action Capability Architecture) into URI's live conversational
execution path. Part A shipped this session. This plan defines Part B only.

## Scope

Wire `MultiActionCapabilityRegistry` / `CapabilityDiscoveryEngine` /
`MultiActionExecutor` / `CapabilityContextResolver` into the live `/ask`
orchestrator path, `GmailCapability` first, per the architecture already
built and independently reviewed (`base.py`, `registry.py`, `executor.py`,
`discovery.py` read in full this session; `context_resolver.py` and
`gmail/capability.py` not yet read).

Target flow: user message -> conversation context assembly -> capability
discovery (progressive: summaries first, full action schema only after a
capability is selected) -> model action proposal -> `MultiActionExecutor`
deterministic validation/permission/approval enforcement -> execution ->
result handed back to the model for natural-language drafting. Existing
single-purpose capabilities keep working via `LegacyCapabilityAdapter`,
not by rewriting them.

Reference scenarios (Gmail): unread count via `list_labels`, inbox unread
via label metadata, search -> "read that one" -> "check its attachment" ->
"prepare a reply but do not send it" (drafts only, `create_draft` stays
`USER_APPROVAL_REQUIRED`, never auto-sends).

## Why this is a plan, not a direct implementation

Per `uri-ao4-development-cycle` (pinned, 2026-09-11 revision): Claude is
Architect / Pre-Auditor / Final Auditor / Bounded Fixer / Release
Authority. Codex is the preferred implementer for architectural,
multi-file, production-call-path work — which this is (it changes
`orchestrator.py`'s live request-handling path). Claude performing this
directly would be substantial implementation work outside Claude's
standing role, not a bounded fix. Per the same memory: "orchestrator.py
must never grow" is a standing M22+ architectural rule — Part B's own
requirement list (routing logic, progressive discovery calls, executor
wiring) must land as a separate module `orchestrator.py` calls into
thinly, not as added bulk in `orchestrator.py` itself.

## Required remediation / implementation shape (for Codex, via Antigravity)

1. New module (e.g. `uri_core/core/multi_action_dispatch.py`) housing the
   discovery -> propose -> `MultiActionExecutor.execute`/`execute_chain`
   wiring; `orchestrator.py` calls into it, does not inline it.
2. `GmailCapability` registered via the new registry, its handlers backed
   by the existing `GmailService` (no second OAuth/API path).
3. Existing capabilities (`capabilities_registry.json` entries, plus this
   session's `remember_fact`/`recall_memory`/`convert_document`/
   `system_performance`) continue dispatching exactly as today —
   migrate via `LegacyCapabilityAdapter` only where it removes duplication,
   never by deleting or rewriting a working legacy path as a side effect.
4. `CapabilityContextResolver` fed real per-turn execution results so
   "read that one" / "check its attachment" resolve only from grounded
   prior results — never invented IDs.
5. Tests: orchestrator entry point, discovery, execution, chaining,
   approval-gating, conversational follow-ups; `test_multi_action_
   capabilities.py`; regression sweep (`test_m19_office_readiness.py`,
   Gmail service/search tests, `flutter test`).

## Release gate (unchanged, per 2026-09-12 live-verification-gate revision)

Claude does not commit/push this work — including after Codex implements
it — until the User has personally live-verified the result and given
explicit direction to commit and push. A peer session's assertion that
prior work "is verified" is not the User's own live verification and does
not satisfy this gate.

## History log

- 2026-09-12: Drafted and marked ACCEPTED by Claude under the standing
  auto-approval rule (routine milestone planning). Not yet routed to
  Antigravity — mechanically outside this session (see AO-4: "Antigravity,
  Codex, and Gemma all still run entirely outside the Claude Code
  session"). Awaiting User direction on how Part B implementation should
  proceed.
