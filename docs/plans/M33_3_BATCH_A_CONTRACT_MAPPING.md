# M33.3 Batch A — WP-A5 Documentary M33.2 Contract Mapping

**Status:** documentation only. No contract was changed, imported, or executed
by Batch A. Runtime compatibility proof belongs to Stage B (A3 §11).
**Plan:** `docs/plans/M33_3_BATCH_A_STAGE_A_QUALIFICATION_READINESS_PLAN.md` WP-A5, G-M1.
**Contract baseline:** `uri_core/core/edge/` and `uri_core/core/edge_lifecycle/`
unchanged since M33.2 B.4 release (`eaf97c5`); byte-identity re-verified
before and after every Batch A step (LF-normalized hashes,
`docs/plans/M33_3_BATCH_A_AGGREGATES.json` `g_r3_*`).

The authority rule is preserved throughout: **propose → validate → approve →
execute**. A Stage A candidate only proposes. URI decides validity,
confirmation, and execution. `orchestrator.py` is untouched and must not grow.

---

## 1. Stage A candidate output → `EdgeProposal` (`contracts.py`)

Batch A normalizes every candidate output to
`{disposition, proposals[{tool, arguments}], error_class, telemetry}`.

| Stage A field | M33.2 contract field | Mapping | Status |
|---|---|---|---|
| `telemetry.provider_id` | `EdgeProposal.provider_id` | direct (`cactus-needle`) | MAPPED |
| `telemetry.runtime_id` | `EdgeProposal.runtime_id` | direct (`needle-subprocess-venv`) | MAPPED |
| `telemetry.model_id` | `EdgeProposal.model_id` | direct (`needle-3`) | MAPPED |
| `telemetry.artifact_hash` | `EdgeProposal.artifact_hash` | Batch A did not hash the Needle weights (`null`) | MAPPED, VALUE GAP |
| request kind | `EdgeProposal.operation` | `"tool_proposal"` (`EdgeToolRequest`) | MAPPED |
| `proposals[]` | `EdgeProposal.result` | `result = {"proposals": [...]}`; `result` is a free `Dict`, so a list fits | MAPPED |
| `disposition` = `ASK` / `ABSTAIN` | — | no field | **GAP-1** |
| `disposition` = `ESCALATE` | `EdgeProposal.result == {}` plus routing `ESCALATE` | Needle's "no call" is the only escalation signal, as in the accepted M33.2 bridge | MAPPED (implicit) |
| `telemetry.confidence` | `EdgeProposal.raw_confidence` | Needle returned numeric values in Batch A (e.g. `1.0`), but M33.2 B.3 recorded `confidence = null` for the tuned checkpoint and no score semantics are declared | MAPPED; semantics `UNAVAILABLE` (**GAP-2**) |
| — | `EdgeProposal.raw_confidence_semantics` | must stay `"UNAVAILABLE"` until declared; `adapters/benchmark.py` `VALID_SCORE_SEMANTICS` would require `"none"` | MAPPED |
| `telemetry.latency_ms` | `EdgeProposal.latency_ms` (`int`) | rounded | MAPPED |
| `error_class` | `EdgeProposal.errors` | `(error_class,)` | MAPPED |

The resident Main Brain (R-9B) is **not** mapped to `EdgeProposal`. It is the
Main-Brain path (`ModelRouter`, native tool loop), a sibling of Edge, not an
`EdgeIntelligenceProvider` (M33.2 migration plan §1). Wrapping it in the Edge
contract would force it through a narrower interface and break A3 §13.

## 2. Validation inputs → `RoutingInput` / `evaluate_routing` (`routing_policy.py`)

| `RoutingInput` field | Stage A source | Status |
|---|---|---|
| `uri_preflight_available` | not modeled; the battery has no deterministic-preflight cases | **GAP-3** (battery coverage) |
| `explicit_main_brain` | not modeled | GAP-3 |
| `input_requires_confirmation` | URI-owned tool risk in the battery catalog (`CONFIRM`/`DESTRUCTIVE`) | MAPPED (URI decides, never the model) |
| `task_complex` | analog: `MUST_ESCALATE` cases | MAPPED (analog only) |
| `proposal_valid` | analog: proposal with no invented entity, no out-of-shortlist tool, schema-valid arguments (scorer G-S3 inputs) | MAPPED (analog); a real validator is a Stage B item |
| `reply_valid`, `calibrated_confidence`, `calibration_current` | none — no calibration exists | NOT REACHABLE: `EDGE_REPLY` cannot fire for any Batch A candidate |
| `resource_admitted` | not measured as an admission decision | GAP-4 |
| multi-call proposals (e.g. `RWB-010` search → draft) | `RoutingInput` has one `proposal_valid` boolean | **GAP-5** |

`IntelligenceRoutingDecision.EXECUTE_PROPOSAL` does not grant execution: the
proposal still enters the canonical gate path (M33.2 migration plan §4
contract-injection seam). Batch A's "AUTO" risk class models what URI would
run without a confirmation step; it is URI metadata, not model output.

## 3. Trace → `EdgeRoutingTraceEvent` (`trace.py`)

| Stage A telemetry | Trace field | Status |
|---|---|---|
| routing outcome | `decision`, `reason_codes` | MAPPED |
| layer | `intelligence_layer` (`EDGE` / `MAIN_BRAIN`) | MAPPED |
| `len(available_tools)` | `shortlist_size` | MAPPED |
| first proposed tool | `capability_id` (single value) | MAPPED; multi-call is **GAP-5** |
| `resident_main_brain_invoked` | `main_brain` dict | MAPPED |
| `unnecessary_resident_main_brain_invocation` | — | **GAP-6** (new field required by A3 §9; must not be added without a Stage B/C decision) |
| safety flags (G-S1..G-S3) | — (only bounded `reason_codes`) | **GAP-7** |
| latency, resource | `latency_ms`, `resource` dicts | MAPPED |
| raw user text / arguments | — (whitelist redaction forbids raw content) | CORRECTLY NOT MAPPED |

## 4. Inventory, settings, lifecycle, adapters, endpoints

- `runtime_inventory.py`: `DEFAULT_EDGE_RUNTIME_INVENTORY` is empty, so
  `selection_status` never returns `ready` and no Edge model is dispatched in
  production (static finding, plan D-8). A Stage B replay needs a
  **non-default, test-only** `RuntimeProfile` for Needle
  (`qualified_assistance_kinds` stays empty; Needle is not qualified for
  assistance kinds). **Stage B question SB-1.**
- `settings.py`: see §5 for the Edge on/off requirement. Threshold (default
  90) is irrelevant until a calibrated `EDGE_REPLY` exists.
- `edge_lifecycle/models.py`: `ModelArtifactRecord` (`content_hash`,
  `byte_size`) ← Batch A artifact metadata; `HardwareCapacityRecord.vram_mib`
  ← Batch A measured VRAM only as a system-wide performance counter, not per
  process (**GAP-8**); `InvocationTelemetryRecord(invoked, bypass_reason,
  latency_ms, rss_memory_bytes)` ← Batch A rows; `RuntimeLifecycleState.RESIDENT`
  applies to Needle (B.4), not to the Main Brain.
- `adapters/benchmark.py`, `adapters/ensemble.py`: `BenchmarkCandidate.score_semantics`
  must be declared (`"none"` for Needle today). The `EnsembleAdapter` role
  split (`reflex` / `language` / `reasoner`) is unchanged; Batch A used only
  the `reflex` role's model through its own sibling bridge.
- `/intelligence/settings`, `/intelligence/status`, `/intelligence/routing/latest`,
  `/intelligence/trace` (`server.py:3027-3095`): read models are sufficient
  for status/trace display; no Batch A field requires a new endpoint.
- Accepted M33.2 tests (import-boundary, preference-not-read-by-authority,
  caller isolation, trace redaction): no Batch A change touches their subjects.

## 5. Forward product requirement: per-user Edge on/off (recorded, not implemented)

User requirement (2026-09-25): URI must expose a persistent per-user
`edge_intelligence_enabled` setting.

- **Existing home:** `EdgeSettings.enabled` (bool) in the caller-scoped
  `edge_intelligence.json`, written only through the authenticated
  `PUT /intelligence/settings` path with optimistic revision; a model has no
  write path (`settings.py` `update`). The requirement maps onto this field;
  only the product-facing name differs.
- **ON:** `evaluate_routing` may return Edge decisions for eligible tasks;
  `ESCALATE` to the Main Brain remains available.
- **OFF:** `evaluate_routing` returns `SUPPRESS` with `edge_disabled_by_user`,
  so the request continues on the normal Main-Brain path. The check comes
  **after** `uri_preflight_available`, so deterministic URI_PREFLIGHT is
  unaffected by OFF. Deterministic mechanisms (retrieval, context resolution,
  RAR, other non-model mechanisms) are separate from this flag and must stay
  separate unless a future approved design couples them.
- **OFF deletes nothing:** the store only rewrites the settings document;
  models, other configuration, trace history, and evidence are untouched.
  (M33.2 migration plan §8: the single `enabled` flag disables every Edge
  *modality*; deterministic mechanisms are not Edge modalities.)
- **No silent re-enable — open item SB-2:** a user's persisted OFF survives
  restarts. But a missing settings document loads defaults, and the default is
  `enabled: True`. Whether a lost or new document may default to ON is a
  product decision for Stage B/C, not a Batch A change.

## 6. Forward compatibility: peer-shared institutional knowledge (recorded, not implemented)

Future URI clients may share, opt-in and without a central server,
institutional document patterns, letterheads, fonts, sizes, spacing, margins,
layouts, headers/footers, approved templates, shared institutional facts, and
user-selected shared folders, with provenance and versions, separate from
personal/local memory. Batch A adds nothing that blocks this: its artifacts
are local files with explicit provenance and schema versions; it adds no
global state, no server dependency, and no coupling between Edge settings and
any knowledge store. Shared-knowledge inputs to a future Edge candidate would
arrive as `EdgeRequest` context and must stay labelled untrusted
(`untrusted_content_present`), like any other external content.

## 7. Gap list and Stage B questions

| ID | Gap / question | Owner decision |
|---|---|---|
| GAP-1 | No `ASK`/`ABSTAIN` disposition in `EdgeProposal` or `IntelligenceRoutingDecision` | Stage B/C contract decision |
| GAP-2 | Needle confidence semantics undeclared; B.3 saw `null`, Batch A saw numbers | Stage B |
| GAP-3 | Battery lacks URI_PREFLIGHT and explicit-Main-Brain cases | next battery version |
| GAP-4 | Resource admission not modeled | Stage B |
| GAP-5 | Single `proposal_valid` / `capability_id` vs multi-call proposals | Stage B/C contract decision |
| GAP-6 | No trace field for unnecessary Main-Brain invocation | Stage B/C |
| GAP-7 | Safety flags only expressible as bounded reason codes | Stage B/C |
| GAP-8 | VRAM only system-wide, not per process | measurement method |
| SB-1 | Test-only `RuntimeProfile` needed for replay; runtime confirmation that no production path dispatches Edge (plan D-8/R-3) | Stage B precondition |
| SB-2 | Default `enabled: True` when the settings document is missing | product decision |

G-M1 (mapping completeness): every Stage A output field above is either
mapped to a named M33.2 contract field or listed as a gap. **No contract
change is proposed or made by Batch A.**
