# URI M22 — ARCHITECTURE SPECIFICATION (FINAL SYNTHESIS)

**Status:** Architecture plan; M22.1 and M22.2 are implemented. M22.3 is next.
**As-built baseline:** M22.2 is complete at commit `34839ce`, with 1,141/1,141
tests passing at delivery. This documentation update does not repeat the M22,
M22.1, or M22.2 architecture/security audits.
**Role of this document:** the governing specification for the remaining M22
milestones, executed **one milestone at a time**.

**Current worktree note:** uncommitted `uri_ui` Windows/platform work is active
and unverified. It is not an M22 milestone and does not change this plan.

This synthesis supersedes the earlier draft of this file. It is grounded in a fresh, targeted re-inspection of the repository specifically to verify the claims in Parts 1–4 of the brief (which import edges are real vs. cosmetic, which test files carry real coverage, what the Flutter mobile scaffolding actually contains) rather than repeating the general survey. Every non-obvious factual claim below was checked against the actual source, not assumed.

---

## 1. Current M21 state

M21 delivered, correctly, and this document builds on it without re-litigating it:

- A clean provider boundary (`ModelProvider` ABC, `ModelProviderConfig`, `ModelProviderStatus`, `ModelResponse`) and a working seam (`config/model_roles.py` → `build_provider(role)`) used by all four real call sites (`provider_semantic_interpreter.py`, `model_reasoning_adapter.py`, `response_drafting.py`, `document_composer.py`).
- Deterministic context/prompt bounding (`context_budget.py`: `estimate_tokens`, `fit_within_budget`, `bound_json_value`), applied to execution history, session facts, experience, and a new bounded conversation window.
- Per-user isolation for nine stores via `_build_user_context` (profile, memory, growth, sessions, approvals, experience, skill memory, conversation history, and — the M21 fix — files), all under `portable_paths.user_scoped_path`.
- The AST import-boundary testing technique (`test_capability_authority_boundary.py`, 22 tests) proving structural separation between reasoning, execution, and approval.
- The `ApprovalGate` → `ToolDispatcher` execution boundary, with `ApprovalGate` as the orchestrator's sole execution path (also structurally tested).

**None of this is touched in kind by M22.** M22 adds scoping (per-user capability authority, per-user provider config), an edge layer (auth on every route), and client surfaces. It does not alter the propose → validate → approve → execute chain.

---

## 2. Critical security blockers

Ordered by what they gate, verified directly against `uri_core/app/server.py`:

| # | Finding | Verified evidence | Gates |
|---|---|---|---|
| S1 | Five mutating endpoints have no `Depends(_resolve_authenticated_user_id)` at all | `/skills/{id}/enable`, `/skills/{id}/disable`, `DELETE /skills/{id}`, `POST /connections/{id}/authorize`, `DELETE /connections/{id}` | Any non-loopback exposure (M22.9, and any future messaging/cloud work) |
| S2 | `ToolDispatcher.execute_tool` does `importlib.import_module()` on a path read from `capabilities_registry.json` | `dispatcher.py:84-96` | Any promotion mechanism, any Developer Mode, any skill-controlled UI |
| S3 | Capability authority has no per-user axis | `CapabilityRegistry()` constructed once, shared by every `UriOrchestrator` instance `_build_user_context` builds | Multi-user deployments; "models cannot grant themselves capabilities" is currently true only because nothing per-user exists to grant |
| S4 | `AuthSessionStore` is process-memory only | `auth_session.py` module docstring: "Tokens live only in this process's memory... reset on restart" | Mobile/PWA (a restart logs out every device) |
| S5 | No rate limiting anywhere, including `/auth/login` | absent from `server.py` | Any non-loopback exposure |

**S1 and S2 are the two that must close before any remote/mobile milestone (M22.9) proceeds.** S3 is the deeper structural gap and is the largest single milestone in this plan (M22.4). S4/S5 are required specifically because mobile clients cannot tolerate silent logout on every server restart and because remote exposure makes brute-force realistic.

`DELETE /connections/{id}` performs a real, install-wide state change (revokes a shared Gmail/Drive OAuth token — confirmed by reading its handler; the connection is server-host-scoped, not per-user). It is therefore an **ADMIN**-gated endpoint, not merely USER-gated, once roles exist.

---

## 3. Capability authority

### 3.1 The gap, precisely

`CapabilityRegistry()` is instantiated once at module scope in `server.py` and shared by every user's `UriOrchestrator`. Every `_UserContext` built by `_build_user_context` gets its own approval store, session manager, experience store, skill memory, conversation history, and (M21) file store — but reads the exact same capability set as every other user. There is no data structure today that could answer "may *this* user use *this* capability."

### 3.2 CapabilityResolver

A new INSTALL-scope-reading, USER-scope-aware component:

```
CapabilityResolver.resolve(principal: PrincipalContext) -> List[CapabilityDescriptor]
CapabilityResolver.is_allowed(capability_id: str, principal: PrincipalContext) -> bool
```

Computed as an intersection, never a union:

```
resolved = registry_capabilities ∩ user_grants[principal.user_id] ∩ mode_allowlist[principal.mode] ∩ node_scope[principal.node_id]
```

Backed by one new INSTALL-scope store, `capability_grants.json` (`user_id → [capability_id]`), defaulting every existing/new user to the **full current registry** at migration time — this is what makes M22.4 a zero-behaviour-change milestone for single-user installs while making the per-user axis real and testable.

### 3.3 Where it is consulted — twice, deliberately

1. **Advisory**, when the catalogue is shown to the Brain (`orchestrator._build_query_context`) — so the model is never even offered a capability the user cannot use.
2. **Authoritative**, inside `ApprovalGate.execute_tool`, immediately before the existing `capability_registry.describe_status` lookup — so a stale catalogue, a race, or a bug in step 1 cannot become an execution path. This is the same "the gate decides, nothing upstream is trusted" discipline `ApprovalGate`'s own module docstring already states about model proposals; M22.4 extends it to cover *user* authority the same way it already covers *model* authority.

**This is the concrete mechanism behind "models cannot grant themselves capabilities" and "ADMIN must still obey capability authority and approval boundaries."** A model proposal was already re-validated against the registry (M21 and earlier); now the *user* is also re-validated against their own grants, at the same enforcement point, including for ADMIN — an ADMIN's own turns flow through `ApprovalGate` exactly like any user's, and ADMIN privilege is exercised only through the separate, explicitly-classified `/admin/*` endpoints (§14), never by bypassing the gate.

### 3.4 orchestrator.py impact and the extraction this milestone requires

`orchestrator.py` currently computes "which capabilities exist for this turn" itself, in `_executable_capability_ids` (a ~50-line method) and inline in `_build_query_context`'s capability-catalogue assembly. Wiring in `CapabilityResolver` without growing the file means **extracting this logic into the resolver module as part of M22.4's own scope** — moving lines out of `orchestrator.py` before adding back a one-line call to `self.capability_resolver.resolve(principal)`. This is not a separate milestone: it is a small (~50-80 line), bounded move of code that already exists as its own method into the new module whose entire job is to own exactly that computation. **Acceptance criterion: `wc -l uri_core/core/orchestrator.py` after M22.4 is ≤ its value before M22.4.**

---

## 4. User / role model

### 4.1 Two axes, enforced apart

```
Role            USER | ADMIN                      — privilege, admin-assignable only
ExperienceTier  BASIC | ADVANCED                   — preference, self-settable, zero authority
```

`INTERMEDIATE` is **not added**. Nothing in the repository or the brief identifies a concrete behavioural difference a third tier would produce beyond BASIC/ADVANCED; adding it now would be speculative configuration with no consumer.

### 4.2 UserAccount extension

```
UserAccount
  user_id, username, password_salt, password_hash, created_at   # unchanged
  role              USER | ADMIN            # new
  experience_tier   BASIC | ADVANCED        # new, user-editable via own account only
  status            active | suspended      # new
  schema_version                            # bumped
```

### 4.3 Bootstrap

First account created on a fresh install (by `created_at`) becomes ADMIN; every subsequent account is USER. No env var, no default password, no magic username. Migration of pre-existing accounts: earliest `created_at` in the existing `user_accounts.json` → ADMIN, rest → USER (§20).

### 4.4 The enforced separation

Every authorization decision in the codebase reads `role`. **None reads `experience_tier`.** This is not a convention — it is a structural test (§19.4): an AST scan asserting no function reachable from `ApprovalGate`, `CapabilityResolver`, or any `/admin/*` handler references the string `experience_tier`. `experience_tier` is read in exactly one place: the client-facing UI-shaping code that decides how much configuration surface to show (§8).

### 4.5 ADMIN's actual boundary (made concrete, not asserted)

- ADMIN endpoints are **install-scope only**: provider catalogue, capability registry promotion, mode configuration, aggregate (non-content) usage, role assignment, connection management.
- **No endpoint, anywhere, lets ADMIN read another user's API key, memory, files, or conversation.** Keys are write-only (§6.4); there is no "read as user" endpoint at all.
- ADMIN's own conversational turns go through the identical `ApprovalGate`/`CapabilityResolver` path as any USER's.
- Every `/admin/*` action writes an audit record with the acting `user_id`.

---

## 5. Experience tiers

BASIC and ADVANCED shape **client-side presentation and guidance text only**:

- **BASIC**: never shown "API key," "context window," "OpenRouter," "token," or a raw model id. Sees curated provider *options* with plain-language framing (what it's good for / free-or-paid / main limitation / what happens at the limit) and a simple usage bar. On hitting a ceiling: a one-tap choice among configured alternatives.
- **ADVANCED**: full per-role provider/model assignment, explicit fallback ordering, base URLs/timeouts/context sizes, own API keys, local endpoints, raw usage detail.

Tier is stored per-user, editable by the user at any time, read by exactly the client-rendering / guidance-copy layer (§16 UI extension boundary reuses the same "declared surface" discipline for this, at a much smaller scale: a `basic` vs `advanced` view of the same underlying `/providers` data, never two different authorization outcomes).

---

## 6. Provider / model abstraction

### 6.1 Static vs. live — kept as two stores with two lifetimes

| Store | Scope | Lifetime | Refresh |
|---|---|---|---|
| `provider_catalogue.json` | INSTALL | ~30 days | ADMIN manual, age-triggered, or change-detected (a real call contradicts a cached fact) |
| `providers.json` (per user) | USER | until edited | user action |
| `provider_keys.enc` (per user) | USER | until edited | user action; **write-only, never read back** |
| `usage/YYYY-MM.jsonl` (per user) | USER | append-only | every call |

### 6.2 Two adapter families, not five

`ADAPTERS` in `build_provider` stays a **closed dict** (M21's `UnknownModelProviderError` — never silently substitute — is preserved unchanged). M22 adds exactly:

1. **One OpenAI-compatible HTTP adapter**, parameterised by `base_url` — covers OpenRouter, Groq, LM Studio, llama.cpp, and OpenAI itself, all of which share the `/chat/completions` wire shape.
2. `OllamaProvider` — unchanged, kept as the local/offline default path.

Anthropic- and Google-specific adapters (different wire formats) are **not built in M22** — no concrete role in this milestone consumes them, and the seam (`ADAPTERS` dict + `ProviderDescriptor.adapter`) makes adding one later a three-file change, not an architecture change.

### 6.3 ModelDescriptor confidence labelling

Every numeric field carries `KNOWN | ESTIMATED | UNAVAILABLE`:

- `context_tokens`, pricing, rate limits: `KNOWN` when the catalogue entry is provider-documented, `ESTIMATED` when derived from URI's own estimator, `UNAVAILABLE` when neither.
- Provider-side remaining quota: `KNOWN` only when a real response actually exposes it (e.g. `x-ratelimit-remaining-*` headers some providers return); otherwise **always** `UNAVAILABLE` — URI does not compute a guess for a number it does not have.
- URI's **own** consumption (requests, measured tokens, latency) is always `KNOWN`, because URI made every call itself.

### 6.4 API keys — the one genuinely new sensitive data type

Per-user, encrypted at rest (`cryptography` is already an installed transitive dependency — no new dependency), write-only API (`POST /providers/keys` sets, there is no `GET`; validity shown via a cheap `describe()`-style probe and a stored last-4 suffix only), bound to `(user_id, provider_id)`, deleted with the user's directory. **No module that assembles a prompt may import the key store** — enforced by the same AST technique (§19.4).

### 6.5 Model roles — extend M21's four, do not add a role with no consumer

`semantic_interpretation` (renamed conceptually to *classification*), `reasoning`, `drafting`, `document_composition` — unchanged. Add `diagnostics` and `background` (both default to a light tier). **Do not add `implementation`** — nothing in M22 calls it; adding it now is unconsumed configuration surface.

---

## 7. Provider routing / fallback

### 7.1 ModelRouter — the one new decision-maker

```
ModelRouter.resolve(role, principal) -> ProviderPlan(provider_id, model, config, fallback_chain)
```

Deterministic inputs, in order: user's configured primary for `role` → health (per `(provider, model)`, sticky with a short cooldown, not a permanent mark) → a deterministic pre-flight budget check (§8.3) → user's declared fallback order → install default (only if the user permits it) → any healthy local provider → **degrade** (§9).

### 7.2 Failure-class-aware, never silent

`ProviderTimeoutError` / `ProviderUnavailableError` → try next in chain. `ModelNotFoundError` → do not retry the same model, mark unhealthy, report honestly. **Authentication failure → stop, do not fall back** — silently trying a different provider on an auth error hides a broken key and can spend a different provider's quota/money without the user knowing why. Every fallback that actually occurs is surfaced to the user: which model actually answered.

### 7.3 Where it plugs in

`build_provider(role)` becomes `build_provider(role, principal)`. Its four M21 call sites (`provider_semantic_interpreter.py`, `model_reasoning_adapter.py`, `response_drafting.py`, `document_composer.py`) are the only edits required — **`orchestrator.py` does not construct providers itself today and does not need to.** This is direct evidence the M21 seam was designed correctly for exactly this extension; M22.6 is low-risk to the orchestrator by construction, not by discipline.

---

## 8. Usage / limits

### 8.1 UsageRecord (append-only, per user, monthly JSONL)

`ts, user_id, session_id, role, provider_id, model_id, prompt_tokens{value,confidence}, output_tokens{value,confidence}, duration_seconds(KNOWN — M21 already measures this), outcome, fallback_from, estimated_cost{value,confidence}, context_utilisation`.

### 8.2 Dashboard — zero model calls, by construction

A pure fold over the current month's JSONL + the static catalogue. **Enforced by test**: the aggregation module never imports `ModelProvider`/`ModelRouter` (§19.4) — the same technique already used to keep, e.g., `response_drafting.py` out of the approval path.

### 8.3 Budgets are pre-flight, not post-hoc

`UsageMeter` is purely observational — it records after a call completes and **never itself blocks a call** (this is what keeps rule "provider quota must never be fabricated" and "usage tracking is deterministic" both true without adding a feedback loop into the router). The actual ceiling check is a **separate, deterministic pre-flight** using `estimate_tokens` (the same estimator M21 already uses for its oversized-prompt warning) against the user's configured monthly ceiling, run by `ModelRouter` *before* it selects a provider. Two thresholds: **warn** (surfaced, not blocking) and **stop** (blocks, `ModelRouter` proceeds to fallback/degrade exactly as if the provider itself were unavailable).

---

## 9. Degraded no-model operation

**Design decision, stated once and enforced everywhere:** *no reachable model* is a `ModelRouter` outcome like any other — it is the last, mandatory step in the fallback chain (§7.1), not a special case scattered through the orchestrator.

When it occurs: `ModelReasoningGateway`'s call is reported as unavailable, with the real reason (no provider configured / all providers unhealthy / all budgets exhausted) and the concrete remedy (configure a provider / wait for reset / switch to local). **Deterministic capabilities are unaffected** — `ApprovalGate`, `ToolDispatcher`, approve/reject, list tasks, read history, list files, list memory, view usage — none of these call a model and none of them are gated by `ModelRouter`'s outcome. This falls out of the existing architecture almost for free: the propose/approve/execute chain was already separate from reasoning; M22 only needs to make sure the degrade path is **reported honestly to the user** rather than surfacing as a generic error, and that the reasoning-unavailable state never blocks an already-approved or already-pending action from being decided.

**Test requirement:** with every configured provider forced unreachable, the deterministic-capability test suite (`test_orchestrator_attachments.py`-style, `test_multi_user_isolation.py`-style) still passes unchanged.

---

## 10. Remote security

This section gates every non-loopback milestone (M22.9 and beyond).

**Must exist before non-loopback binding:**
1. S1 closed — the five endpoints authenticated/ADMIN-gated (M22.3).
2. Every route explicitly classified `PUBLIC | USER | ADMIN` (M22.3) — enumerated by test, so a new route can never silently default to public.
3. TLS — via reverse proxy (recommended: keeps TLS termination out of URI's own code) or native uvicorn TLS for a self-hosted single box. **URI refuses to bind a non-loopback interface without TLS unless an explicit, logged, insecure override is passed.**
4. Rate limiting on `/auth/login`/`/auth/signup` (currently unlimited password guessing) and a per-token request cap.
5. CORS locked to an explicit allow-list (currently permissive middleware).
6. Request size caps on `/ask` (currently unbounded text) — `/files` already has `MAX_FILE_BYTES`.

**Durable identity for remote clients:** hashed, persisted sessions (§4, S4) with sliding expiry, per-device revocation, and revoke-all-on-role-change.

**Structural guarantee for any future remote interface:** no adapter module may import `UriOrchestrator`, `ToolDispatcher`, or `ApprovalGate` — an adapter's only permitted action is an HTTP call to the same API a phone uses, carrying an authenticated `PrincipalContext`. This is the literal mechanism behind "remote interfaces cannot bypass capability authority or ApprovalGate": there is no import path by which they could.

---

## 11. Portability

### 11.1 What to measure (only what would change a decision)

| Metric | Target | Rationale |
|---|---|---|
| Cold start | < 2s | Also catches an accidental startup network call |
| Idle RSS | < 250MB | Fits a small VM / Raspberry Pi alongside the OS |
| Startup network calls | **0** | Non-negotiable — proves offline + cloud-independence |
| Declared dependencies | ≤ 10 (currently 8) | Forces justification per addition |
| `/ask` p95 excluding model time | < 150ms | Isolates Core cost from model latency |
| Dashboard render | < 200ms, 0 model calls | Makes §8.2's requirement measurable |

Not measured: throughput/concurrency/GPU — URI is not a high-QPS service; optimising for it would be the "blind optimisation" the brief itself warns against.

### 11.2 Hard rules

No absolute paths (already the convention via `portable_paths`). **The packaged default is "no provider configured; here are your options" — not Ollama/Gemma.** Optional dependencies (OCR, PDF, DOCX, PPTX) degrade to "capability unavailable," never crash (`pdf_reader.py` already models this). No database, no broker, no cache server (§11.3 below).

### 11.3 No database in M22

JSON-per-user plus append-only JSONL for usage scales to the realistic multi-user counts this milestone targets, costs nothing operationally, and preserves the portability profile. The one real risk — concurrent writes to a *shared* file (`user_accounts.json`, `auth_sessions.json` if not yet split per-user) — is handled with a simple single-writer/file-lock discipline, not a database. Revisit only if a measured problem appears.

---

## 12. PWA / mobile boundary

### 12.1 Verified starting point

`uri_ui/` is a Flutter project that **already has `android/` and `web/` targets scaffolded** (confirmed: `uri_ui/android/app/`, `uri_ui/web/manifest.json` present). This is a materially better starting position than "build mobile from scratch" — M22.9's job is to *finish and brand* an existing scaffold, not create one.

### 12.2 One brain, thin clients

Mobile/web is a client of the same HTTP API desktop uses — same `/auth/*`, same `PrincipalContext`, same `CapabilityResolver`, same `ApprovalGate`, same provider routing, same per-user isolation. No separate reasoning path, no separate approval path. Enforced structurally by §10's adapter-import rule, which applies equally to the Flutter client's Dart HTTP layer (`http_uri_client.dart`) — it already only calls the HTTP API and holds no Core logic; M22 does not change that shape, only what the API now requires (a durable bearer token, role-aware responses).

### 12.3 "Mobile without desktop powered on"

Has no architecture-only solution — it requires an always-on host somewhere (cloud VM, home server, small always-on box). M22 makes that deployment *possible* (stateless-where-feasible, no machine-bound config, no absolute paths, TLS-ready) without *performing* it. Scenario coverage: desktop-online (works today), desktop-offline (achievable via §9's degrade path + a local provider), cloud-hosted (possible after M22, not deployed in M22), mobile-only (== cloud-hosted + a phone; not a separate architecture).

### 12.4 Multi-node — seam only

Add `node_id` to `PrincipalContext` and a `node_scope: any | local_only` field to `CapabilityDescriptor`, consulted by `CapabilityResolver` (§3.2)'s intersection. This lets a cloud node **honestly** report "`organise_local_folder` is unavailable on this node; `read_attached_file` is available" — which is the actual user-trust requirement — without building node-to-node RPC, job forwarding, or peer discovery. No multi-node distributed mesh in M22, per the standing rule.

---

## 13. Android review APK

### 13.1 What already exists (verified)

`uri_ui/pubspec.yaml`: `version: 1.0.0+1`, unbranded default dependencies (`cupertino_icons`, `shared_preferences`, `http`, `file_picker`, `open_filex` — no analytics, no crash-reporting SDK, nothing that phones home). `AndroidManifest.xml`: `android:label="uri_ui"`. `build.gradle.kts`: `applicationId = "com.example.uri_ui"`. Icons are the **default Flutter mascot placeholders** in every `mipmap-*` density and in `web/icons/`. Theme colour is Flutter's default blue (`#0175C2`). **No branding work has been done at all** — this is a real, concrete task, not a formality.

### 13.2 What M22.9 must produce

A debug/profile-signed **review** APK: correct app name ("URI"), a real `applicationId` (not `com.example.*`), replaced launcher icons across all `mipmap-*` densities using the approved logo, a repeatable build command (`flutter build apk --debug` or a profile build, documented), and **zero embedded secrets** — every provider credential the app needs is a *user-supplied* API key entered through the app's own settings screen and sent to URI's backend over the already-designed write-only key API (§6.4); the APK itself contains no key, no `.env`, no hardcoded base URL beyond a sensible local-network default the user can change (the existing `server_address_store.dart` already supports this pattern).

### 13.3 What it explicitly does not require

Play Store signing, a Play Store listing, release-track configuration, or app-store review. This is a side-loadable, physical-device review build — debug or profile signing is sufficient and is what keeps this a small, low-risk deliverable inside M22.9 rather than a separate release-engineering milestone.

---

## 14. Approved URI AI COMPANION branding

Applied consistently once, across every surface, from **assets** — never encoded as logic:

```
uri_ui/assets/branding/
  logo.svg / logo.png (multiple densities)
  app_icon (source, exported to every mipmap-* and web/icons/* size)
  wordmark  "URI — AI COMPANION"
  color_tokens.dart   (theme primary/secondary derived from the approved logo, replacing #0175C2)
```

Surfaces to update: Android launcher icon + label + `applicationId`, `web/manifest.json` (`name`, `short_name`, `theme_color`, `background_color`, icons), login/onboarding/loading screens' wordmark and colour, app bar / splash. **Branding assets live under `uri_ui/assets/`, never inside `uri_core/`** — the Core has no concept of presentation and must stay that way; this is the same "Core stays presentation-free" principle that already keeps `query_context.py` from knowing about UI, applied to imagery instead of text.

---

## 15. UI extension boundary

### 15.1 Specify now, build in M23 — the brief's own instruction, and correct

A skill declares a bounded **view specification**, never code:

```
UISurface
  surface_id, title, mode_scope
  components: [ { type: text|table|chart|list|kv|form|button, ...bounded props } ]  # closed enum
  data_source: capability_id           # must already be a registered, resolvable capability
  actions:     [capability_id]         # each still executes only through ApprovalGate
  permissions: [declared reads/writes]
```

Hard rules: closed component enum (an unrecognised type rejects the whole surface, never partially renders it); no HTML/JS/expression language of any kind; every action id is resolved through `CapabilityResolver` and executed only through `ApprovalGate` — a declared UI surface grants **zero** new authority, it only arranges authority that already exists; bounded sizes reusing `context_budget` discipline (row caps, point caps, component-count caps).

### 15.2 Why M22 cannot build the renderer yet

It depends on four things none of which exist before M22: `CapabilityResolver` (M22.4), per-user grants (M22.4), a real skill promotion path (§17), and client rendering work. Building the declaration format is cheap and valuable now (it disciplines every later UI decision); building the enforcement + renderer before its dependencies exist would mean designing against imagination, and shipping a component renderer with no `CapabilityResolver` underneath it would let a skill's "action" bypass the exact authority check M22.4 exists to add.

### 15.3 Validation against the two example skills (architecture check only, not built)

**Monthly Budget Planner** — fits the vocabulary cleanly (`table`/`chart`/`kv` components, one `data_source`, few actions). Its real difficulty is data access and prediction quality, not UI — a good vocabulary validator, a poor early-implementation candidate.

**File/Folder Organisation** — the sharper validator. Classification/duplicate-detection is read-only and safe under the existing boundary. "Authorised execution" of a bulk filesystem reorganisation is destructive and hard to reverse, and exposes a real gap worth naming now: `ApprovalStore`'s current single-use, session-bound, expiring approval needs a **plan content digest** so what the user approved is provably what executes, plus an execution journal for undo. This is a small, well-scoped extension to `ApprovalStore` — noted here as a concrete M23+ prerequisite, not built in M22.

---

## 16. Modes

### 16.1 A mode is a filter, never a Core variant

```
Mode
  id            office | diagnostic | admin
  capabilities  allow-list of registered capability ids
  ui_surfaces   which screens/panels are offered
  min_role      USER | ADMIN
```

Mode participates in `CapabilityResolver`'s intersection (§3.2) exactly like grants and node scope. **Invariant, enforced by test:** `resolved ⊆ granted ⊆ registered` — switching mode can only ever narrow what's offered, never grant anything a user's own grants or the install registry don't already contain.

### 16.2 Office / Diagnostic / Admin — built in M22 (as scoped filters)

- **OFFICE** — the existing drafting/document/evidence capability set, USER-reachable, no new capabilities — this is largely a UI arrangement over what already exists.
- **DIAGNOSTIC** — read-only: connection status, capability catalogue, usage dashboard, audit trail views. Zero mutating capabilities.
- **ADMIN** — the `/admin/*` surface (§14 endpoints), `min_role: ADMIN`.

### 16.3 Developer Mode — not built in M22, and the reason is structural, not a preference

The blocker is S2 (§2): `ToolDispatcher` still dynamically imports from a JSON registry with no sandbox, and there is no per-user capability scoping to confine a hypothetical "write code" capability to its author. A Developer Mode built today would combine file-write capability with an import-anything dispatcher, gated only by a single approval click, on a codebase with zero execution isolation. That is an unacceptable arbitrary-code-execution surface, not a UX decision to defer. It becomes buildable once M22.4 (per-user grants) exists and a real sandbox (subprocess isolation, restricted imports, resource limits) is designed — neither exists yet, and neither is in scope here.

**The literal standing rule that must be encoded, not just documented:** no capability descriptor may declare an interface whose semantics are "run an arbitrary command" or "execute arbitrary code" — enforced as a registry lint test (§19.4), so a future PR cannot introduce Developer Mode by accident via a generically-named capability.

---

## 17. orchestrator.py extraction strategy

### 17.1 Current state (measured)

`orchestrator.py`: 5,476 lines. `_process_user_input_core`: ~1,132 lines. Two additional stale full copies exist on disk (`orchestrator.backup_before_router_fix.py`, 3,521 lines; `orchestrator.before_compatibility_fix.py`, ~979 lines) — dead weight, not live risk, but they inflate every repo-wide grep and are removed in M22.1 (§18).

### 17.2 Which M22 milestones actually touch it (checked, not assumed)

- **M22.2 (roles/sessions), M22.3 (endpoint auth), M22.5 (provider registry), M22.6 (router), M22.7 (usage), M22.9 (PWA): zero required changes to `orchestrator.py`.** Verified: `build_provider` (soon `ModelRouter`) is called only from the four M21 adapter/interpreter modules, never from `orchestrator.py` itself; roles/sessions/endpoint-auth are `server.py`-only; usage metering wires into the provider call site, not the orchestrator. This is direct evidence the M21 boundary was drawn in the right place.
- **M22.4 (CapabilityResolver) and M22.8 (modes): the only two milestones with a real touch point** — both need `_build_query_context`'s capability-catalogue assembly and `_executable_capability_ids` to consult the resolver instead of the registry directly.

### 17.3 The strategy: extraction is folded into the milestone that needs it, not a separate one

`_executable_capability_ids` (§3.4) already exists as an isolated, self-contained method — moving it (and the small amount of related catalogue-building logic in `_build_query_context`) into the new `capability_resolver.py` module is a **net line reduction** in `orchestrator.py`, done as the first sub-step of M22.4, before the one-line resolver call is added back. M22.8 (modes) reuses the same already-extracted seam and needs no further extraction of its own. **No standalone "extraction milestone" is warranted by the dependency evidence** — the standing rule is satisfied by disciplined editing inside M22.4, verified by `wc -l` as an explicit acceptance criterion on that milestone, not by inserting a new milestone with no independent objective.

---

## 18. Shadow-provider migration strategy

### 18.1 The brief's caution, checked against real import evidence

The brief warns not to blindly rewrite the shadow layer in one pass. I checked exactly which of the five flagged modules have *real* (non-docstring, non-dead-file) importers, because that determines whether this is one safe deletion or a genuine phased migration:

| Module | Real importers found | Verdict |
|---|---|---|
| `strategic_evaluator.py` | **none at all** — not even the dead backups | Delete outright, zero risk |
| `rost_evaluator.py` | `orchestrator.backup_before_router_fix.py` only | Delete outright once that backup is deleted |
| `hermes_forge.py` | `orchestrator.backup_before_router_fix.py` only | Delete outright once that backup is deleted |
| `core/semantic_interpreter.py` | `orchestrator.before_compatibility_fix.py` (dead) **and `test_semantic_interpreter.py` (live, passing, real regression coverage)** | **Cannot be blindly deleted** |
| `hermes_service.py` | `uri_core/app/main.py` (a standalone demo script, not part of the FastAPI app) **and `test_credential_hygiene.py` (live, passing, real regression coverage)** | **Cannot be blindly deleted** |

This confirms the brief's instinct was correct, but only for two of the five modules, and for a specific reason: `test_credential_hygiene.py` and `test_semantic_interpreter.py` currently prove real, valuable behaviour — "an API key is read only from the environment, never hardcoded, never silently substituted when absent." Deleting the modules would delete that regression coverage with nothing yet in place to replace it (M22.5's key handling doesn't exist until its own milestone).

### 18.2 The actual, phased plan

**M22.1 (now):**
- Delete both dead orchestrator backups, `strategic_evaluator.py`, `rost_evaluator.py`, `hermes_forge.py` — verified zero real callers once the backups are gone, zero dedicated tests exist for any of the three.
- Delete or neuter `uri_core/app/main.py` — it is not imported by `server.py`, not part of any test path, and is the one thing keeping `hermes_service` "live" per the brief's own finding #4. Severing it makes `hermes_service.py` fully unreachable from any production or demo entrypoint while its test remains valid.
- Add one boundary test: no module under `uri_core/core/` or `uri_core/app/` (excluding `hermes_service.py`/`core/semantic_interpreter.py` and their own two tests) imports either — locking in "unreachable" as a provable fact, not an assumption.
- Label both remaining modules' docstrings explicitly: *"Superseded by ModelProvider/build_provider (see model_providers/base.py, config/model_roles.py). Retained only for test_credential_hygiene.py / test_semantic_interpreter.py's regression coverage on environment-only credential handling. Not part of any live call path — see test_shadow_provider_unreachable.py."*

**M22.5 (provider registry, when user API-key handling ships):** port the *behavioural guarantee* those two tests check — "a key is read only from where it's supposed to come from, never hardcoded, never silently substituted" — onto the real `provider_keys` store, then delete `hermes_service.py`, `core/semantic_interpreter.py`, and their two now-redundant tests in the same milestone. This is a one-paragraph addition to M22.5's own scope, not a new milestone.

This is the correct reading of "do not blindly rewrite everything in one milestone": it was never about the three fully-dead modules (safe to delete immediately, confirmed by evidence), it was specifically about not discarding the two modules' real test coverage before their replacement exists.

### 18.3 Broken test discovery (bundled into M22.1 as it's the same cleanup pass)

`test_context_budget.py` has a genuine unclosed-parenthesis syntax error at line ~221 breaking `unittest discover`; fix it (it tests the still-present, M20-declared-unwired `ContextBudget` class — not in scope to remove that class, only to make its existing test importable again). `test_gmail_thread.py` and `test_pdf_reader.py` are manual demo scripts (module-level `print()`/`raise SystemExit`, no `unittest.TestCase`, require live Gmail credentials) that happen to match the `test_*.py` discovery glob; rename them to `manual_gmail_thread.py` / `manual_pdf_reader.py` (preserves them for manual use, removes them from automated discovery) rather than deleting outright.

---

## 19. Testing strategy

### 19.1 Keep the existing technique as the primary tool

The AST import-boundary test pattern (`_imported_module_names` + a set-difference assertion) is the strongest asset in this codebase and is reused, not replaced, for every new boundary in M22.

### 19.2 Categories

Boundary (AST, no runtime) · Isolation (real HTTP, per-user, following `test_multi_user_isolation.py` / `test_m21_file_store_isolation.py`'s proven pattern verbatim for grants/keys/usage/providers) · Authorization (negative matrix: USER cannot reach ADMIN routes; ADMIN cannot read user secrets/content) · Determinism (router/aggregation reproducibility) · Degradation (every §9 scenario) · Portability (§11.1's measured targets) · Live/opt-in (real-provider, skipped when unreachable, the `test_m21_context_window_live.py` pattern).

### 19.3 Regression baseline

The existing ~1,070-test suite stays green throughout. §18.3's fixes make it *honestly* green (zero collection errors) rather than green-with-three-known-exceptions.

### 19.4 New structural invariants required by this milestone (one test each)

1. `capability_resolver.py` never imports `ModelProvider`/`ModelRouter` (authority must never see provider identity).
2. `model_router.py` never imports `approval_gate`/`approval_store`/`dispatcher`/`capability_registry`.
3. No authorization-reachable code path references `experience_tier` (AST scan from `ApprovalGate`, `CapabilityResolver`, and every `/admin/*` handler).
4. `provider_keys` store is never imported by any prompt-assembly module (`provider_semantic_interpreter.py`, `model_reasoning_adapter.py`, `response_drafting.py`, `document_composer.py`).
5. Usage/dashboard aggregation module never imports `ModelProvider`/`ModelRouter`.
6. Every registered FastAPI route is present in an explicit `PUBLIC | USER | ADMIN` classification table (route-enumeration test — this is the direct fix-verification for S1).
7. No adapter/client-facing module imports `UriOrchestrator`/`ToolDispatcher`/`ApprovalGate`.
8. No `CapabilityDescriptor` in the registry declares a shell/arbitrary-command interface (registry lint — the literal Developer Mode guard from §16.3).
9. Mode resolution property: `resolved ⊆ granted ⊆ registered`.
10. `hermes_service.py`/`core/semantic_interpreter.py` unreachable from any live call path (§18.2, until their M22.5 removal).
11. `wc -l orchestrator.py` does not increase across M22.4 and M22.8 (a scripted check, run in CI, not merely a reviewer's manual glance).

---

## 20. Migration strategy

1. **M22.1's deletions are pure subtraction** — no schema, no data migration.
2. **Accounts**: add `role`/`experience_tier`/`status` with defaults, earliest `created_at` → ADMIN, bump `schema_version`, following the exact precedent `migrate_legacy_file_if_needed` already established for the M18/M21 user-scoping migrations.
3. **Capability grants**: every existing user_id defaults to the **full current registry** — this is what makes M22.4 behaviour-neutral for existing single-user installs on day one; grants only *narrow* behaviour when an ADMIN deliberately edits them afterward.
4. **Sessions**: existing in-memory tokens are simply lost once at deploy time (already the status quo on every restart today) — no migration needed, only a one-time re-login.
5. **Provider config**: existing `uri_workspace/model_roles.json` becomes the install-level default; per-user config starts empty and inherits from it — no existing deployment's behaviour changes until a user opts into per-user config.
6. **Usage**: no backfill; records begin at the meter's ship date.
7. **Backward compatibility**: the unauthenticated legacy-ambient path (`_resolve_context(None)`) is **retained through all of M22** — it still carries the entire pre-M22 test suite and every single-user deployment. It is not touched, deprecated, or flagged for removal inside this document; that decision belongs to M23 once every M22 milestone has proven the authenticated path is a strict superset of its behaviour.

---

## 21. What must explicitly NOT be built in M22

Every standing rule from the brief, restated as a build decision with its concrete reason:

| Not built | Concrete reason |
|---|---|
| Unrestricted Developer Mode | S2 (dynamic-import dispatcher) + no sandbox + no per-user grants until M22.4 (§16.3) |
| Messaging (Telegram/WhatsApp) approval channel | Approval-over-chat is replayable/spoofable with no resolved trust model; messaging may notify + deep-link to an authenticated client, never itself decide |
| Multi-node distributed mesh | `node_id` + honest unavailability (§12.4) gets the real user-trust benefit at a fraction of the risk of node-to-node RPC/job-forwarding/partition-handling |
| Cloud deployment | M22 builds the seam (TLS-ready, stateless-where-feasible, no machine-bound config); it does not stand up or operate a hosted instance |
| Dynamic skill-controlled UI implementation | Declaration format specified now (§15.1); enforcement/renderer needs `CapabilityResolver` + grants + skill promotion, none shipped until M22.4/M23 |
| Unnecessary database/account complexity | JSON + JSONL is sufficient for the realistic scale (§11.3); no email/phone/PII fields added to `UserAccount` — nothing in this milestone needs them |
| A second full round of native-mobile work | The Flutter scaffold (§12.1) already exists with `android/`/`web/` targets; M22.9 finishes and brands it rather than starting a parallel native track |
| Five provider adapters | Two adapter families cover the realistic near-term market (§6.2); Anthropic/Google wire-format-specific adapters wait for a concrete consumer |
| `implementation` model role, `INTERMEDIATE` tier | Both are unconsumed configuration surface with no caller in this milestone (§6.5, §4.1) |
| Removing `_resolve_context(None)`'s legacy ambient path | It carries the pre-M22 suite and every single-user install; premature removal is a regression risk with no corresponding M22 requirement (§20.7) |
| Blind deletion of `hermes_service.py`/`core/semantic_interpreter.py` | They carry real, currently-passing regression tests with no replacement yet; phased into M22.5 instead (§18) |
| A standalone "orchestrator extraction" milestone | Dependency evidence shows only two milestones touch the file, and both can absorb their own small extraction without growing it (§17) |

---

## 22. Final milestone dependency graph

### 22.0 Sequence evaluation

The proposed order (M22.1 → M22.9) is **kept**, with two evidence-based clarifications rather than a reordering:

- The dependency between **M22.4 (CapabilityResolver) and M22.5 (provider registry) is not a hard technical dependency** — they are independent axes (tool authority vs. model access) and could technically be built in parallel. They stay in the stated order for a **risk-priority** reason, not a dependency one: M22.4 closes the deeper structural gap (S3 — capability authority has no per-user axis at all), and it is the mechanism behind "models cannot grant themselves capabilities," which is the single most safety-critical property in this entire document. It goes first because it is more important, not because M22.5 cannot start without it.
- No milestone is inserted for orchestrator extraction (§17.3) or for a phased shadow-provider migration beyond what's already folded into M22.1/M22.5 (§18) — both were considered and rejected on dependency evidence, not merely to keep the count at nine.

```
M22.1 (cleanup)
   │
   ▼
M22.2 (roles, accounts, durable sessions)
   │
   ▼
M22.3 (endpoint authorization, edge hardening)  ◄── gates ALL remote/mobile work
   │
   ├──────────────────────────────┐
   ▼                              ▼
M22.4 (CapabilityResolver)   M22.5 (provider registry, 2 adapters)
   │                              │
   │                              ▼
   │                         M22.6 (ModelRouter, fallback, degrade)
   │                              │
   │                              ▼
   │                         M22.7 (usage, budgets, dashboard)
   │                              │
   └──────────────┬───────────────┘
                  ▼
            M22.8 (modes: office/diagnostic/admin, BASIC/ADVANCED UX)
                  │
                  ▼
            M22.9 (PWA/mobile client, branding, Android review APK)
```

### 22.1 Milestone detail

---

**M22.1 — Cleanup and honest baseline**
- **Objective:** remove dead code and the fully-orphaned two-thirds of the shadow provider layer; make the test suite honestly green; sever `hermes_service`'s only reachable path.
- **Dependencies:** none.
- **Files affected:** delete `orchestrator.backup_before_router_fix.py`, `orchestrator.before_compatibility_fix.py`, `strategic_evaluator.py`, `rost_evaluator.py`, `hermes_forge.py`; delete/neuter `uri_core/app/main.py`; fix `test_context_budget.py`; rename `test_gmail_thread.py`→`manual_gmail_thread.py`, `test_pdf_reader.py`→`manual_pdf_reader.py`; new `test_shadow_provider_unreachable.py`.
- **Security considerations:** none negative; removes attack surface (fewer live paths holding API-key-reading code).
- **Tests required:** invariant #10 (§19.4); full suite collection with zero errors.
- **Acceptance criteria:** `unittest discover` reports 0 collection errors; no import of `hermes_forge`/`rost_evaluator`/`strategic_evaluator` anywhere; `hermes_service`/`core.semantic_interpreter` unreachable from any live entrypoint (test-enforced); full suite green.
- **Commit checkpoint:** yes — standalone, revertible, no schema change.
- **APK/review build required:** no.
- **Review tier: implementation/test workflow only.** Mechanical, low-risk, fully verified by the tests it adds.

---

**M22.2 — Roles, accounts, durable sessions — COMPLETE**
- **Objective:** add `role`/`experience_tier`/`status` to accounts; first-account-becomes-ADMIN bootstrap; persist sessions (hashed tokens) so restart doesn't log out every device; device registry with revocation; introduce `PrincipalContext`.
- **Dependencies:** M22.1 (clean baseline).
- **Files affected:** `user_accounts.py`, `auth_session.py` (→ persisted store), new `devices.py`, new `principal_context.py`, `server.py` (new self-scoped `/auth/*` endpoints; `_resolve_principal` dependency).
- **Security considerations:** token hashing (never store raw tokens), migration must not grant ADMIN to more than exactly one account, revocation must be immediate.
- **Tests required:** migration idempotency; isolation suite extended for role/tier; invariant #3 (§19.4) — first version of the "experience_tier never read by authorization" test, even before there is much authorization logic to check it against.
- **Acceptance criteria:** existing suite green with roles migrated; a server restart no longer invalidates a still-valid session; `experience_tier` provably unread outside client-facing code.
- **Commit checkpoint:** yes.
- **APK/review build required:** no.
- **Review tier: independent deep review recommended.** Touches authentication; a mistake here (e.g. two accounts becoming ADMIN, or token hashing done wrong) is high-blast-radius and easy to miss in a fast implementation pass.

**As-built notes (two things this entry left underspecified, resolved during implementation):**

1. **`devices.py`'s actual shape.** The entry named the file but not its data model. Implemented as a genuinely thin module with **no persisted state of its own** — "a device" is a grouping, by client-reported `device_id`, of the session records `AuthSessionStore` already persists, not a second registered-device concept with its own lifecycle (no `first_seen`/`display_name`/etc., since nothing in M22.2 needs them). This required extending `AuthSessionStore` with `list_for_user()` and `revoke_by_ref()` — revocation-by-device must work from a *different* client than the one being revoked (e.g. revoking a phone's session from a desktop), which by construction never has the phone's raw token, only its `device_id`. `revoke_by_ref()` takes an opaque `session_ref` (the token's own hash, exposed only to its owning user) rather than a raw token — documented explicitly as non-credential, the same way `file_store.py`'s `StoredFile.to_reference()` is documented as non-authoritative.
2. **`PrincipalContext`'s actual footprint.** Introduced as specified, but deliberately **not** wired into the ~25 pre-existing endpoints — only the three new self-scoped M22.2 endpoints (`POST /auth/experience-tier`, `GET /auth/devices`, `DELETE /auth/devices/{device_id}`) construct and consume it. Retrofitting every existing endpoint's signature is exactly the endpoint-by-endpoint classification work §22's own M22.3 entry describes; doing it here would have widened this milestone's diff well past "add role/experience_tier/status to accounts" for no M22.2 benefit, since nothing yet gates on `role`.

Legacy-account migration was implemented as a **pure, deterministic computation inside `UserAccountStore._load()`** rather than a separate migration script: because `_load()` already reads every account in the file at once, it can correctly apply "the earliest `created_at` among accounts with no persisted `role` key becomes ADMIN, the rest become USER" without extra bookkeeping, and the result is stable/idempotent (a record that already has a persisted `role` is never recomputed) — see `test_user_accounts.py`'s `RoleExperienceTierAndMigrationTests` for the full behavioural proof, including that a fresh signup after migration never produces a second ADMIN.

---

**M22.3 — Endpoint authorization and edge hardening**
- **Objective:** close S1 and S5; classify every route; TLS-refusal-without-override on non-loopback bind; rate limiting; CORS lock-down; request size caps.
- **Dependencies:** M22.2 (roles must exist to gate the five endpoints as ADMIN).
- **Files affected:** `server.py` (route decorators + new `PUBLIC|USER|ADMIN` table), new `edge.py`/middleware module for rate limiting and size caps.
- **Security considerations:** this milestone exists entirely for security reasons; the whole point is closing S1/S5 before anything remote ships.
- **Tests required:** invariant #6 (route enumeration, §19.4); negative authorization matrix (USER → 403 on ADMIN routes); rate-limit trip test; oversized-request rejection test.
- **Acceptance criteria:** all five previously-unauthenticated mutating endpoints now require ADMIN; every route appears in the classification table; server refuses non-loopback bind without an explicit override flag.
- **Commit checkpoint:** yes.
- **APK/review build required:** no.
- **Review tier: independent deep review required.** This is the literal gate for all remote/mobile work; an incomplete route classification here reopens S1 under a different name.

---

**M22.4 — CapabilityResolver and per-user grants**
- **Objective:** close S3; make "models cannot grant themselves capabilities" concretely enforced per user, not merely per model-proposal.
- **Dependencies:** M22.2 (roles/`PrincipalContext`), M22.3 (its endpoint-classification pattern reused for the new grant-management endpoints).
- **Files affected:** new `capability_resolver.py` (receives the extracted `_executable_capability_ids` logic per §17.3), `orchestrator.py` (net-neutral-or-negative edit only), `approval_gate.py` (add the authoritative check), new `capability_grants.json` store, `server.py` (`/capabilities` becomes principal-aware; new ADMIN grant-management endpoints).
- **Security considerations:** the two-checkpoint design (advisory in query-context, authoritative in `ApprovalGate`) must both exist — a resolver consulted only advisorily would be decorative, not authority.
- **Tests required:** invariants #1, #9 (§19.4); `wc -l` non-increase check on `orchestrator.py` (invariant #11); isolation test — a user without a grant cannot execute that capability even holding a valid, otherwise-correct approval.
- **Acceptance criteria:** default migration grants every existing user the full current registry (behaviour-neutral); revoking a grant provably blocks execution at the `ApprovalGate` layer even if the advisory layer is bypassed in a test; `orchestrator.py` line count ≤ pre-milestone value.
- **Commit checkpoint:** yes.
- **APK/review build required:** no.
- **Review tier: independent deep review required.** This is the largest and most safety-critical milestone in the plan — it is the actual mechanism behind the brief's most important standing rule.

---

**M22.5 — Provider registry and second adapter family**
- **Objective:** `ProviderDescriptor`/`ModelDescriptor` with confidence labelling; packaged static catalogue; one OpenAI-compatible adapter; per-user provider config; encrypted write-only key storage; complete the shadow-provider migration (§18.2's second phase — delete `hermes_service.py`/`core/semantic_interpreter.py` and port their credential-hygiene test guarantees onto the real key store).
- **Dependencies:** M22.3 (endpoint auth pattern for `/providers/*`).
- **Files affected:** new `provider_registry.py`, new `model_providers/openai_compatible_provider.py`, new `provider_keys.py` (encrypted store), `config/model_roles.py` extended, `server.py` (`/providers/*` endpoints), deletion of `hermes_service.py`/`core/semantic_interpreter.py`/their two tests, new key-hygiene tests against the real store.
- **Security considerations:** the single highest-risk data type introduced in M22 (API keys) — write-only API, encrypted at rest, never logged/audited/prompted.
- **Tests required:** invariant #4 (§19.4); key round-trip test proving no read-back endpoint exists; `UnknownModelProviderError` still raised for an unregistered provider id (M21's no-silent-substitution guarantee, unchanged).
- **Acceptance criteria:** a user configures a second provider with their own key and it answers a real turn; no key appears in any log/audit/prompt/response; `hermes_service.py`/`core/semantic_interpreter.py` fully removed with their behavioural guarantee re-proven against the new store.
- **Commit checkpoint:** yes.
- **APK/review build required:** no.
- **Review tier: independent deep review required.** Secret handling; a mistake is a credential leak.

---

**M22.6 — ModelRouter, fallback, degraded mode**
- **Objective:** deterministic per-role provider selection with health/budget-aware fallback; the mandatory no-model degrade path (§9).
- **Dependencies:** M22.5 (needs `ProviderDescriptor`/per-user config to route over).
- **Files affected:** new `model_router.py`; the four M21 call sites updated to pass `principal` through `build_provider`; no change to `orchestrator.py` (§17.2, verified).
- **Security considerations:** auth-failure-does-not-fallback rule (§7.2) must hold, or a broken key silently starts spending a different provider's budget.
- **Tests required:** invariant #2 (§19.4); every §16-table failure scenario for provider routing specifically; the "all providers unreachable → deterministic capabilities still work" test (§9).
- **Acceptance criteria:** a forced-unhealthy primary provider falls back correctly and the response indicates which model actually answered; an auth error does not silently fall back; with zero reachable providers, approve/list/history/files all still function.
- **Commit checkpoint:** yes.
- **APK/review build required:** no.
- **Review tier: implementation/test workflow, with a targeted review of the fallback-chain logic only.** Lower risk than M22.4/M22.5 because it has no new data-authority surface — it is a deterministic selection algorithm, well suited to test-driven verification.

---

**M22.7 — Usage metering, budgets, dashboard**
- **Objective:** append-only per-user usage records; deterministic pre-flight budget check; zero-model-call dashboard aggregation.
- **Dependencies:** M22.6 (meters the router's actual calls; budget check runs inside the router's resolution step).
- **Files affected:** new `usage_meter.py`, new `usage_aggregator.py`, `model_router.py` (budget pre-flight + record-on-completion), `server.py` (`/usage`, `/usage/limits`).
- **Security considerations:** append-only avoids read-modify-write races; no content (prompts/responses) ever stored, only counts/durations/outcomes.
- **Tests required:** invariant #5 (§19.4); exact-aggregation test; confidence-labelling test (every numeric field carries `KNOWN|ESTIMATED|UNAVAILABLE`, never bare).
- **Acceptance criteria:** dashboard renders correctly from a fixture JSONL with zero model calls made during the test; pre-flight budget stop correctly routes to fallback/degrade rather than silently overspending.
- **Commit checkpoint:** yes.
- **APK/review build required:** no.
- **Review tier: implementation/test workflow.** Deterministic aggregation over already-designed data; low ambiguity.

---

**M22.8 — Modes and tiered UX**
- **Objective:** office/diagnostic/admin as capability filters; BASIC/ADVANCED provider UI and plain-language guidance; ceiling-reached flow.
- **Dependencies:** M22.4 (capability filtering), M22.7 (ceiling-reached needs usage/budget state to react to).
- **Files affected:** new `modes.json` + loader (mirroring `institutional_rules.py`'s packaged-defaults-plus-JSON-override pattern), `orchestrator.py` (reuses the M22.4 extraction seam — net-neutral edit only, §17.3), `server.py` (`/modes`, mode on `PrincipalContext`), client-side tier-driven view logic.
- **Security considerations:** the `resolved ⊆ granted ⊆ registered` narrowing invariant (§16.1) is the entire safety property of this milestone.
- **Tests required:** invariants #9, #11 (§19.4, `wc -l` check repeated for this milestone specifically).
- **Acceptance criteria:** switching mode never surfaces a capability outside the user's own grants; a BASIC user can configure a working provider without the client ever showing the words "token" or "context window"; `orchestrator.py` line count unchanged from pre-milestone.
- **Commit checkpoint:** yes.
- **APK/review build required:** no.
- **Review tier: implementation/test workflow, with a short focused review of the narrowing invariant only.**

---

**M22.9 — PWA/mobile client, branding, Android review APK**
- **Objective:** finish and brand the existing Flutter `android`/`web` scaffold into a working client of the M22 API; produce a side-loadable review APK with zero embedded secrets.
- **Dependencies:** all of M22.2–M22.8 (the client surfaces auth, providers, usage, modes — it needs all of them to exist and be stable).
- **Files affected:** `uri_ui/` broadly (new `assets/branding/`, `AndroidManifest.xml`, `build.gradle.kts` `applicationId`, `web/manifest.json`, theme/color tokens, login/onboarding/loading screens, `http_uri_client.dart` durable-token handling), no `uri_core/` changes.
- **Security considerations:** APK must contain no embedded API key/secret/hardcoded production URL (§13.2); TLS-only base URL once M22.3's TLS requirement is live.
- **Tests required:** Dart widget/unit tests for the client's own auth/token-refresh handling; a static check that no string literal matching a key-shaped pattern exists in the built APK's assets.
- **Acceptance criteria:** `flutter build apk --debug` (or profile) produces an installable APK; app displays "URI — AI COMPANION" branding with the approved logo across launcher icon, splash, and in-app wordmark; a physical device can sign in, converse, approve a pending action, and view the usage dashboard against a real (LAN or TLS-terminated) backend.
- **Commit checkpoint:** yes.
- **APK/review build required:** **yes — this is the milestone's primary deliverable.**
- **Review tier: implementation/test workflow for the client code; a short manual device-install check as the actual acceptance step (this is inherently a hands-on-device verification, not something a text-based review substitutes for).**

---

### 22.2 Summary table

| Milestone | Depends on | New security surface | APK required | Review tier |
|---|---|---|---|---|
| M22.1 Cleanup | — | none (removes surface) | no | implementation/test |
| M22.2 Roles/sessions | M22.1 | auth/session | no | **independent deep review** |
| M22.3 Endpoint auth | M22.2 | edge/network | no | **independent deep review** |
| M22.4 CapabilityResolver | M22.2, M22.3 | authorization | no | **independent deep review** |
| M22.5 Provider registry | M22.3 | secrets (API keys) | no | **independent deep review** |
| M22.6 ModelRouter | M22.5 | none new (uses M22.4/5) | no | implementation/test + focused review |
| M22.7 Usage/budgets | M22.6 | none new | no | implementation/test |
| M22.8 Modes/tiered UX | M22.4, M22.7 | none new (reuses M22.4) | no | implementation/test + focused review |
| M22.9 PWA/mobile/APK | M22.2–M22.8 | client-side token storage | **yes** | implementation/test + manual device check |

Four milestones (M22.2, M22.3, M22.4, M22.5) carry genuinely new security surface — auth, network exposure, authorization, and secrets, respectively — and are the four recommended for independent deep architecture review before merge. The remaining five are algorithmic, additive, or presentation work well suited to the implementation/test workflow alone, each with one or two narrowly-scoped invariants worth a focused look rather than a full review pass.
