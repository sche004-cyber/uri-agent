# M33.1 — Real Integrations & Extension Validation

**Status:** Batch 2 CLOSED / ACCEPTED — authoritative frozen plan for the remainder of M33.1. The bounded pinned-`yt-dlp` CLI-Skill acceptance case and its §4 residual corrections were independently audited and accepted on 2026-09-19. Batch 3 has not started.

**Authority:** This supersedes the M33 bridge blueprint §10 sketch for the remainder of M33.1. Batch 1 is CLOSED / ACCEPTED at `d78366d` / `0558a99`. Batch 2 entry slice is authorized.

## 1. Evidence and authority

M33.1 proves that URI can acquire and manage external abilities through the landed generic external-capability bridge. It is not M33.2.

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

## 3. Frozen batches and M33.2 boundary

1. **Batch 1 — Foundations:** CLOSED / ACCEPTED: descriptor/store, encrypted credentials, lifecycle primitives, status/Graphify seams, and persisted removal at `d78366d`.
2. **Batch 2 — pinned `yt-dlp` CLI Skill** (corrected from "Agent Reach": real Skill-package/CLI acceptance case, 2026-09-19 — see §7). CLOSED / ACCEPTED at `dd4863a`.
3. **Batch 3 — Firecrawl:** optional HTTP/API Connected Service acceptance case. NOT STARTED.
4. **Batch 4 — Broader Extensibility Proof:** prove four to five structurally different mechanisms. NOT STARTED.
5. **Batch 5 — Natural-Language / UI Lifecycle Seam:** lifecycle requests such as Install/Remove a registered Skill and Connect/Disconnect GitHub. NOT STARTED.

M33.1 acquires and manages abilities. M33.2 is reserved for Knowledge Fabric—sources, watches, continuous learning. M33.1 outputs may carry normalized evidence metadata but no integration gains direct durable-knowledge write authority. A future M33.2 Knowledge Gateway must validate candidate, provenance, user scope, consent, and retention before a durable write.

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

## 8. Batch 3 — Firecrawl acceptance

Firecrawl remains optional; URI works without it. As HTTP/API Connected Service, a pinned provider API version must prove per-user encrypted key, explicit connect/configure/health, sanitized status, service descriptor capability registration, generic HTTP-adapter execution through URI validation/permission/approval/audit/evidence, and disconnect/revoke deleting local key plus immediately retiring live capabilities and refreshing discovery/Graphify. Bad/expired/revoked credentials, transport/redirect/response failures, and cross-user attempts fail closed without disclosure. Include component, integration, canonical-loop, and live UI/chat evidence; Gmail/Drive/native execution stay compatible.

## 9. Batch 4 extensibility matrix

| Mechanism | Onboarding/lifecycle | Credentials/dependencies | Registration/execution | Removal/discovery |
| --- | --- | --- | --- | --- |
| CLI/local Skill — pinned `yt-dlp` | Inspect, qualify, install/configure/enable/update/disable/remove | Pinned version/dependencies; no browser/cookie import, no third-party installer/router | Descriptor + generic CLI adapter | Store removal; immediate registry/discovery/Graphify retirement |
| HTTP/API Service — Firecrawl | Configure/connect/health/disconnect/revoke | Per-user encrypted key | Service descriptor + generic HTTP adapter | Revoke/retire/refresh |
| OAuth Service — Gmail/equivalent | Consent/connect/refresh/health/disconnect | User OAuth token/scopes | Existing canonical path/equivalent bridge | Disconnect makes availability false |
| Local in-process — `remember_fact` | Built-in availability and normal enable/grant | No external credential | Existing common executor | Grant/enable removal affects surfaces |
| Manifest/SKILL.md package | Inspect, qualify/install/update/enable/disable/remove | Declared dependencies; prose is never executable authority | Validated action descriptor only | Remove/refresh derived views |

Batch 4 closes only when all five are evidenced as structurally distinct.

## 10. Batch 5 lifecycle seam

Natural language/UI may request lifecycle intent, but URI resolves registered target, validates eligibility, requires needed confirmation/approval, runs lifecycle, and returns actual sanitized state. Neither model nor UI can invent id, credential, registration, grant, or success.

## 11. M33.1 exit criteria

Close only with evidence that the pinned `yt-dlp` CLI Skill and optional Firecrawl work end-to-end; live install/enable/disable/update/remove and connect/disconnect/revoke work; retirement is immediate; credentials remain encrypted/isolated/sanitized; discovery/Graphify refresh and remain non-authoritative; generic contracts carry every mechanism without vendor-specific core execution; all five matrix mechanisms are proven; the natural-language/UI seam works; Gmail/Drive/canonical/native execution stays compatible; and full regression has zero new failures plus component, integration, canonical-loop, and live user-visible evidence.

## 12. Batch 2 closure record (2026-09-19 — see §7)

The vendor-selection question that originally blocked this gate is resolved by §7's corrected acceptance case (`yt-dlp` pinned directly, not the Agent-Reach package). What remains is a short, bounded checklist, not an open architectural question:

1. Implement and verify all §4 residual corrections (A: store-root consistency, B: immediate live removal propagation, C: delete `LifecycleController.remove()`) — small, mechanical, already scoped in this document.
2. Pin one specific `yt-dlp` release (exact version recorded in the descriptor/commit), and write its descriptor + fixed argv template (e.g. `["yt-dlp", "--dump-json", "--no-playlist", <url-or-id-placeholder>]`) and JSON result shape from `--dump-json`'s real, already-documented output — no new discovery/negotiation needed.
3. Confirm the target for the first read-only action is one stable, public, review-safe source (no login, no cookies, no credential) — satisfiable without building any new infrastructure, since public metadata reads need none.
4. The descriptor is developer-authored and code-reviewed, per §7's new trust-boundary decision — not proposed by a model or accepted from a runtime request.

Each item above was implemented only within the bounded entry authorization and independently verified. The slice did not add a new URI adapter type or vendor-specific execution branch.

**Accepted bounded scope:** §4's three residual corrections, the developer-authored pinned `yt-dlp` descriptor, runtime lifecycle seam, the unchanged generic CLI adapter, one read-only action, and component/canonical-loop/live-refresh evidence. It excludes Firecrawl, Batches 4/5, M33.2, the `agent-reach` package/installer/SKILL.md/router in any form, arbitrary SKILL.md prose execution, and vendor-specific core changes.

CLOSED / ACCEPTED — Batch 2 bounded pinned-`yt-dlp` CLI-Skill acceptance case. Batch 3 (Firecrawl) remains NOT STARTED.
