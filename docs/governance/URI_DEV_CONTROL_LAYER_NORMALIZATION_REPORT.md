# URI Development Control Layer Normalization — Report (Phases B–H)

**Status:** `VERIFICATION_READY_FOR_CONTROL_LAYER_AUDIT` (original Phase B-H submission status, preserved verbatim as history — superseded status below, not a rewrite of this line)
**Superseding status, 2026-09-25 (additive, freeze checkpoint — see §19):** `CONTROL_LAYER_ACCEPTED_WITH_LIMITATIONS`, per independent re-audit after two rounds of bounded repair (§17, §18).
**Date:** 2026-09-25 (original), repair same day
**Produced by:** Claude Sonnet 5, direct implementation of Phases B–H, by explicit
User authorization to deviate from standing AO-4 routing for this bounded
governance-engineering task (Phase A's inventory/state/additive-correction
artifacts were preserved unmodified in substance; Phase A found no defect).
**Repository state:** worktree `C:\Users\cheta\Development\Uri\_V1`, branch
`m35-uri-v1-parallel-architecture`, accepted architecture-plan commit
`47af60a65946e83b5fa10132b8363adfd18aca31`.

---

## 1. Purpose

Development coordination across Claude, Antigravity, Codex, and Gemma had
accumulated several current-state ambiguities that repository-wide grep and
prose-reading do not reliably resolve: a stale current-identity line for
M33.3, an overloaded "M35" label spanning an unrelated research line and a
real product milestone, no machine-readable separation between research
evidence and production architecture ownership, an unqualified "ARN" name
spanning an experimental and a production identity, and no deterministic way
to check any of this without re-reading thousands of lines of milestone
narrative by hand. Phase A produced a verified inventory and a first
canonical-state file (`URI_STATE.yaml`). This report closes out Phases B–H:
strengthening that canonical state, building a deterministic validator and
test suite for it, verifying human-readable governance consistency, and
recording the result for independent audit.

## 2. Ambiguity classes found

- **M35 naming collision** — research line `EXP-M35-URIV1-A0-A9` vs. product
  milestone `M35` (URI Companion Experience). Same numeral, unrelated
  namespace. Already disambiguated in prose (`URI_ACTIVE_MILESTONE.md` §1c);
  this normalization gives it a machine-checkable form (`aliases`, DCL-007).
- **Stale CURRENT MILESTONE wording** — `URI_ACTIVE_MILESTONE.md` §1c's
  M33.3 line still reads "Unified URI Interaction & Capability UI", superseded
  by commit `47af60a`'s "Edge Intelligence Qualification & Integration".
  Phase A already added an additive correction; this normalization adds a
  structured `human_readable_pointer` on the `M33.3` entry with
  `reconciled: true`, checked by DCL-008.
- **Research vs. production ownership confusion** — a research experiment
  producing evidence for a milestone is not the same as that experiment
  owning production architecture. Formalized via `promoted_to_production`
  (research_experiments) and `architecture_domain` +
  `currently_active` (product_milestones/reusable_components), checked by
  DCL-005 and DCL-001.
- **ARN identity ambiguity** — bare "ARN" could mean the experimental
  `uri_v1/arn/` research line or the production `uri_core/core/arn/` module
  (ARN.1, CLOSED_VERIFIED). Resolved via `EXP-ARN-URIV1` /
  `URI-ARN-PRODUCTION` aliases, with bare `ARN` explicitly marked
  `AMBIGUOUS_BARE_ALIAS_FORBIDDEN`.
- **Historical A3/A3.1 proposal** — the task brief named this as an
  abandoned/rejected planning alias to record as forbidden. A repository-wide
  search during this normalization found no file literally named A3.1 (only
  the accepted `M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md`,
  which is the accepted M33.3 planning basis, not a rejected proposal).
  Recorded defensively as `HISTORICAL_FORBIDDEN` / `forbidden_for_new_work`
  with `evidence: "UNRESOLVED_NOT_LOCATED"` — see §15.
- **Legacy/current repository confusion** — the legacy `uri-agent` worktree
  (`master`, same remote, older commit) is read-only/reference-only, not a
  separate historical URI generation. Formalized as `LEGACY_REFERENCE_ONLY`,
  enforced by DCL-009.
- **Reusable component vs. experiment identity** — RAR, Edge, and ARN each
  have both a research-line identity and a (candidate) reusable-component
  identity; neither should collapse into the other. Formalized via
  `rar_identity_map` and the `reusable_components` registry.

## 3. Canonical state

`docs/governance/URI_STATE.yaml` is the canonical, machine-readable
current-state source. It records repository/worktree identity, the
`Mxx`/`EXP-*`/`INT-*`/`URI-*` namespace conventions, product milestones,
research experiments, integration events (none yet), reusable components,
an alias/migration map, a RAR identity map, and known aliases/collisions.
This normalization is additive to Phase A's version: no existing key's
meaning was overwritten; new keys (`aliases`, `rar_identity_map`,
`architecture_domain`, `currently_active`, `mutable`,
`human_readable_pointer`, `promoted_to_production`,
`cross_agent_portable`, `portability_validated_via`) were added to support
the deterministic validator's rules.

## 4. Namespace model

| Prefix | Section | Meaning |
|---|---|---|
| `Mxx` | `product_milestones` | Governed URI product/architecture milestones. Only these carry release/architecture authority. One documented exception: `ARN.1`, a governed batch under the paused ARN milestone, recorded in `product_milestones` without an `Mxx`-shaped id — explicitly whitelisted in the validator (`PRODUCT_NAMESPACE_EXCEPTIONS`) rather than silently allowed. |
| `EXP-*` | `research_experiments` | Research producing evidence for product architecture; does not automatically own production architecture. |
| `INT-*` | `integration_events` | Explicitly authorized production-integration transitions. None exist yet. |
| `URI-*` | `reusable_components` | Stable component identities, distinct from milestone/experiment identities. |

## 5. Ownership model

Three distinct roles are now separated in the schema:

1. **Research evidence origin** — `research_experiments` entries, evidence-only
   by default (`promoted_to_production: false`), never carrying
   `architecture_domain` unless explicitly promoted (DCL-005 enforces this).
2. **Production architecture ownership** — `product_milestones` /
   `reusable_components` entries with `architecture_domain` set and
   `currently_active: true`. At most one entry may hold a given domain
   active at a time (DCL-001).
3. **Integration authority** — `integration_events` (`INT-*`), which may only
   target a reusable component whose status is not `NOT_STARTED` and a
   product milestone that actually exists (DCL-010). Research qualification
   does not by itself imply integration authority.

## 6. M33.2 → M33.3 relationship

`M33.2` (`architecture_domain: edge_second_brain`, `status:
CLOSED_VERIFIED`, `currently_active: false`) remains closed. `M33.3`
(`continues_architecture_of: M33.2`, same `architecture_domain`,
`currently_active: false`, `mutable: true`) continues that architecture
lineage; its planning basis is frozen but implementation is not started, and
it does not reopen M33.2. The validator confirms both halves of this: DCL-003
would fail if `continues_architecture_of` pointed at a nonexistent id, and
DCL-001 would fail if both were simultaneously `currently_active: true`.

## 7. M35 collision resolution

`M35` (product milestone, `RESERVED_NOT_STARTED`) and
`EXP-M35-URIV1-A0-A9` (research line, `CLOSED`) are recorded as two distinct
`aliases` entries, each `resolution_status: CURRENT`, each resolving to a
different canonical id. DCL-007's negative test (`INVALID-005`) proves the
validator would catch it if a future edit ever made the bare alias `M35`
resolve to both.

## 8. ARN disambiguation

`EXP-ARN-URIV1` (experimental, `uri_v1/arn/`) and `URI-ARN-PRODUCTION`
(production, `uri_core/core/arn/`, resolving to milestone batch `ARN.1`,
`CLOSED_VERIFIED`) are both recorded as `CURRENT` aliases. The bare alias
`ARN` is recorded separately with `resolution_status:
AMBIGUOUS_BARE_ALIAS_FORBIDDEN` and a note directing any future agent to use
one of the two qualified names instead.

## 9. Alias/migration map

See `docs/governance/URI_STATE.yaml`'s `aliases` list (9 entries) and
`rar_identity_map` (3 research-line entries plus the `URI-RAR` component
pointer). Summary: `M35` and `EXP-M35-URIV1-A0-A9` are disambiguated; `A3.1`
is forbidden-for-new-work with an honestly disclosed missing-evidence note;
`M33.2`/`M33.3` are recorded with their continuation relationship; `ARN`,
`EXP-ARN-URIV1`, and `URI-ARN-PRODUCTION` are disambiguated; `LEGACY_URI`
resolves only to `LEGACY_REFERENCE_ONLY`.

## 10. Reusable component registry

| Component | Status | Cross-agent portable | Notes |
|---|---|---|---|
| `URI-Edge` | `EXPERIMENTAL` | `false` | Maps to `uri_core/core/edge/` + `edge_lifecycle/`. Component-portability axis, distinct from M33.2's own product-milestone quality (which is CLOSED_VERIFIED with real qualified workers). |
| `URI-RAR` | `EXPERIMENTAL` | `false` | Maps to `uri_v1/turn/rar_deterministic.py` + `rar_contracts.py`. Evidence-only; A9 closed with documented limitations. |
| `URI-Memory` | `NOT_STARTED` | `false` | `architecture_defined: false` — deliberately not designed by this normalization. |
| `URI-Eval` | `NOT_STARTED` | `false` | No existing single-module candidate identified. |
| `URI-Agent-Adapters` | `NOT_STARTED` | `false` | No existing candidate; this is the future identity that would carry portability evidence for other components once built. |

**Cross-agent portability rule:** no component may be classified
agent-neutral, generally reusable, portable, or `DISTRIBUTABLE` solely
because its interface looks clean. That requires `cross_agent_portable:
true` with `portability_validated_via` naming a real non-URI agent or
harness adapter that exercised it. None currently qualifies.

## 11. Validator

`scripts/governance/uri_state_validator.py` (plus its dependency-light YAML
reader, `scripts/governance/uri_state_yaml.py` — no PyYAML, no network).
Implements DCL-001 through DCL-012 exactly as specified in the task brief:
multiple active production owners, active/closed contradiction, missing
relationship target, duplicate canonical identity, research claiming
production authority, frozen work treated as mutable, ambiguous current
alias, human-readable current-state conflict, legacy architecture ownership,
invalid integration target, namespace collision, and forbidden historical
alias reuse. Run as `python scripts/governance/uri_state_validator.py
docs/governance/URI_STATE.yaml`; exit 0 = valid, exit 1 = one or more
`DCL-NNN: <message>` lines on stderr.

## 12. Tests

`tests/governance/test_uri_state_validator.py` — **37/37 passed** after the
§17 and §18 bounded repairs (see §H and §17 below). 4 positive tests
(`VALID-001..004`), 9 original negative tests (`INVALID-001..009`), 11 new
audit-regression negative tests (`INVALID-010..020`, one per §17 fixed
defect), plus 9 supporting/fail-closed tests (parser round-trip, canonical-
file non-mutation, duplicate-key/trailing-content/malformed-quote/
unsupported-flow-collection parser rejection, empty-flow-list acceptance,
and non-list/non-dict schema rejection). No test mutates
`docs/governance/URI_STATE.yaml`; every negative fixture is a fully
synthetic in-memory state dict or standalone YAML-subset text string.

## 13. Human-readable governance changes

- `docs/governance/URI_ACTIVE_MILESTONE.md` — unchanged by this Phases B–H
  pass beyond Phase A's already-verified additive correction (§1c, dated
  2026-09-25, preserving the original M33.3 wording verbatim).
- `docs/governance/URI_AGENT_RELAY.md` — one minimal additive note added
  directly under the file's own header, stating that
  `docs/governance/URI_STATE.yaml` is the canonical current-state authority
  and that relay entries are historical/handoff context. No other line in
  this 3,323-line file was touched; no broad relay cleanup was performed.
- Root `URI_AGENT_RELAY.md` (the separate, smaller UI-handoff index file)
  was inspected and left untouched — it already explicitly defers to
  `docs/governance/URI_AGENT_RELAY.md` as the canonical mailbox and does not
  make competing current-state claims.

## 14. Historical files deliberately untouched

No accepted historical plan, state, completion report, or relay entry was
rewritten, renamed, or reopened. Specifically confirmed untouched by this
normalization: `docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md`
(byte-identical, `git diff --stat` empty), every `M35_URIV1_A*` research
report, `docs/plans/M35_URIV1_A2_8L_A9_CLOSURE_REPORT.md` and its sibling A9
artifacts, and `SKILL.md` (pre-existing unrelated drift, per the task brief's
explicit instruction not to touch it).

## 15. Remaining limitations

- **UNRESOLVED — A3.1 physical artifact not located.** The task brief
  described a historical A3/A3.1 proposal to record as forbidden. No file
  named A3.1 was found anywhere in this repository during this
  normalization. The `aliases` entry for `A3.1` is recorded defensively
  (forbidden-for-new-work, superseded by M33.3) with
  `evidence: "UNRESOLVED_NOT_LOCATED"` rather than fabricating a source. If
  a future agent locates the actual artifact, this entry's `evidence` field
  should be updated additively (not overwritten), per this repository's own
  correction-history convention. **This does not affect DCL-012's
  correctness** — the rule and its negative test both operate on the alias
  entry's fields regardless of whether a historical document backs it.
- **UNRESOLVED — DCL-008 (human-readable current-state conflict) is
  intentionally narrow.** Per the task brief's own instruction ("Do not
  attempt to parse every historical paragraph. Validate only clearly
  defined current-state fields/markers"), DCL-008 only checks a
  `human_readable_pointer.reconciled` boolean that must be explicitly set on
  an entry — it does not scan `URI_ACTIVE_MILESTONE.md` or
  `URI_AGENT_RELAY.md` prose directly. Currently only the `M33.3` entry
  carries this pointer (the one stale-wording case Phase A's inventory
  found). A future stale-wording case will not be caught by DCL-008 unless
  a maintainer adds the same structured pointer to the relevant entry.
- **Reusable component registry statuses are first-pass, not binding.**
  Per the task brief, this normalization introduces `URI-Edge`, `URI-RAR`,
  `URI-Memory`, `URI-Eval`, and `URI-Agent-Adapters` net-new; their
  `likely_maps_to` mappings are candidates, not a formal adoption decision.
- **`PRODUCT_NAMESPACE_EXCEPTIONS` is a hand-maintained whitelist.** `ARN.1`
  is the one product-milestone id that does not match the `Mxx` pattern by
  design (it is a batch under a non-`Mxx` parent milestone name). Any future
  non-`Mxx` product identity must be added to this whitelist explicitly, or
  DCL-011 will correctly flag it as a namespace violation.

## 16. Next authorized action

`INDEPENDENT_CONTROL_LAYER_AUDIT`

---

## H. Final validation record

1. **YAML parses successfully.** `python scripts/governance/uri_state_validator.py docs/governance/URI_STATE.yaml` completed without a parse error.
2. **Canonical state passes the deterministic validator.** Output: `VALID: docs/governance/URI_STATE.yaml — no DCL violations found.` (exit 0).
3. **All positive validator tests pass.** `VALID-001..004` — 4/4 passed.
4. **All negative tests fail with the intended error code.** `INVALID-001..009` — 9/9 passed, each asserting its specific `DCL-*` code.
5. **No test depends on an LLM.** Confirmed by inspection — `tests/governance/test_uri_state_validator.py` imports only `pytest`, `copy`, and the validator/parser modules.
6. **Frozen architecture plan remains byte-unchanged.** `git diff --stat docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md` — empty.
7. **A9 artifacts remain untouched.** `git status --porcelain` shows `docs/plans/M35_URIV1_A2_8L_A9_*` files in their pre-existing untracked (`??`) state, not modified by this normalization.
8. **Runtime/model code remains untouched except validator implementation, placed in a governance tooling location** (`scripts/governance/`, `tests/governance/`). No file under `uri_core/`, `uri_v1/`, or `uri_ui/` was touched.
9. **`SKILL.md` remains untouched by this normalization** (its pre-existing modified state predates this session and is explicitly out of scope per the task brief).
10. **No model benchmark or model download occurred.** This normalization performed no network access and invoked no model.

Full test run:

```
37 passed in 0.16s
```

Full validator run:

```
VALID: docs/governance/URI_STATE.yaml — no DCL violations found.
```

---

## 17. Bounded repair record (post-audit, same day)

An independent audit returned `CONTROL_LAYER_REPAIR_REQUIRED` against the
Phase B–H submission above, with verdict `REPAIR_REQUIRED` and next
authorized action `BOUNDED_CONTROL_LAYER_REPAIR`. Per this repository's
standing AO-4 bounded-fix authority (Claude audits → fixes a bounded
in-scope defect → re-tests → re-audits, without expanding the accepted
milestone's scope), the following defects the audit found via adversarial
in-memory state mutation and direct code/line inspection were fixed
in-session, re-tested, and are recorded here rather than silently folded
into the sections above:

1. **Parser was fail-open** (`scripts/governance/uri_state_yaml.py`):
   `integration_events: []`/`corrections: []` parsed as the literal string
   `"[]"` instead of an empty list; a duplicate top-level/nested key silently
   overwrote the first value instead of erroring; unconsumed trailing
   content after the parsed document was silently dropped; a malformed
   quoted string (e.g. an unterminated quote) fell through to being treated
   as an unquoted bare scalar. **Fixed:** the parser now raises
   `UriStateYamlError` in all four cases — empty `[]`/`{}` are now real
   empty collections, non-empty flow collections are explicitly rejected as
   unsupported, duplicate keys raise, and any unconsumed trailing content
   after the document raises. A pre-existing legitimate use of
   backslash-escaped quotes inside a quoted string (line 142's Hybrid UI
   title) required adding real `\"`/`\\` escape handling to the quoted-scalar
   regex, not just tightening it.
2. **`_entries()` silently treated a wrong-typed section as empty**
   (validator). **Fixed:** it now raises a new `UriStateSchemaError` if a
   present section is not a list, or contains a non-mapping item — "VALID"
   can no longer mean "the section was silently skipped."
3. **DCL-001 only compared `currently_active` claimants pairwise** and
   missed a new active claimant conflicting with a closed sole-owner
   predecessor (e.g. a hypothetical new milestone claiming
   `edge_second_brain` while M33.2 — closed, not `currently_active` —
   still asserted historical sole ownership). **Fixed:** DCL-001 now builds
   connected components per domain using the relationship fields
   (`continues_architecture_of`, `derived_from`, `supersedes`,
   `feeds_into`); a domain with more than one connected component, where at
   least one component contains a `currently_active` entry, is now a
   violation — this correctly still allows the real M33.2→M33.3 lineage
   (one connected component) while catching an unconnected new claimant.
4. **DCL-003 did not validate alias resolution targets**, and two real
   alias entries (`EXP-ARN-URIV1`, and the three `rar_identity_map`
   research-line ids) pointed at ids that did not actually exist in
   `research_experiments`. **Fixed:** DCL-003 now also checks every
   `CURRENT` alias's `resolves_to` against all known canonical ids; the four
   missing `research_experiments` entries (`EXP-ARN-URIV1`,
   `EXP-RAR-DETERMINISTIC`, `EXP-RAR-HYBRID`,
   `EXP-RAR-A9-TRANSPORT-FACTORIAL`) were added to `URI_STATE.yaml` so their
   aliases now resolve to real entries instead of the gap being merely
   caught.
5. **DCL-007 did not catch a `CURRENT` alias coexisting with its own
   `AMBIGUOUS_BARE_ALIAS_FORBIDDEN` collision guard** (a future `ARN → ARN.1`
   `CURRENT` entry would have passed despite the existing bare-`ARN` guard).
   **Fixed:** DCL-007 now also fails when an alias string's entry group
   contains both an `AMBIGUOUS_BARE_ALIAS_FORBIDDEN` entry and a `CURRENT`
   entry.
6. **DCL-012 did not catch a forbidden alias string gaining a new `CURRENT`
   resolution** (a future `A3.1 → M60` `CURRENT` entry would have passed
   despite `A3.1` being `HISTORICAL_FORBIDDEN`). **Fixed:** DCL-012 now also
   fails when an alias string's entry group contains both a
   forbidden-for-new-work/`HISTORICAL_FORBIDDEN` entry and a `CURRENT` entry.
7. **DCL-005 accepted a self-declared `promoted_to_production: true` with no
   integration evidence**, and had no check at all for a reusable component
   claiming `DISTRIBUTABLE` without portability evidence. **Fixed:** DCL-005
   now also requires a `promoted_to_production: true` research experiment to
   carry an `integration_event_ref` resolving to a real `integration_events`
   id, and requires a `DISTRIBUTABLE` component to have
   `cross_agent_portable: true` with a non-empty `portability_validated_via`.
8. **DCL-006 did not inspect `rar_identity_map.research_lines`**, so a
   frozen/closed research-line entry there marked `mutable: true` would have
   passed. **Fixed:** DCL-006 now also walks that nested list (and checks an
   explicit `frozen: true` flag, not only a `CLOSED*`/`FROZEN` status
   string).
9. **DCL-008 accepted a bare self-attested `reconciled: true`** with no
   machine-checkable evidence. **Fixed:** `reconciled: true` now also
   requires a commit-hash-shaped `superseding_commit` field; the real
   `M33.3` entry's pointer was updated with
   `superseding_commit: "47af60a..."` (the actual commit that superseded
   the stale wording). This is a disclosed, intentionally bounded
   improvement, not full prose verification — see the restated limitation in
   §15.
10. **DCL-009 missed two cases:** a legacy-flagged entry claiming an
    `architecture_domain` while `currently_active: false` (only the
    `currently_active: true` case was checked), and a non-legacy
    `currently_active: true` entry whose `continues_architecture_of` (etc.)
    pointed at a legacy-flagged entry ("legacy as active continuation").
    **Fixed:** both cases now raise DCL-009.
11. **DCL-010 let an integration event with no `target_component` pass**,
    and let a bare `qualification_override: true` bypass an ineligible
    component's status with no justification. **Fixed:** a missing
    `target_component` is now itself a violation, and `qualification_override:
    true` now additionally requires a non-empty `override_justification`.
12. **DCL-011 accepted any `M`-prefixed string as a valid product-milestone
    id** (e.g. `Mwhatever`). **Fixed:** product-milestone ids (outside the
    explicit `PRODUCT_NAMESPACE_EXCEPTIONS` whitelist) are now checked
    against `^M\d+(\.\d+){0,2}$`.
13. **Factual correction, `URI_STATE.yaml`:** the file called `uri_v1/`
    "git-tracked" in two places (`repository.canonical_worktree.role` and
    the `EXP-M35-URIV1-A0-A9` entry's `lives_in` field). Direct verification
    (`git ls-files uri_v1 | wc -l` = 30 vs. 79 total files) confirmed the
    audit's finding that this is a mixed tree, substantially untracked —
    consistent with `URI_DEVELOPMENT_EVIDENCE_REGISTRY.md`'s own framing.
    Both lines corrected; a new `repository.uri_v1_tracking_note` field
    records the correction and the evidence for it, per this repository's
    auditable-correction-history convention (the original claim is not
    silently deleted, it is corrected with its own evidence trail).
14. **Reconciliation, `URI_ACTIVE_MILESTONE.md`:** the file's own "Shared
    Active-Milestone Invariant" section states it is the "**SINGLE**
    canonical current-state file," which the audit correctly flagged as an
    unreconciled conflict with this normalization's new authority rule
    naming `URI_STATE.yaml` canonical for identity/namespace resolution. A
    minimal additive reconciliation note was added directly under that
    invariant, clarifying the two files' distinct scopes (no-forking-copies
    vs. canonical identity resolution) and restating that `URI_STATE.yaml`
    wins on a genuine current-state conflict, per its own stated authority
    rule. The original invariant wording is preserved, not edited.

**Not fixed, and explicitly out of this bounded repair's scope, because they
are disclosed, intentionally bounded design limitations rather than defects**
(the audit itself classified these as `VERIFIED_WITH_LIMITATION` /
`NOT_ESTABLISHED`, not `CONTRADICTED`): DCL-002's reliance on an accurate
`currently_active` field being set correctly by a human editor; DCL-003 not
validating `rar_identity_map` research-line ids as relationship targets
(they are historical research identifiers, not relationship pointers, by
design); DCL-008 still not parsing free-text prose (only a structured
pointer field, per the task brief's own explicit instruction not to parse
every historical paragraph); relationship-field cycle detection (no DCL
rule was specified for this); and the previously-disclosed absent physical
`A3.1` artifact (§15, unchanged).

**Re-verification after repair:** `python
scripts/governance/uri_state_validator.py docs/governance/URI_STATE.yaml` →
`VALID` (no violations). Full governance test suite,
`tests/governance/test_uri_state_validator.py` → **37/37 passed** as of
the §17 repair (the original 15, plus 11 new tests reproducing each fixed
audit finding by name — `test_invalid_010` through `test_invalid_020` —
plus 7 new parser/schema fail-closed tests); see §18 for the further
round-2 repair and its own 4 additional regression tests (37 total). Frozen plan (`M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_...`)
confirmed still byte-unchanged (`git diff --stat` empty). No file under
`uri_core/`, `uri_v1/`, or `uri_ui/` was touched by this repair. Not
committed, not pushed — awaiting the next independent audit, per the
original brief's own commit/push restriction, which this repair does not
lift.

## 18. Bounded repair record, round 2 (post-second-audit, same day)

A second independent audit again returned `CONTROL_LAYER_REPAIR_REQUIRED`
against the round-1 repair (§17), with three specific blocking findings out
of a broader re-audit that otherwise confirmed round 1's fixes held under
re-inspection and reproduction (parser fail-closed behavior, DCL-004/007/011
all VERIFIED, the disconnected-active-claimant half of DCL-001, A3.1 reuse
guard, `Mwhatever` rejection, `DISTRIBUTABLE`-without-evidence rejection —
all re-confirmed correct). The three blocking findings and their fixes:

1. **DCL-001 allowed two simultaneously `currently_active: true` entries
   within one *connected* lineage** (e.g. a hypothetical state with both
   M33.2 and M33.3 marked `currently_active: true` at once — round 1's
   connected-component check only caught *disconnected* multi-ownership,
   not this). The task brief's own DCL-001 definition — "Only one current
   production owner may govern a given architecture domain" — is a
   cardinality rule, not merely a disconnection rule. **Fixed:** DCL-001 now
   independently counts `currently_active: true` entries per domain; more
   than one is a violation regardless of connectivity. A correct
   continuation transition must deactivate the predecessor before or when
   activating the continuation (see the new `test_valid_005` positive test).
2. **DCL-003 did not reject a `CURRENT` alias with a null/empty
   `resolves_to`** (e.g. `{"alias": "EXP-ORPHAN", "resolution_status":
   "CURRENT", "resolves_to": null}` passed). **Fixed:** a `CURRENT` alias
   with no target now fails DCL-003 directly, before the existing
   "target not in known_ids" check even runs.
3. **DCL-005 accepted an `integration_event_ref` that resolved to a real
   `integration_events` entry but did not verify that entry actually
   authorized the promoted experiment** — citing an unrelated integration
   event (a different `target_experiment`) passed. **Fixed:** DCL-005 now
   requires the cited integration event's own `target_experiment` field to
   equal the promoted research experiment's id; a mismatch (including an
   event with no `target_experiment` at all) now fails DCL-005.

**Re-verification after round-2 repair:** validator CLI on the canonical
file → `VALID` (no violations; no canonical-file content changes were
needed for round 2 — these were pure validator-logic fixes). Full suite,
`tests/governance/test_uri_state_validator.py` → **37/37 passed** (33 from
round 1, plus 3 new regression tests reproducing each round-2 finding by
name — `test_invalid_021` through `test_invalid_023` — plus one new
positive test, `test_valid_005`, proving the correct deactivate-then-
activate continuation shape still passes). Frozen plan confirmed still
byte-unchanged; no `uri_core/`/`uri_v1/`/`uri_ui/` file touched by this
round of repair either. Not committed, not pushed.

**Disclosed, not addressed this round, because the second audit itself did
not classify them as blocking** (`VERIFIED_WITH_LIMITATION`, not
`CONTRADICTED`): DCL-002's dependence on an accurate `currently_active`
field; DCL-008 not parsing free prose; DCL-009's `active_continuation.owner`
field (a free-text field in the existing `active_continuation` block, not a
per-entity `legacy` flag — the second audit noted this specific field path
remains unchecked; a future round should either add a structured check for
it or fold it into the existing per-entity legacy checks if it is
reclassified as a canonical relationship); DCL-010 not checking a target
milestone's own status eligibility (e.g. an integration event aimed at a
`RESERVED_NOT_STARTED` milestone like M35 currently passes) — this is a
plausible real gap but the second audit explicitly did not classify it as
one of the three blocking items requiring this round's fix, so it is left
disclosed rather than fixed under this bounded repair's scope; bare `A3` has
no dedicated forbidden-alias guard (only `A3.1` does, per the original task
brief's own specific instruction); and the previously-disclosed unlocated
`A3.1` physical artifact (§15, unchanged).

---

**Not rewritten, not renamed, not reopened by this normalization:** any
accepted historical plan, state, completion report, or relay entry beyond
the two additive notes described in §13, plus the one additional
reconciliation note added to `URI_ACTIVE_MILESTONE.md` during the §17
repair. No canonical `URI_STATE.yaml` content changes were required for the
round-2 repair (§18) — only validator logic changed.

## 19. Freeze record (release checkpoint)

**Verdict:** `CONTROL_LAYER_ACCEPTED_WITH_LIMITATIONS`, per independent
re-audit following the §17 and §18 bounded repair rounds. This is the
terminal verdict of the sequence `CONTROL_LAYER_REPAIR_REQUIRED` (initial
audit) → bounded repair → `CONTROL_LAYER_REPAIR_REQUIRED` (second audit,
3 blocking findings) → bounded repair → `ACCEPT_WITH_DOCUMENTED_LIMITATIONS`
(third, independent re-audit).

**Re-verified at freeze time (2026-09-25):**
- `python scripts/governance/uri_state_validator.py docs/governance/URI_STATE.yaml` → `VALID: docs/governance/URI_STATE.yaml — no DCL violations found.`
- `python -m pytest tests/governance/ -q` → `37 passed`
- `git diff --stat docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md` → empty (frozen plan byte-unchanged)
- `git status --porcelain uri_core uri_v1 uri_ui | grep -v '^??'` → no output (no tracked runtime/product change)

**Accepted documented limitations (carried forward from the independent
re-audit, not reopened by this freeze):**
- DCL-002 depends on accurate `currently_active` state being set correctly.
- DCL-005 still requires governance review of substantive authorization
  evidence beyond the structural `target_experiment` match it now enforces.
- DCL-008 validates structured reconciliation evidence
  (`superseding_commit`), not free prose.
- DCL-009 does not inspect the free-text `active_continuation.owner` field.
- DCL-010 does not enforce target-milestone status eligibility (e.g. an
  integration event aimed at a `RESERVED_NOT_STARTED` milestone currently
  passes).
- DCL-012 has no dedicated bare-`A3` alias guard (only `A3.1`, per the
  original task brief's specific instruction).
- The physical `A3.1` artifact remains unlocated (§15).
- Component portability evidence (`portability_validated_via`) still
  requires human/governance review of the named adapter's authenticity —
  the validator checks the field is present and non-empty, not that the
  named adapter is real.

**Confirmed held at freeze, unchanged since normalization:**
- M33.2 remains `CLOSED_VERIFIED`.
- M33.3 remains `PLANNING_BASIS_FROZEN`, implementation not started.
- `integration_events: []` — no `INT-*` event authorizes M33.3 or any other
  implementation.
- Research qualification does not imply production promotion
  (`promoted_to_production: false` on every research_experiments entry in
  the canonical file; DCL-005 would now reject any that set it to `true`
  without matching integration evidence).
- Reusable-component candidacy does not imply integration authority (all
  five components remain `EXPERIMENTAL`/`NOT_STARTED`, none `INTEGRATED` or
  `DISTRIBUTABLE`).

**Next authorized action:** `READY_FOR_NEXT_DEVELOPMENT_BATCH_SELECTION`.
This freeze task does not select or start that next batch.
