# M33.2 Batch B.3 — State

**Status:** ACCEPTED — awaiting Antigravity-routed implementation
**Plan:** `docs/plans/M33_2_BATCH_B3_LOCAL_MODEL_RUNTIME_LIFECYCLE_PLAN.md`
**Depends on:** Batch B.2 `b98620a`, CLOSED/ACCEPTED; architecture
amendment to `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md`
§13, recorded 2026-09-20.

## History log

- **2026-09-20 — Architecture conflict found, then DRAFT → ACCEPTED
  (Claude):** After closing and releasing Batch B.2 (`b98620a`), Claude
  began drafting B.3 per the User's original scope (URI-managed local model
  installation, install/update/remove lifecycle, etc.) and, per the
  Verification-First standard's requirement to inspect primary evidence
  before returning a plan, checked the frozen
  `M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` §13 non-goals list.
  Found a direct contradiction: §13 explicitly excluded "runtime
  installation; OS-permission changes" as one undifferentiated item, which
  the User's B.3 request directly conflicts with. Rather than silently plan
  around this or auto-approve past it, Claude stopped and asked the User
  how to resolve it (a genuine architectural-boundary question, per this
  project's own "preserve User review authority" rule). The User chose to
  redefine B.3 directly: authorize a narrow architecture amendment that
  splits the single excluded line into (a) still-excluded, unconditional:
  privileged/OS-level/system-wide installation, OS permission changes,
  GPU/driver installation, PATH/registry/service modification, third-party
  executable installation, and installation outside URI-controlled storage;
  and (b) newly permitted, additive: URI-managed, user-space model and
  portable-runtime lifecycle under deterministic validation and integrity
  controls. Claude applied this amendment to the architecture doc itself
  with full auditable correction history (original line preserved, not
  overwritten), then drafted this plan against the amended boundary.

  The plan additionally resolves a second real conflict Claude identified
  during drafting (not User-raised, found independently per the
  Verification-First standard's "independent defect discovery" rule):
  URI-managed model **download** requires network egress, which would
  violate the existing recursive zero-egress AST tests covering
  `uri_core/core/edge/` if lifecycle code were placed inside that tree.
  Resolution: lifecycle code lives in a new sibling package (outside
  `uri_core/core/edge/`), the existing zero-egress tests are preserved
  unweakened, and a new, separate test proves network calls are reachable
  only from a named, explicit set of install/update/download entry points.

  This is a routine, standing-auto-approved planning extension once the
  boundary and egress questions were explicitly resolved by direct User
  instruction and independent inspection respectively — it does not itself
  touch core project structure or the security/authority model beyond the
  User-authorized amendment. Per standing AO-4 governance, Claude produced
  this plan and the paired architecture amendment, and now stops:
  implementation is routed through Antigravity to Codex, outside this
  session, not performed directly by Claude.

## Routing

Antigravity: pick up this ACCEPTED plan, route implementation to Codex
(multi-file, new-package, precision-critical, security-boundary-adjacent
work fits "complex/precision-critical" routing criteria over Gemma's
bounded-task profile — same rationale used for B.1/B.2), and persist
milestone state through the usual `STATE.md`/completion-report handoff
artifacts this repository already uses for M33.1/M33.2 batches.

**Binding constraint for the implementation task package:** the
implementation task Antigravity writes for Codex must explicitly quote
this plan's "still-excluded, unconditional" list and instruct Codex to stop
and escalate (not implement a workaround) if any part of the work would
require privileged installation, OS permission changes, or writing outside
URI-controlled storage.

## Next action

Antigravity packages the completion report, source diff, generated
evidence, and test results for Claude's independent audit once
implementation reports `VERIFICATION_READY`. Claude determines ACCEPT or
REPAIR REQUIRED. Codex does not self-verify, commit, or push.
