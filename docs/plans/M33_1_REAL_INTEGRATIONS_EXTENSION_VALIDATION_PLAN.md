# M33.1 — Real Integrations & Extension Validation

**Status:** M33.1 is **CLOSED / ACCEPTED**. Batches 1, 2, and 3 remain CLOSED / ACCEPTED (`d78366d`/`0558a99`, `dd4863a`, `0fcdf29`); Batch 4 is the accepted closure record — see §13.H. The generic natural-language/UI lifecycle seam (`uri_core/external/lifecycle_intent.py`) is wired into live `/ask` (§13.G), via a narrow per-request executor closure added to `server.py`'s `ask()` — never a change to `canonical_execution.py`, `multi_action_dispatch.py`, `orchestrator.py`, `approval_gate.py`, or `registry_bridge.py`.

**Authority:** This supersedes the M33 bridge blueprint §10 sketch for the remainder of M33.1. Batch 1 is CLOSED / ACCEPTED at `d78366d` / `0558a99`. Batch 2 entry slice is authorized.

## 1. Evidence and authority

M33.1 proves that URI can acquire and manage external abilities through the landed generic external-capability bridge. It is neither M33.2, M33.3, nor M33.4.

Live source establishes: `ExternalCapabilityStore` owns persisted descriptor and skill-style lifecycle records; `ExternalCapabilityPublisher` creates a fresh registry generation from enabled qualified records; and `MultiActionDispatch` remains the execution, permission, and approval path. Batch D's `transport_handler()` selects only the closed `in_process`, `cli`, or `http` adapter vocabulary and validates input/output. `ConnectedServiceStore`/`ExternalCredentialStore` are separate from installable-capability lifecycle; the service store currently does not publish capabilities or enter user-context composition. `GraphifyIndex` derives service records only when given a service store. `server.py` builds a cached per-user registry once, with no lifecycle mutation route that swaps it or refreshes discovery/Graphify.

The model proposes; URI validates, grants, approves, dispatches, executes, stores evidence, and audits. An integration manifest, health state, generated SKILL.md, connection record, or Graphify record cannot grant permission, approval, credential access, registration, or execution authority.

## 2. Frozen product taxonomy

| Term | Frozen meaning | Not interchangeable with |
| --- | --- | --- |
| Connected Service | Account/provider-level external connection with OAuth, API-key, or session credentials; connect, configure, health, refresh, revoke, disconnect; exposes authenticated capabilities. | Skill package or credentialless individual action. |
| Skill | Installable capability/workflow package: install, update, enable, disable, remove; may depend on Connected Services; may expose capabilities. | Provider account connection. |
| Capability | Individual registered executable action with schema, permission, effect/risk, approval, handler, result, evidence. | Package, provider, or discovery item. |
| Workflow | Runtime-validated composition of registered capabilities/actions. | Installation or authorization grant. |
| Discovery / Graphify | Derived navigation/index layer reflecting authoritative state. | Registry, credential store, permission authority, or execution surface. |

Services are not Skills, and Skills are not Services. A Skill can declare a service dependency, but URI verifies it as a precondition.

## 3. Frozen batches and milestone boundaries

1. **Batch 1 — Foundations:** CLOSED / ACCEPTED: descriptor/store, encrypted credentials, lifecycle primitives, status/Graphify seams, and persisted removal at `d78366d`.
2. **Batch 2 — pinned `yt-dlp` CLI Skill** (corrected from "Agent Reach": real Skill-package/CLI acceptance case, 2026-09-19 — see §7). CLOSED / ACCEPTED at `dd4863a`.
3. **Batch 3 — GitHub Skill / Package Lifecycle** (`strip-json-comments-cli`, §11). CLOSED / ACCEPTED at `0fcdf29`.
4. **Batch 4 — M33.1 Closure:** extension-matrix proof, natural-language/UI lifecycle seam, live `/ask` wiring, compatibility, and regression evidence. CLOSED / ACCEPTED — see §13.H.

Firecrawl is not an M33.1 acceptance case or closure prerequisite. Generic HTTP/API capability support remains part of the external-capability bridge; Firecrawl may later be onboarded as an optional Connected Service, but URI never depends on it for crawling, Sources, Watches, or knowledge functions.

**M33.1 — Acquire / manage abilities.** It may emit bounded evidence results but never grants an integration direct durable-knowledge write authority.

**M33.2 — Edge / Second Brain Foundation.** This is a separate reserved milestone; it does not implement Sources, Watches, crawling, or Knowledge Fabric.

**M33.3 — Unified URI Interaction & Capability UI.** This is a separate reserved interaction/UI milestone; it does not change the M33.1 authority model or open knowledge ingestion.

**M33.4 — Knowledge Fabric / Sources / Watches.** A future M33.4 Knowledge Gateway must validate every candidate's provenance, user scope, consent, retention, and policy before any durable write. No M33.1 integration gets unrestricted direct-write authority merely by being installed or connected.

## 4. Batch 1 residual decisions — mandatory before Batch 2

### A. Store-root consistency

`DEFAULT_USER_STATE_ROOT` and `server.py`'s `_USER_STATE_ROOT` both currently spell `uri_workspace/users`, so there is no present path split. That equality is accidental, not composition: default-created `ExternalCapabilityStore` in publisher/permission resolver, `ConnectedServiceStore` in `connection_status`, and nested `ExternalCredentialStore` do not receive the configured runtime root.

**Decision:** `_build_user_context`, or one explicit integration composition object constructed there, must retain exactly one `ExternalCapabilityStore`, `ConnectedServiceStore`, and `ExternalCredentialStore`, all with `root=_USER_STATE_ROOT`. Publisher, external permission resolver, status projection, and Graphify refresh receive those exact instances. Defaults are allowed only for standalone/local tooling, never production request handling.

**Acceptance test:** override `_USER_STATE_ROOT` to a temporary root and build an authenticated context. Install/connect through its lifecycle seam; assert descriptor state, encrypted credential file, connection status, published registry, and Graphify service/capability records all occur only under that root.

### B. Immediate live removal propagation

`ExternalCapabilityStore.remove()` deletes descriptor and credential; a later publisher call omits it. The cached registry and discovery surface are not republished after lifecycle mutation.

**Decision:** install/enable/disable/update/remove must be one runtime lifecycle operation: mutate authoritative state; build a fresh registry atop fixed native capabilities; atomically swap the context registry and discovery engine; refresh derived capability/service Graphify; return sanitized status. Disable/remove make a capability unselectable and undispatchable on the next request—without restart, cache expiry, or login. Disconnect/revoke does the same for service-exposed capabilities; remove deletes its credential.

**Acceptance test:** in one authenticated context execute an enabled action; disable and prove next discovery/dispatch denies; re-enable and prove return; remove and prove registry, capability discovery, dispatch, and Graphify omit it and the encrypted entry is absent. No context rebuild/restart between assertions.

### C. `LifecycleController.remove()`

It is an in-memory transition used only by its unit test. `ExternalCapabilityStore.remove()` is the persisted hard-removal authority and does not invoke it.

**Decision:** delete `LifecycleController.remove()` and its isolated test in the residual correction. Do not wire a duplicate authority. The store removal is the sole hard-removal operation; any absent-event record belongs in existing evidence/audit, not a retained deleted state.

### D. Settings/surface collision

**Decision:** existing conceptual home is **System → Capabilities**. Future UI has **Skills** (packages, capabilities/dependencies) and **Connected Services** (accounts, scopes, health, connect/revoke/disconnect). A capability is a derived drill-down of its owner, never competing settings. Provider/model endpoint and API-key configuration remains **Brain & Providers**. No UI ships in Batch 2 or this task.

## 5. Frozen credential contract

`ExternalCredentialStore` retains provider-key-grade security: Fernet encryption at rest derived from `URI_EXTERNAL_CREDENTIAL_SECRET`, strict user-scoped paths, atomic same-directory replace, and fail-closed construction on a missing secret. Wrong secret, malformed ciphertext, and corrupt JSON yield no usable credential, never a secret/ciphertext/decryption error to callers.

Secret material is forbidden in prompts, model context, Graphify, evidence, audit/log metadata, status payloads, descriptors, and exceptions. Disconnect, revoke, and Skill removal delete local credential before success returns. Provider revocation, if applicable, is separately audited best-effort action whose failure cannot retain usable local credentials.

Rotation explicitly decrypts with old secret, atomically re-encrypts with new secret, validates readback, and leaves no plaintext/temp file; it remains rollback-safe until readback succeeds. There is no silent plaintext/other-store migration. A versioned migration validates then atomically writes or quarantines malformed state. Unrecoverable decryption means needs-authentication/not-connected and immediate retirement, followed by re-authentication—never a stale connected claim.

## 6. Frozen generic path

Descriptor → qualification → configuration/authentication where required → explicit enable/grant → fresh registry publication → existing permission/approval/dispatcher → closed adapter → validated result/evidence → derived discovery/Graphify refresh. No vendor branch in `canonical_execution.py`, `MultiActionDispatch`, `ToolDispatcher`, approval gate, or model reasoning. Service state is a precondition/presentation fact, never permission. URI stays authoritative for permissions, grants, approvals, credential retrieval, lifecycle, dispatch, evidence, audit, and isolation.

## 7. Batch 2 — CLI Skill acceptance, corrected vendor choice

### Live vendor finding (re-verified independently against the real upstream, 2026-09-19)

The current upstream named **Panniantong/Agent-Reach** is not the assumed stable video CLI, and the live finding above understates it. Direct inspection of `agent_reach/skill/SKILL.md` and the project README confirms this is **positioned by its own authors as an installer/doctor/config tool, explicitly "not a wrapper"** — after install, the agent calls upstream tools directly per a routing table with no single frozen API. Its `agent-reach` command surface is install/update/doctor/configure/`skill --install`. Beyond the previously-listed `curl`, `gh`, `yt-dlp`, `twitter`, `rdt`, `opencli`, `mcporter`, the SKILL.md also routes to a `bili-cli` tool and a `boss` backend that drives a **Chromium browser over CDP** (`--cdp-url`) for Reddit/Facebook/Instagram/XiaoHongShu. Each platform "channel" (`twitter.py`, `youtube.py`, etc.) maintains its **own ordered primary+fallback backend list** that the tool reorders and re-probes automatically at runtime when a backend breaks (its own docs cite a real June-2026 yt-dlp/Bilibili breakage as the reason this exists). Some channels need Node.js, manual cookie-file imports, or an MCP server (LinkedIn via `mcp-server-linkedin`).

That confirms and sharpens the original conclusion: URI cannot generically execute arbitrary generated instructions, and no vendor-specific core execution branch is permitted. It also means **"pin one bounded Agent Reach channel/backend profile" is the wrong correction** — Agent-Reach's own package is a self-reconfiguring multi-backend router with browser-automation and MCP dependencies URI has no infrastructure for and no need to acquire just to prove a bounded CLI Skill. Vendoring or pinning a specific Agent-Reach revision still means depending on that router's own update/backend-reordering logic as an opaque black box, which is a *worse*, not better, fit for a "fixed executable/argv template" than picking a narrow tool directly.

### Corrected acceptance case: pin `yt-dlp` directly, not the Agent-Reach package

The M33 blueprint's own §10 already recorded this exact alternative as deliberately left open: *"Running pinned `yt-dlp` directly would deliver the same CLI proof without a supply-chain review."* The live Agent-Reach finding above is the resolution of that open question, not a dead end — it confirms the lower-risk path was correct. `yt-dlp` itself is a single-purpose, independently well-known CLI (no installer indirection, no multi-platform router, no browser automation, no MCP dependency) whose `--dump-json` output is a fixed, well-documented, machine-parseable schema, which is exactly what URI's existing closed CLI adapter (`uri_core/external/adapters/cli.py`: fixed descriptor-owned argv list, `shell=False`, JSON on stdin/stdout, bounded timeout) is already built to represent, with zero adapter-layer changes needed.

Batch 2's acceptance case is corrected to: **pin one specific, version-locked `yt-dlp` release as a URI-authored Skill descriptor** — never installing, importing, or depending on the `agent-reach` package, its `SKILL.md`, or its router. "Agent Reach" as a named upstream project is dropped from Batch 2's scope entirely; it is not the right acceptance case at any pinned channel/backend, for the reasons above, not merely at the specific channel Codex evaluated.

### Minimum trust boundary for installing a real external Skill (new — not previously stated in this plan)

Batch A's `Qualifier.qualify()` validates a descriptor's *shape* (contract version, schema constructs) — it does not and cannot evaluate whether a `transport_config.command` argv list is itself safe to run. Nothing in `register_descriptor`/`ExternalCapabilityPublisher.publish()` restricts *who* may register a descriptor or *where* its command list came from. This is inert today only because every registered descriptor so far (fixture profiles, `remember_fact`'s in-process mapping) is authored by URI's own team, not submitted by an end user or proposed by a model at runtime.

**Decision:** for Batch 2 and for any future real external Skill, the descriptor (including its exact pinned command/argv) must be **developer-authored and code-reviewed at implementation time, committed to the repository, and never constructed from end-user input, model output, or a runtime "install by URL/package name" flow**. No endpoint or lifecycle seam in Batch 2 accepts an arbitrary descriptor from a request. This must hold until a real install-time integrity/provenance check (signature, allowlist, or equivalent) exists — which is explicitly out of Batch 2's scope, not assumed away.

## 8. Batch 3 — GitHub Skill / Package Lifecycle

**Goal:** prove URI can acquire a real GitHub-hosted Skill/package and manage it through generic contracts. GitHub is an acquisition/provenance surface, not execution authority. A repository, its README, or `SKILL.md` cannot confer permission, approval, credential access, dispatch authority, or a successful lifecycle result.

**Required lifecycle:** inspect/discover the repository; identify a structured package/manifest/SKILL contract; qualify it before execution; install only its reviewed artifact into a URI-managed location; register declared capabilities; enable, disable, update, and remove; retire live capabilities immediately; refresh Discovery/Graphify; and preserve user isolation and URI's permission, approval, dispatch, evidence, and audit gates.

**Frozen safety rules:** the model and user may request a registered target but cannot construct an arbitrary repository URL, revision, manifest, argv, handler, or installer command. `SKILL.md` prose is descriptive only; it must be projected through a validated descriptor before execution. Installation may use a shared immutable verified-artifact cache only when it contains no user state or credentials; the installed/enabled record, grants, status, evidence, and removal authority remain strictly user-scoped. Update selects a separately qualified immutable revision and atomically swaps only after its validation succeeds. Removal deletes the user's installation state and retires it from every live surface without deleting another user's state.

No GitHub-, package-, or vendor-specific branch may be added to canonical execution, the orchestrator, `MultiActionDispatch`, the generic adapters, permission resolution, approval handling, or Graphify.

### Batch 3 entry criteria

Batch 3 may begin only when all of the following are recorded in its task-initiation package:

1. A specific public GitHub repository, immutable commit/tag, license/provenance record, and repository layout have been independently inspected; mutable branch names are not an execution input.
2. The target exposes a bounded, reviewable package/manifest contract and at least one useful capability that can be represented by existing generic adapter contracts. Browser automation, arbitrary shell installation, opaque self-updaters, MCP sidecars, cookies, and runtime-generated commands are excluded.
3. The exact allowed artifact files, dependency lock, installation location, update source revision, uninstallation semantics, and capability projection are specified. No package install hook or unreviewed script runs merely because it is present in the repository.
4. The implementation plan identifies how qualification, integrity/provenance checks, atomic install/update, rollback/quarantine, per-user lifecycle state, live retirement, and Graphify refresh will be tested.
5. Acceptance evidence is specified for discovery/inspection, rejected qualification, install/register/enable/execute, disable/re-enable, update, remove, stale-session retirement, cross-user denial, Graphify refresh, permissions/approvals/evidence, and Gmail/Drive/native compatibility.

**Current entry status:** target selected and frozen — see §11. Entry criteria 1–5 above are satisfied by §11's contract. Implementation is authorized to begin against §11 exactly as written; NOT STARTED means no code has been written yet, not that the gate remains open.

## 9. Batch 4 — M33.1 Closure

Batch 4 consolidates the remaining work where it is materially coherent: extension-matrix proof, the natural-language/UI lifecycle seam, compatibility, and final regression/live evidence. It does not add a mandatory HTTP vendor.

| Mechanism | Required proof | M33.1 status |
| --- | --- | --- |
| Real CLI capability — pinned `yt-dlp` | Qualified descriptor, generic CLI execution, live lifecycle retirement | Proven, Batch 2 (`dd4863a`) |
| OAuth Connected Service — Gmail | Existing consent/connection lifecycle and canonical compatibility | Re-confirmed in closure, §13 |
| Local in-process capability — `remember_fact` | Existing common executor and grant/availability behavior | Re-confirmed in closure, §13 |
| GitHub-hosted Skill/package — `strip-json-comments-cli` | Batch 3 acquisition, qualification, managed install/update/removal, generic execution | Proven, Batch 3 (`0fcdf29`) |
| Manifest/SKILL-style package or equivalent | Prove only if structurally distinct from the GitHub package mechanism; otherwise record that it is not double-counted and use another materially distinct mechanism | **Closure decision (§13): not proven separately.** A Skill installed from a manifest/lockfile (`strip-json-comments-cli`) and a Skill installed as a static pinned binary (`yt-dlp`) already span the two structurally distinct installation shapes this bridge supports; a `SKILL.md`-driven mechanism was deliberately rejected as an acceptance case in §7 (Agent-Reach) precisely because URI cannot safely execute manifest prose as authority. Manufacturing a fifth proof here would either re-exercise the same generic path a fourth time or reopen the rejected SKILL.md-execution question - neither adds real coverage. |

Generic HTTP/API capability support remains reusable infrastructure, not an M33.1 vendor-onboarding requirement. Firecrawl is optional future work only.

The natural-language/UI seam may request lifecycle intent such as “install [registered package],” “remove [registered package],” “enable [capability],” or “connect GitHub.” URI resolves the registered target, validates eligibility, obtains needed confirmation/approval, runs the lifecycle operation, and returns sanitized actual state. Neither model nor UI can invent an id, credential, registration, grant, or success.

## 10. M33.1 exit criteria

M33.1 closes only with evidence that: the pinned `yt-dlp` CLI proof remains compatible; the GitHub Skill/package lifecycle works end-to-end; install/enable/disable/update/remove and immediate live retirement work; credentials, grants, and lifecycle state remain isolated and encrypted where applicable; Discovery/Graphify refresh correctly while staying derived/non-authoritative; every proven mechanism uses generic contracts with no vendor-specific execution-core branch; the four required matrix mechanisms and any qualifying fifth distinct mechanism are evidenced; the natural-language/UI lifecycle seam works; Gmail/Drive/canonical/native execution remains compatible; and full regression has zero new failures plus component, integration, canonical-loop, and live user-visible evidence.

## 11. Batch 3 frozen candidate — `strip-json-comments-cli` (2026-09-19)

An initial candidate proposal (v3.0.0, "commit" `16523e04be035a62187650e2ddef2d572ec2978a`, update source v2.0.2 `e614aab7ca463a09d7978145d52f0d154df3c1cc`) was independently audited against the real npm registry and the real GitHub repository via `gh api`, not taken on trust. That audit found and this section corrects: the two cited hashes are annotated-**tag-object** SHAs, not commit SHAs (`gh api repos/.../commits/16523e04...` returns "No commit found for SHA"); the CLI's real dependency closure includes `meow@^12.0.1`, which carries its own `"prepare": "npm run build"` lifecycle script (confirmed directly from the npm registry); the real `cli.js` (fetched and read at the tag) accepts an optional positional file-path argument (`fs.readFileSync(input, 'utf8')`) and its stdout is raw transformed text, not JSON — neither matches this plan's contracts as originally assumed.

### A. Pinned revisions (dereferenced commits, not tag objects)

- v3.0.0 → commit `d1f67f37c0543fbc06a107b7df4ea034476c98d7` (dereferenced from tag object `16523e04be035a62187650e2ddef2d572ec2978a`; matches npm's own published `gitHead` for this version).
- v2.0.2 (update source) → commit `f820f90720ae34faf0b05dea82c99432da4131dc` (dereferenced from tag object `e614aab7ca463a09d7978145d52f0d154df3c1cc`; matches npm's published `gitHead`).
- Any future revision pin in this repository must record the dereferenced commit SHA (`git rev-parse <tag>^{commit}` or the registry's own `gitHead` field), never a bare tag-object SHA, so tooling that expects a commit object behaves correctly.

### B. Generic CLI descriptor output mode (adapter-level, not vendor-specific)

`uri_core/external/adapters/cli.py`'s descriptor contract gains one new, fully generic field: `output: "json" | "text"`, defaulting to `"json"` (existing behavior for every descriptor that does not set it, including the Batch 2 `yt-dlp` descriptor — zero behavior change there). `output: "text"` means the adapter does not `json.loads()` stdout; it instead wraps the raw stdout string as `{"text": <stdout>}` and returns that through the same structured URI result envelope every other CLI action already uses. This is a capability of the adapter available to any future text-transform Skill, not a `strip-json-comments-cli`-specific branch.

### C. Installation contract — reviewed lockfile, not a hand-picked tarball list

The original candidate's "pin the N direct tarballs" approach is rejected as unsound: it does not reliably cover the full transitive dependency closure for an arbitrary npm package, and would need re-deriving by hand for every future npm-based Skill. Instead:

- A developer-authored, code-reviewed `package.json` + `package-lock.json` (the full, real lockfile for `strip-json-comments-cli@3.0.0`, generated and reviewed at implementation time, committed to this repository) is the installation artifact — not the live npm registry consulted at install time for anything beyond fetching exactly what the lockfile pins.
- Install runs `npm ci --ignore-scripts --omit=dev` inside a URI-managed, immutable staging directory. `--ignore-scripts` is unconditional and non-negotiable — it applies regardless of whether any specific transitive dependency's lifecycle script is believed safe on a given npm version, precisely because that belief is not something this contract will re-verify on every future lockfile update.
- The reviewed lockfile must pin the complete transitive dependency tree and its integrity data (npm's own `package-lock.json` `resolved`+`integrity` fields for every entry) — this is npm's own existing, already-correct mechanism; URI does not invent a second lock format.
- The resulting staged install (a content-addressed, immutable artifact keyed by the lockfile's own hash) may be shared read-only across users with no user state or credentials in it, per §8's existing shared-artifact-cache rule; per-user lifecycle state (installed/enabled/disabled/removed, grants, evidence) stays exactly as user-scoped as every other store in this plan.

### D. Execution boundary (unconditional, not a per-package judgment)

No package lifecycle script (`preinstall`/`install`/`postinstall`/`prepare`/`postpack`, etc., for the target or any transitive dependency) may execute at any point — enforced structurally by `--ignore-scripts`, not by auditing each dependency's scripts field per install. No `npx` (it triggers its own on-demand resolution/install path outside this contract). No caller-controlled executable name, argv, or file path — the fixed invocation is `["node", "cli.js"]` (or the equivalent resolved staged path) with zero positional arguments; `cli.js`'s own optional file-path argument is never used or reachable, since text always arrives over stdin only, matching how the existing CLI adapter already injects input.

### E. The bounded action

One action only: `strip_json_comments(text, remove_whitespace=false) -> {text}`. Fixed CLI invocation as above. Input is JSON-encoded and piped to stdin exactly as the existing adapter already does for every CLI action; `remove_whitespace` maps to the tool's own `--no-whitespace` flag (default `false`, i.e., whitespace preserved, matching the tool's own default). `output: "text"` (§B) carries the raw stdout back as `{"text": ...}` — no double-JSON-parsing of output that may or may not itself be valid JSON.

### F. Update and removal

Update (v2.0.2 → v3.0.0, or any future revision) is a fresh qualification of the new commit's own reviewed lockfile, staged into its own immutable, content-addressed directory, and atomically activated only after that staged install validates — never an in-place mutation of the currently active staged install. Removal immediately retires the user's lifecycle/enablement state and its registry/discovery/Graphify presence, exactly as §4B already requires for every other Skill; the immutable shared staged artifact itself is only garbage-collected once no user's lifecycle record references it, since it carries no per-user state to begin with.

### G. Entry criteria satisfied

§8's five entry-criteria items are satisfied by A–F above: (1) real repository, dereferenced immutable commits, MIT license, inspected layout; (2) the bounded action is representable by the existing generic adapter contract plus the one additive `output` field in §B, with browser automation/self-updaters/MCP/cookies/runtime-generated commands all absent from this candidate; (3) exact artifact (the reviewed lockfile + `npm ci --ignore-scripts --omit=dev`), dependency lock, staging location, update/removal semantics all specified in C/F, with no install hook ever running (D); (4) qualification/integrity/atomic-install/rollback/per-user-state/live-retirement/Graphify-refresh testing follows the same pattern already proven for `yt-dlp` in Batch 2; (5) acceptance evidence is the same discovery/qualification/install/enable/disable/update/remove/cross-user/Graphify/compatibility matrix Batch 2 already used, extended to this candidate.

## 12. Batch 2 closure record (2026-09-19 — see §7)

The vendor-selection question that originally blocked this gate is resolved by §7's corrected acceptance case (`yt-dlp` pinned directly, not the Agent-Reach package). What remains is a short, bounded checklist, not an open architectural question:

1. Implement and verify all §4 residual corrections (A: store-root consistency, B: immediate live removal propagation, C: delete `LifecycleController.remove()`) — small, mechanical, already scoped in this document.
2. Pin one specific `yt-dlp` release (exact version recorded in the descriptor/commit), and write its descriptor + fixed argv template (e.g. `["yt-dlp", "--dump-json", "--no-playlist", <url-or-id-placeholder>]`) and JSON result shape from `--dump-json`'s real, already-documented output — no new discovery/negotiation needed.
3. Confirm the target for the first read-only action is one stable, public, review-safe source (no login, no cookies, no credential) — satisfiable without building any new infrastructure, since public metadata reads need none.
4. The descriptor is developer-authored and code-reviewed, per §7's new trust-boundary decision — not proposed by a model or accepted from a runtime request.

Each item above was implemented only within the bounded entry authorization and independently verified. The slice did not add a new URI adapter type or vendor-specific execution branch.

**Accepted bounded scope:** §4's three residual corrections, the developer-authored pinned `yt-dlp` descriptor, runtime lifecycle seam, the unchanged generic CLI adapter, one read-only action, and component/canonical-loop/live-refresh evidence. It excludes Firecrawl, later M33.1 batches, M33.2/M33.3/M33.4, the `agent-reach` package/installer/SKILL.md/router in any form, arbitrary SKILL.md prose execution, and vendor-specific core changes.

CLOSED / ACCEPTED — Batch 2 bounded pinned-`yt-dlp` CLI-Skill acceptance case. Batch 3 (GitHub Skill / Package Lifecycle) remains NOT STARTED.

## 13. Batch 4 — M33.1 closure record (implemented 2026-09-19/20; CLOSED / ACCEPTED)

### A. Extensibility matrix

§9's table is updated in place. Four structurally distinct mechanisms are proven: a static pinned CLI binary (`yt-dlp`), an existing OAuth Connected Service (Gmail), a built-in in-process capability (`remember_fact`), and a manifest/lockfile-installed npm CLI package (`strip-json-comments-cli`). No fifth mechanism is added — see §9's updated closure-decision cell for why one would be redundant, not merely absent.

### B. Natural-language/UI lifecycle seam

New module: `uri_core/external/lifecycle_intent.py`. One entrypoint, `execute_lifecycle_intent(context, user_id, *, operation, target_id, principal=None, **params)`, covering exactly the seven named operations (`install`/`enable`/`disable`/`update`/`remove`/`connect`/`disconnect`). It resolves `target_id` only against a small, developer-authored, code-reviewed catalog (`yt_dlp`, `strip_json_comments` for Skills; whatever `ConnectedServiceStore` already registers for services) and delegates entirely to the exact generic functions Batches 1–3 already proved (`runtime_lifecycle.py`, the per-package install/update/remove modules, `ConnectedServiceStore.connect`/`disconnect`) — it contains no new execution mechanism. `enable` transparently satisfies `LifecycleController.enable()`'s own configuration precondition first (matching the exact sequence Batches 1–3's own tests already use), rather than requiring the caller to name a separate `configure` intent. Every return value is passed through `_sanitize_lifecycle`/`_sanitize_connection`, which allow-list a fixed set of already-public fields — an internal detail (a staged artifact path, a raw exception) can never reach the caller through this seam even if a future catalog entry's return shape grows one. An unknown `target_id`, an unsupported `operation`, a `connect` with no supplied `credentials`, or an install/update handler raising all fail closed to a named status (`unknown_target`/`unsupported_operation`/`credentials_required`/`unavailable`) — never a raised exception, never a fabricated `success`.

**Originally deliberately not done in this closure (2026-09-19), now superseded by §13.G (2026-09-20):** the paragraph below is preserved verbatim as correction history rather than deleted. It described wiring this module into `canonical_execution.py`'s live `/ask` dispatch as a separate, later, explicitly-authorized step. The User then explicitly authorized exactly that step in a follow-up instruction ("CONTINUE M33.1 BATCH 4 — FINAL LIVE WIRING"), with a required architecture that resolved the concern below differently than first assumed: rather than threading the full `_UserContext` through `canonical_execution.py`, the live wiring bypasses that module entirely (§13.G) — `canonical_execution.py`, `multi_action_dispatch.py`, `orchestrator.py`, `approval_gate.py`, and `registry_bridge.py` remain byte-identical to before this batch.

> Wiring this module into `canonical_execution.py`'s live `/ask` dispatch. `_execute_canonical`/`run_canonical_for_ask` currently receive `orchestrator`, not the full `_UserContext` this seam needs (`external_capability_store`, `connected_service_store`, `external_lifecycle_lock`). Threading `context` through that call chain touches the hot path of every `/ask` request — a change of a different risk class than adding a new, self-contained module, and one this closure batch's own instruction ("do not add another substantial integration," "do not build the full M33.3 UI yet") argues for treating as a separate, explicitly-authorized next step rather than rushing into this batch. The seam is fully built, tested, and ready to be called from that wiring once authorized.

**Approval/permission note (disclosed, not a new gap introduced here):** lifecycle mutations (`enable`/`disable`/`remove`/etc.) are not currently gated by `ApprovalGate`/`CapabilityResolver` anywhere in this codebase — Batches 1–3's own direct API calls (`runtime_lifecycle.enable_and_refresh` etc.) have never required approval either, since they are authenticated-user self-service state changes (analogous to a settings toggle), not dispatch of a capability action against `Action.approval_requirement`. This seam inherits that existing precedent unchanged; it does not weaken it, and does not invent a new approval bypass. Per-user isolation (via `context`/`user_id`) and the fixed target catalog are the actual boundaries this seam relies on, exactly as every other lifecycle entry point already does.

### C. Compatibility

Independently re-run together: `test_m33_1_batch4_lifecycle_intent.py` (7), `test_m33_1_batch4_live_ask_lifecycle.py` (9, new — §13.G), `test_m33_1_batch3_github_package.py` (9), `test_m33_1_batch2_yt_dlp.py`, `test_m33_1_batch1_foundations.py`, `test_m33_batch_b_registry_bridge_and_dispatch.py`, `test_m33_batch_d_transports.py`, `test_canonical_execution.py`, `test_multi_action_capabilities.py`, `test_multi_user_isolation.py`, `test_m34_c3_3_heterogeneous_routing.py`, `test_m32_1_ask_resumption_endpoint.py`, and `test_server_ask_narrative.py` — 185 passed, 13 subtests passed, zero failures. (An earlier compatibility run before §13.G, listing a slightly different file set, recorded 234 passed / 13 subtests — both are preserved as history; §13.G's run specifically targets the live `/ask` wiring's own dependencies, since that is the new code this pass verifies.)

### D. Cleanup

`LifecycleController.remove()` (§4C) was already deleted in Batch 2 - reconfirmed by direct search, not re-assumed. No other dead scaffolding, TODO/FIXME markers, or debug prints were found in `lifecycle_intent.py`, `lifecycle_intent_interpreter.py`, the `server.py` wiring, or any Batch 1–3 file.

### E. Full regression

Two runs are preserved as history. Before §13.G's live wiring: `pytest -q` — 2,171 passed, 16 failed, 7 skipped, 40 subtests passed. After §13.G's live wiring (this run): 2,180 passed, 16 failed, 7 skipped, 40 subtests passed, in 1295.48s. The +9 passed matches exactly the 9 new tests in `test_m33_1_batch4_live_ask_lifecycle.py`. The 16 failures are name-for-name identical between both runs and identical to the Batch 3 baseline (14 pre-existing repo-wide failures + 2 environment-only Gmail/Drive credential-state failures). Two of the 16 (`test_m22_3_route_authorization.py`'s two route-count/classification tests) were re-verified independently against the clean pre-§13.G baseline (`git stash` isolation, all 16 named failures reproduced identically on the stashed-clean tree) specifically because a route-enumeration test is the kind of test a new `server.py` function could plausibly perturb — confirmed unrelated to this batch's diff. Zero regressions attributable to this batch.

### F. Recommendation

`COMPLETE` for the full closure scope, including the live `/ask` wiring (§13.G) the User explicitly authorized and required in a follow-up instruction after §13.A–F was first written. Recommend the same independent final-audit pattern used for Batches 2 and 3 before commit: re-verify this section's claims against the live diff (`uri_core/app/server.py`, `uri_core/core/lifecycle_intent_interpreter.py`, `uri_core/external/lifecycle_intent.py`, `test_m33_1_batch4_lifecycle_intent.py`, `test_m33_1_batch4_live_ask_lifecycle.py`, and this plan file), and independently re-run the full regression.

### G. Live `/ask` wiring (2026-09-20)

**Required architecture, as specified by the User:** `/ask` → a bounded, deterministic (model-free) interpretation step → a narrow per-user executor closure, injected directly into `server.py`'s `ask()` handler (never `_UserContext` itself, never exposed to `canonical_execution.py`) → the existing, unchanged `execute_lifecycle_intent(...)` → the existing URI lifecycle authority (catalog membership, `LifecycleController` state-machine legality, per-user store isolation) that Batches 1–3 already proved.

**Files changed:** `uri_core/app/server.py` (new `_lifecycle_intent_ask_envelope()` helper; a new, isolated, try/except-wrapped block inserted into `ask()` immediately after the existing approval-resumption block, following that block's own exact idiom — a `None`/failed interpretation, or the seam being off, falls straight through to the unchanged workflow-continuation/native-tool-loop/canonical/legacy chain below it); `uri_core/core/lifecycle_intent_interpreter.py` (new — the deterministic interpretation step, see below); `test_m33_1_batch4_live_ask_lifecycle.py` (new, 9 tests).

**Why this bypasses `canonical_execution.py`/`multi_action_dispatch.py` rather than registering a new `Capability` in the existing registry:** a `Capability`-in-registry design was evaluated first and rejected during this batch, not merely not attempted. `MultiActionDispatch._action_permitted()` denies, by fail-closed design, any capability id with no entry in its own `_ACTION_GRANT_CAPABILITY`/`_CAPABILITY_GRANT_ALIAS` tables unless `external_permission_resolver()` returns `True` — and that resolver's one and only question (`permission_binding.py`) is "is this id an already-enabled `ExternalCapabilityStore` record for this user," which is circular for a lifecycle-*management* capability whose entire purpose is to act before something is enabled. Satisfying that would have required adding a new alias entry to `multi_action_dispatch.py` itself — precisely the file the User's own instruction named as off-limits for this seam. Bypassing the registry entirely and calling `execute_lifecycle_intent()` directly, exactly as the required architecture specifies, avoids this without touching any of the five named modules.

**Deterministic interpretation (`lifecycle_intent_interpreter.py`):** recognizes only a complete, standalone command: one of `install|enable|disable|update|remove skill <identifier>` or `connect|disconnect service <identifier>`, with optional terminal punctuation. It does not interpret questions, negation, quotations, explanatory text, arbitrary verbs, multi-word/trailing targets, or text that merely contains a command-shaped phrase. The operation/target are still only proposals; `execute_lifecycle_intent()` alone resolves the fixed catalog and state-machine legality. This is the explicit lifecycle-specific policy decision for free-form `/ask`: authenticated users may manage only their own pre-reviewed lifecycle state with an exact command, and no separate ApprovalGate confirmation is required because these are self-service settings mutations rather than capability execution. Deliberately **off by default** (`URI_ENABLE_LIFECYCLE_INTENT_SEAM=1` to opt in), matching `native_tool_loop.py`'s own "materially newer, has not earned the default-on bar" convention — production `/ask` behavior is unchanged unless explicitly enabled.

**Authority/credential/isolation evidence:** the executor closure captures `context`/`user_id` from `ask()`'s own already-authenticated resolution (`Depends(_resolve_authenticated_user_id)`) — the interpreter never supplies or selects a `user_id`, and the seam is skipped entirely when `user_id is None` (the unauthenticated/legacy-ambient path). The interpreter extracts only `operation`/`target_id` from `payload.text` — never a `credentials` field — so a `connect` intent always reaches `_execute_service_operation` with no credentials, which always returns `credentials_required` (the existing secure-flow-required response); no secret can reach this path via model-visible `/ask` text. Sanitized lifecycle outputs never expose raw exceptions or provider/caller-controlled connection fields, and the live seam records only structured operation/target/status/user evidence (not prompt text or credentials). Cross-user isolation, corrupt-state fail-closed behavior, unknown-target and unsupported-operation behavior, and the known-skill catalog boundary are all enforced by the runtime — this wiring adds no text-derived authority.

**Focused live `/ask` tests (`test_m33_1_batch4_live_ask_lifecycle.py`, 9, all passing):** seam off by default; ordinary conversation unaffected; install→enable→disable a known skill (`yt_dlp`, no network) with real dispatch-registry swap verified after enable and disable; install→remove a known skill (`strip_json_comments`, real `npm ci`); unknown target fails closed; unsupported operation fails closed; connect-requiring-credentials returns the secure-flow response with no secret in the body; cross-user isolation (User B's registry/state untouched by User A's lifecycle actions, and User B's own disable reports `not_installed`); an unauthenticated request never reaches the seam.

### H. Independent closure review and acceptance (2026-09-20)

The recovered implementation was independently reviewed against this frozen plan after the power interruption. Verdict: **ACCEPT**. No bounded production-code fix was required. The reviewed matrix remains four materially distinct mechanisms — static pinned CLI (`yt-dlp`), OAuth Connected Service (Gmail), local in-process capability (`remember_fact`), and reviewed manifest/lockfile-installed package (`strip-json-comments-cli`). Arbitrary `SKILL.md` prose is deliberately not counted as a fifth mechanism: URI does not execute prose as authority, and re-exercising the same package path would not add coverage.

The accepted recovery contains the Batch 4 lifecycle catalog/sanitization seam, deterministic opt-in interpreter, narrow authenticated `/ask` closure, malformed-state fail-closed guards, and its two test modules exactly as reviewed. The seam remains opt-in through `URI_ENABLE_LIFECYCLE_INTENT_SEAM=1`; a graphical lifecycle-management UI remains M33.3 work and is out of scope.

Independent isolated lifecycle/live evidence: **35/35 passed** across the Batch 2–4 acceptance suites, including real `yt-dlp`, real reviewed npm-package lifecycle, and live `/ask` operations. Full recovered-tree regression: **2,175 passed / 23 failed / 7 skipped / 40 subtests**. Detached clean `5973f6d` baseline: **2,165 passed / 15 failed / 7 skipped / 40 subtests**. Failure classification: 14 recovered failures overlapped the baseline; 7 transient external DNS/npm/yt-dlp failures later passed in the isolated rerun; 2 Drive tests were environment-sensitive and outside every Batch 4 path. No closure regression was found.

Residual: test-environment nondeterminism remains for external DNS/npm/yt-dlp and local Drive credential state. It is documented evidence debt, not a reason to alter URI's deterministic authority core or reopen accepted Batches 1–3. M33.2 planning artifacts remain unrelated and unabsorbed.
