# URI Milestone Tracker

**Scope:** M6 onward — the actual implementation-milestone scheme used in this
repository's commit history. This is the canonical, actively maintained record
of delivery status for M-numbered milestones.

**Last verified:** 5 Sep 2026, against `uri-agent` HEAD (`744d05c`, branch `master`,
clean working tree). Verification below was produced by running the listed
test files with `unittest` directly (`.venv/Scripts/python.exe -m unittest ...`),
not by re-reading commit messages.

## Relationship to the older Phase 0–4 checklist

This tracker does **not** replace, relabel, or rewrite the earlier
Phase 0–4 architecture-planning checklist, preserved unchanged at:

`OneDrive\Desktop\URI_Project_Management_Session_001_Closed_29_Aug_2026\URI_Project_Management\URI_MILESTONE_CHECKLIST.md`

That document reflects an earlier, pre-implementation planning scheme
(architecture-freeze phases 0–4) from a closed project-management session
dated 29 Aug 2026. It is retained as historical documentation only and is
not actively maintained. Current implementation work is tracked exclusively
by the M-numbered milestones below.

---

## Milestones

| Milestone ID | Milestone Name | Status | Commit Hash | Verification / Test Status | Purpose (short) | Major Deferred Items |
|---|---|---|---|---|---|---|
| M6 | Capability Awareness | DONE | `89169c1` | **Verified 5 Sep 2026:** 60/60 tests pass — `test_capability_planner.py`, `test_capability_registry.py`, `test_capability_authority_boundary.py`, `test_ollama_provider.py`, `test_server_capabilities_endpoint.py` | One authoritative capability descriptor (status, availability, permissions, approval requirement, risk) plus read-only model/provider self-knowledge (`ModelProvider.describe()`), exposed via `GET /capabilities`. Reporting-only — dispatcher, workflow executor, and tool-selection scoring remain unaware of it. | Capability awareness still does not influence tool selection or execution (by design, enforced by boundary tests). `PC/System Optimization` remains a documented `not_implemented`, high-risk example capability with zero executable backing. |
| M7 | Real Approval Gate + Self-Knowledge Protection | DONE | `b967ff3` | **Verified 5 Sep 2026:** 73/73 tests pass — `test_approval_gate.py`, `test_approval_store.py`, `test_authoritative_facts_immutability.py`, `test_capability_authority_boundary.py`, `test_orchestrator_approval_gate.py`, `test_server_approval_endpoints.py` | `ApprovalStore` (bound to action_id + capability_id + session_id + argument fingerprint, single-use, fail-closed) and `ApprovalGate` sit in front of `ToolDispatcher` for both direct and dynamic-workflow execution paths. Also locks identity/purpose and verified capability facts against mutation via user input, model output, or memory/profile APIs (proven by static analysis + file-hash invariance). | None recorded in the commit message — **not yet confirmed with project owner.** |
| M8A | Live Conversational Response Foundation | DONE (superseded by correction, see M8A-fix) | `3570651` | **Verified 5 Sep 2026 (combined with M8A-fix below):** see M8A-fix row — the two commits' test suites were run together against current HEAD since M8A's own behavior is only meaningful post-correction | Grounded natural-language narrative alongside every deterministic response (drafted after the outcome is decided, validated for claim-consistency); a Tasks screen wired to the real approval gate; `extract_student_records` / `draft_institutional_note` rewritten to parse actual request text through the real service chain instead of returning fixed, input-independent content; learned-skill path re-executes through the real dispatcher/approval gate instead of a fake "recognized" response. | Known gaps at merge time, all closed by M8A-fix: gap-reason phrasing didn't distinguish "doesn't exist" from "exists but unavailable now"; `workflow_capability_router`'s generic bucket could report success on failure; ambiguous student identifiers were silently resolved to the first match. |
| M8A-fix | M8A correction: honest gap reasons + student-record ambiguity handling | DONE, VERIFIED | `744d05c` | **Verified 5 Sep 2026:** 85/85 tests pass — `test_orchestrator_response_narrative.py`, `test_response_drafting.py`, `test_server_ask_narrative.py`, `test_extract_student_records.py`, `test_draft_institutional_note.py`, `test_workflow_capability_router.py`, `test_response_drafting_gap_condensation.py`, `test_response_validation.py` | Adds `CapabilityDescriptor.gap_reason` distinguishing `not_implemented` (no execution adapter exists) from `unavailable_runtime` (adapter exists, runtime can't use it now), threaded through response drafting/validation so URI never implies more detail or approval would unblock a capability that doesn't exist. Fixes `workflow_capability_router`'s generic bucket to report real failure instead of faking success. Makes `extract_student_records` detect and surface ambiguous identifiers instead of silently picking one. | Not specified in commit message — **not yet confirmed with project owner.** |
| M10A | Unified Query Context Foundation | DONE, VERIFIED | *pending commit — implemented on top of `e259ae5`, working tree not yet committed at time of writing* | **Verified 5 Sep 2026:** targeted suite 57/57 passing — `test_query_context.py`, `test_response_drafting.py`, `test_capability_authority_boundary.py`, `test_orchestrator_response_narrative.py`. Full repo `python -m unittest discover -p "test_*.py"`: 722 collected, 719 passing, 3 pre-existing collection errors unrelated to this milestone (see Major Deferred Items). Flutter `flutter test`: 70/70 passing (no Dart/UI changes in this milestone). | New pure, read-only module `uri_core/core/query_context.py` assembles one bounded, model-facing context — identity/character/principles, personalization + consent-eligible memory, current session/task state, VERIFIED-only evidence, and the capability catalogue with its approval-requirement/risk/gap-reason fields — reusing existing sources (`ModelReasoningGateway.load_policy()`, `personalization_context.build_personalization_context()`, `UriOrchestrator._build_model_session_context()`, `evidence_context.get_verified_evidence()`/`evidence_summary()`, `CapabilityRegistry.list_capabilities()`) with no new storage and no duplicated logic. Wired into `response_drafting.DraftRequest` as one new optional `query_context` field and supplied by `UriOrchestrator._build_query_context()` — closing the gap identified in the M10A audit where session/evidence/capability context reached only the shadow `ModelReasoningGateway.reason()` path (never shown to a user) while the live, user-visible narrative-drafting path saw only personalization. Capability information is reporting-only, exactly as `CapabilityDescriptor` already intends — no selection/scoring logic was added, and `CapabilityPlanner` is untouched. | Does not change capability selection/planning — the Brain now *receives* the capability catalogue but nothing yet acts on that awareness (`CapabilityPlanner`'s deterministic keyword scoring is unchanged by design). No multi-turn conversation transcript exists or was added — session/task context remains the existing fact-and-workflow-shaped state, not a raw dialogue history. `ModelReasoningGateway.reason()`'s shadow path was not changed to also receive personalization/query context, so the two model-facing pipelines documented in the M10A audit remain distinct; unifying them further is explicitly out of scope for this milestone. M11's general problem-solving loop over this context is out of scope. Not yet confirmed with project owner. |

---

## Verification method (for future updates)

1. Confirm working tree is clean and on the intended commit: `git status --short`, `git log -1 --format=%h`.
2. Identify the test files touched by the milestone's commit(s): `git show --stat <hash>`.
3. Run them directly with the repo's venv (tests use stdlib `unittest`, not pytest — pytest is not installed in `.venv`):
   `.venv/Scripts/python.exe -m unittest <test_module_1> <test_module_2> ... -v`
4. Record the pass count and date in the Verification column. Do not mark a milestone "verified" from commit-message claims alone.
