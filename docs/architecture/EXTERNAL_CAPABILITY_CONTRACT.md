# URI external capability contract — v1 proposal

Date: 2026-09-15. Status: DRAFT, planning only. Not implemented or independently approved by Claude. Governed by ADR-018, URI AI Operating Policy and Model↔Runtime Contract. See [M32 plan](../plans/M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md) and [source evidence](../research/M32_ROOT_CAUSE_AUDIT.md).

## 1. Boundary and minimum implementation

External integration → ExternalCapabilityAdapter → existing MultiActionCapabilityRegistry → CapabilityDirectory/progressive discovery → canonical Brain proposal → deterministic gates → MultiActionDispatch/MultiActionExecutor → adapter → normalized evidence → existing narrative/claim checks → conversation history/UI.

The adapter is an implementation boundary, never a second planner or authority. Runtime-owned adapter handlers must be unreachable before authorization. Product names occur only in reviewed integration profiles, adapter normalization modules, UI labels and tests. Do not introduce a generic execute-shell, arbitrary URL request or Python import tool for the Brain.

Ship two transports in M32: **CLI** and **HTTP**. A reviewed profile supplies executable/request templates, configuration schemas, action descriptions and result mapping. CLI wraps local Python/document tools out of process too. HTTP covers explicit REST actions, including asynchronous jobs. Reserve MCP as a third transport implementing this same interface later; do not implement a custom MCP protocol now. Instruction/SKILL.md is a declarative recipe/context attachment referencing already registered actions, not a fourth execution transport. Arbitrary in-process Python loading is deferred. Specialist agents can later be called through CLI/HTTP/MCP as bounded result producers, not authorities or substitute URI Brains.

Supported standard profiles should add integrations without Core changes. An arbitrary repository lacking an executable interface/profile is **adapter required**, not automatically compatible. A maintainer may need a bounded adapter/profile; the ordinary User should not write one. No promise that every GitHub repo or OpenAPI document is automatically runnable.

## 2. Descriptor

All descriptors are data, statically validated before any package hook runs. IDs are immutable namespaced values, e.g. `external.<publisher>.<integration>`; action IDs are scoped beneath them. Display names and aliases are not identifiers. Unknown major contract versions and unsupported schema constructs fail closed.

| Field | Meaning |
|---|---|
| contract_version, capability_id, display_name, description | Versioned identity and concise purpose |
| integration_version, adapter_version | Upstream and bridge versions, tracked separately |
| source | Kind, canonical locator, immutable revision/digest, origin; never credentials |
| transport/profile_id | CLI or HTTP in v1; known reviewed template, never model-supplied code |
| categories, affordances, aliases | Vendor-neutral research/video/documents/etc.; deterministic discovery vocabulary |
| required_configuration | Typed nonsecret fields, required flags, defaults and help |
| credential_requirements | Named secret references and destination scopes; no secret values in descriptor |
| dependencies | Package/runtime/platform requirements and supported versions |
| permissions_requested | Reviewed operation/network/file scopes; requests cannot grant authority |
| actions[] | Name, purpose, input/output schema, effect class, approval/risk, compatibility class, bounds and evidence support |
| provenance_support | Supported locators/pages/segments/author/date fields, not a blanket credibility rating |
| lifecycle_support | Which install/connect/check/update/remove hooks exist; unsupported controls disabled with reason |

Instance state is separate: user_id, node_id, config_version, enabled, installed_version, qualification_record_id, readiness reasons, health checked_at/expires_at, registry_generation. Never let package metadata assert its own enabled/qualified status.

Action schema v1 uses a deliberately bounded JSON-schema subset: objects/properties/required/additionalProperties=false; string/integer/number/boolean/array/object; enum, length/item/range bounds; nested validation with maximum depth. Compile representable types into existing ActionSchema; enforce missing constraints in one shared adapter-boundary validator before execution and validate output after execution. Existing ActionSchema only validates a small subset; do not silently accept unsupported OpenAPI unions/references or pretend full JSON Schema compliance. Expand reviewed local references once at qualification; remote references are not fetched at execution.

## 3. Runtime adapter protocol

Conceptual signatures, not production code:

```text
describe() -> ExternalCapabilityDescriptor
check_requirements(context) -> RequirementsResult
plan_lifecycle(operation, target_version, context) -> LifecyclePlan
apply_lifecycle(approved_plan_id, context) -> LifecycleResult
health(context, action?) -> HealthResult
invoke(action_id, validated_inputs, execution_context) -> ExternalResult
poll(operation_id, execution_context) -> ExternalResult       # optional
cancel(operation_id, execution_context) -> ExternalResult     # optional
```

`execution_context` is runtime-created and carries principal, session/turn/action IDs, exact descriptor revision, granted scopes, approved scope reference, deadline, byte/item/request limits, cancellation and credential handles. Raw principal fields or approval booleans from external input are ignored. Only runtime integration management can call lifecycle methods; the Brain gets research actions, not installation powers.

Lifecycle plans expose exact source/version, user-local destinations, dependency list, requested scopes and expected effects. Hooks are reviewed operation handlers/templates, never shell snippets from a fetched README. Output schemas are not executable transformation languages; standard field-path mappings plus bounded trusted adapter code cover custom formats.

## 4. Lifecycle and truthful status

Detection → static requirements check → manual qualification → explicit install/connect approval → installed/connected → configured → health verified → explicit enable.

Detection is static: recognized URI profile, known package metadata, MCP descriptor or reviewed OpenAPI metadata. No importing Python, running package discovery hooks or fetching arbitrary recursive dependencies merely to identify source type. Unknown sources show requirements/adapter-review-needed; no marketplace crawler.

Store orthogonal state dimensions rather than one misleading enum:

- Presence: absent / installing / installed / connected / removing / failed.
- Qualification: pending / approved / rejected / stale, bound to source+dependency lock+adapter/profile digest.
- Configuration: required / complete; authentication: required / available / rejected.
- Health: unknown / ready / unhealthy / dependency_missing with per-action reasons and timestamps.
- Enabled: explicit boolean; update_available: advisory version badge.

UI labels derive in order: Disabled for intentional disabled instances (still show other issues); otherwise Not installed, Dependency missing, Configuration required, Authentication required, Unhealthy, Ready. Update available is independent. A doctor/version success is dependency health, not proof that a particular target transcript/page is retrievable. “Ready” requires the declared action probe to succeed and means last verified, not guaranteed future success.

Enable requires manual qualification, configuration, current health and existing URI grants. It changes only availability, not grants. Re-evaluate readiness and grants immediately before dispatch. Disable blocks new invocations immediately and increments registry generation; cancel/drain bounded in-flight work, label any returned evidence from an earlier generation. Remove waits for drain/cancel, detaches the instance and removes only URI-owned files/secrets explicitly selected in the removal plan. Retain already recorded evidence/history. Never invoke a global upstream uninstall that can delete other agents' configuration.

Updates stage a new pinned version, invalidate qualification, run requirements/health after review, then atomically swap the registry generation. On failure keep old version enabled if still healthy, or disabled with reason; never silently switch versions. In-flight actions retain immutable version handles. Restart is unnecessary for descriptor/config/enable changes; startup reconstructs a consistent snapshot from persisted metadata. Process restart during an external job must not resubmit it.

## 5. Authority, qualification and isolation

Keep existing skill-management ADMIN authority for host code install/update/remove and registration. An authenticated user can view safe metadata, configure their own credential references, check health and disable their own access; enabling is the intersection of reviewed host registration, their explicit availability choice, existing capability grants/mode/node scope and readiness. New external capabilities never inherit the resolver's legacy missing-grant “full registry” default: require explicit existing admin grant records for new external IDs. This is an additive denial for new IDs, not a grant-policy expansion for existing capabilities. Normal single-user admin installations receive the same simple flow. Non-admin users see Request administrator for host changes.

One authoritative permissions path: bind action-level required scopes to reviewed descriptors; CapabilityResolver checks external IDs against the existing grant store and runtime ceiling; action scope checks narrow further. Pass a real permission checker into canonical gates and recheck at executor invocation. Current Gmail aliases remain compatible until regression tests prove generic mapping parity. Absence of a checker may never allow an external action. No new external IDs in ToolDispatcher's arbitrary-import path.

Source → `QualificationPolicy.evaluate(candidate, review_record)` → installation → adapter → URI grants/approvals → execution. v1 policy validates a manually recorded Claude/Codex source review and User installation decision for the exact revision/dependencies. It is not automated code review. Record reviewer, date, source/revision, reviewed dependency lock, scope, findings, decision and evidence path; re-review material changes. User supplies/accepts the review record via the management flow; source text cannot attest to itself.

Future policy evaluators can add scanning, dependency inspection, sandbox tests, permission review, network controls, signing/trust, model-assisted review, reputation and quarantine by returning allow/deny/review_required plus reasons. Define hooks now; implement no scanner, scoring platform, signing service or autonomous quarantine system in M32.

User-local binaries are code running with the host OS user's privileges: M32 is **not** an adversarial sandbox. Manual review is a real trust prerequisite. Use isolated per-integration environments, per-user scratch/config/secret contexts, minimal inherited environment, no shell=True, approved executables and typed argv, bounded time/output, public HTTP(S) target validation and fixed service origins. A CLI that cannot avoid ambient cross-user credentials/home paths is not qualified for multi-user use. Do not pass browser cookies, all environment secrets, arbitrary local paths, private URLs or unrequested content to a tool. Existing security/approval boundaries remain authoritative at every URI entry, including lifecycle actions; external content cannot trigger nested execution.

Secrets use a generic user-scoped credential interface with an encrypted-at-rest implementation; reuse proven provider-key storage mechanics after checking namespacing, not provider IDs or global key defaults. No secret in URLs, logs, manifests, evidence or model context. If encryption is unavailable show configuration required, never add a hard-coded fallback key. No account-wide credential copying.

## 6. Normalized results and evidence

```text
ExternalResult {
  status: success|partial|pending|no_result|error|cancelled,
  capability_id, action_id, integration_version, adapter_version,
  invocation_id, operation_id?, retrieved_at,
  evidence: EvidenceRecord[], artifacts: scoped file references[],
  error?: {code, safe_message, retryable, retry_after?, effect_state},
  coverage: {attempted, completed, failed, truncated, limits_hit[]},
  continuation?: opaque runtime-owned handle
}
```

Map to existing `EvidenceRecord(source_type, evidence_id, retrieved_at, source_reference, excerpt, metadata)`. URL/locator → source_reference; extracted content → bounded excerpt; title/author/publication date, page number/document locator, transcript start/end seconds/language/generated-caption flag, upstream source ID, adapter/source revisions and truncation → validated metadata. Unknown fields remain null/absent. Retrieved time is never publication time. Each transcript segment or document chunk retains a stable source locator; generated captions remain labeled. Do not invent PDF page numbers from flattened Markdown: use pages metadata when supplied, otherwise a document/heading locator and explicit page-unavailable flag.

Respect current 10,000-character excerpt maximum and metadata validation. Keep long content in user-scoped result artifacts; evidence points to bounded chunks. Apply a total turn evidence budget before model context; disclose truncation and preserve omitted-count/continuation. Validate nested data size and redact secrets before EvidenceRecord construction; a malformed result is invalid_output, not no_result. Persist normalized records as part of scoped operation/result storage and rehydrate EvidenceLedger on resume; its default in-memory store alone cannot prove durable evidence.

Map ExternalResult into existing plan/execution/response envelope and call canonical narrative drafting/claim checks. External observations are untrusted evidence, not automatically VERIFIED facts. Never promote them directly through get_verified_evidence. Feed successful/partial evidence and honest errors back to Brain reasoning; preserve URLs/timestamps in visible answers and history. Audit both attempts and result normalization: principal/session, action/version, authorization decision, redacted input digest, timing, effect state, evidence IDs, limits, fallback reason.

## 7. Discovery, fallback and chaining

**Single selection path:** external tool → reviewed adapter/manifest → existing MultiActionCapabilityRegistry → CapabilityDirectory → existing canonical candidate preselection/Brain planning → gated dispatcher → evidence. No external skill router, external ranked catalogue, second scoring service or external-only planner. The registry bridge only compiles/publishes metadata and handlers; it cannot rank prompts or execute them.

Use `decision_engine.preselect_candidate_ids` → `capability_relevance.plausible_matches` as the canonical deterministic candidate path, with `CapabilityDiscoveryEngine` retained for existing progressive action discovery. Do not run both as competing external ranking stages. `core/capability_planner.py` is a legacy name-specific scorer, not the normal canonical planner; normalized metadata alone does not fix it. Leave its existing behavior intact. Canonical rollback/model failure does not authorize external execution through its legacy path.

### 7.1 Normalized selection metadata

Each reviewed manifest declares, at action granularity: purpose/description; category; `intent_signals` (operations, topics and bounded synonyms); accepted source kinds/MIME types/host patterns; required input fields; produced evidence kinds; action compatibility class; limitations; and optional short example utterances. Display aliases are separate from semantic keywords. Existing capability/action IDs, schemas, approval and permission declarations remain authoritative. Signals describe supported operations, not vendor preference or an arbitrary “priority” score.

Compile these fields into registry summaries/details and Directory projections through a shared small extension. Preserve old entries with empty optional fields. Expose compact searchable metadata at Level 1; full schemas only for candidate actions at Level 2. Keep lifecycle/grants/health outside the source manifest in a runtime-owned snapshot. Bound signal lists and descriptions; reviewed metadata is data, not prompt instructions. A claimed capability becomes selectable only if its implemented action/schema/profile and readiness support it.

### 7.2 Eligibility and ordinary prompts

1. Snapshot the current user/node registry generation, enabled state, qualification, grants and per-action health/configuration. Known disabled/not-installed/missing-dependency/auth/quota/unhealthy actions are not executable candidates. A non-executable diagnostic view retains safe labels/reasons for explanation and recovery; it is not a second registry/router.
2. Rank available actions/capabilities using existing deterministic overlap on normalized purpose/signals/source kind/output kind. Never rank installation state as semantic relevance. No-match/weak match returns existing clarification/unsupported behavior; no unrelated tool solely because it is healthy.
3. Fix the observed top-K issue minimally: compare positive raw overlap when discriminating overlap ties, then stable ID; exclude zero-evidence topical matches while retaining existing foundational/active-goal candidates. Duplicate affordance descriptions must not suppress genuine alternatives. Use the same compatibility evidence in the existing Unsupported Gate so candidate recall and gate interpretation agree. Prove weak/generic-only false positives remain rejected.
4. Existing canonical Brain receives candidates, actual schemas and reasons, resolves task inputs and proposes actions. Selection is advisory; fresh runtime validation/grants/readiness/approvals control invocation. No additional model-based evaluator. Per-action stale/unknown health triggers a bounded check before execution, not a fabricated Ready state; failure returns a structured reason to normal planning/feedback.
5. Results follow the existing gated MultiActionDispatch/MultiActionExecutor and normalized EvidenceRecord/plan-execution-response path. Fallback stays inside the same candidate and gated execution system. Every transition rechecks registry generation/authorization; a tool disabled after selection cannot execute.

V1 lexical matching does not promise universal paraphrase or language coverage. Use reviewed localized/synonym signals where supported and the existing Brain's interpretation; do not add a translation/routing model service. Candidate recall on normal example prompts is an explicit acceptance criterion.

### 7.3 Explicit tool selection

Resolve a direct top-level user request such as “Use <registered display alias> …” into a turn-scoped `requested_capability_id` constraint in existing request/candidate context. One vendor-neutral alias matcher, populated from registered metadata; require exact normalized alias boundaries, not substring matching. Preserve the remaining goal for action selection. Quoted evidence, negated mentions, tool descriptions and “compare X with Y” do not become commands; ambiguous aliases/multiple requested tools use existing clarification unless a validated multi-action request explicitly specifies both.

Bind this constraint from the actual user request, never model output; preserve it through candidate truncation, contract validation, gates and fallback. Only matching integration actions may perform the explicitly scoped task. Keep existing foundational context available without allowing it to override that external task constraint. No automatic installation or enablement. Unknown name reports not installed/unknown; disabled/auth/quota/unhealthy returns exact state. If explicit tool lacks the required action, report task_unsupported rather than choosing a different action because the vendor matched.

Explicit “Use <alias>” constrains candidates to the installed matching integration and shows its exact availability problem if unusable. Default is strict selection: no silent switch away from an explicitly requested tool; ask whether an alternative is acceptable. No-match does not silently invoke a broad tool; existing clarification/unsupported behavior remains.

### 7.4 Three metadata-driven examples

| Profile | Declared signals and evidence | Goal-only example → existing planner selection |
|---|---|---|
| Agent Reach video profile | video search, YouTube, transcript, subtitles, timestamps; video URL/query inputs; video metadata/timed text outputs | “Find YouTube discussions of model training and show relevant timestamps” → search_videos then read_transcript. Alias “Agent Reach” constrains to this profile; health applies per action. |
| Firecrawl site profile | site map, crawl, linked pages/PDF, website research; public URL inputs; page/document evidence outputs | “Go through this website and its linked PDFs for age relaxation” → map/crawl/read_document. Alias “Firecrawl” constrains the same planner; no product branch. |
| Unrelated document-extraction fixture | local document, extract table, spreadsheet rows; approved attachment locator/PDF MIME; table/document evidence | “Extract the tables from this attached PDF” → fixture extract_tables, not web crawl merely because both mention PDF. Add manifest/profile/normalizer only; no new planner/Core edits. Fixture proves selection mechanics, not a new shipped document integration. |

### 7.5 Failure policy

Normalize errors: not_installed, disabled, dependency_missing, configuration_required, authentication_required, quota_exhausted, rate_limited, service_unavailable, task_unsupported, invalid_input, invalid_output, permission_denied, approval_required, deadline_exceeded, no_result, outcome_unknown. Distinguish 429 rate limiting from known exhausted credit quota; unknown codes stay service errors.

One compatible alternate per failed action, maximum two attempts total, only for qualified/enabled/granted actions with the same semantic input/output contract and equal-or-narrower data/permission/cost scope. Never fallback to installation, enablement, authentication changes, or an unapproved data recipient. Preserve valid partial evidence and return it to the Brain. No automatic fallback for denied/cancelled/approval-required or side-effect outcome_unknown. No_result is a legitimate answer, not an unlimited retry trigger. Transient polling reads may retry twice within deadline; never blindly resubmit a job-creation POST or ambiguous CLI invocation.

Use existing execute_chain reference binding, not a new general workflow engine: maximum six research actions, all references from validated prior results, each step reauthorized. External adapter retries/fallback apply at action boundary before execute_chain halts. Supported v1 composition: discover/map/search → select bounded locators → read/crawl/transcript → normalized evidence → existing Brain summary. A “research” job may poll a remote job internally but cannot call unrelated tools, install dependencies or elevate permissions.

## 8. Bounded operations and future transports

Prototype defaults: at most 20 mapped URLs, 10 crawled HTML pages, 3 PDFs (10 pages each where service supports limits), 3 video results/2 transcripts, six action steps, two candidates per action, 30-second request timeout, five-minute total operation deadline, 10 MiB returned content per operation and 30,000 characters selected evidence per Brain turn (split into valid records). These are URI defaults, not upstream guarantees or prices. Refuse unsupported hard limits where required, stop at attainable limits, and label partial coverage. Account/provider caps may narrow all limits. Public read requests can consume API credits; display cost class and User-approved budget scope at connect/launch.

Remote jobs: invoke returns pending with owned operation handle; persist upstream job ID, scope/version/budget and session before exposing it. Poll only that job using authenticated management/runtime continuation; completion enters canonical result-feedback once using a durable completion marker. No duplicate submissions on reconnect. A small operation ledger plus UI polling/resume is sufficient; no scheduler/queue platform. After restart, pending operations remain pending/unknown until reconciled. If submission result was lost and upstream has no usable idempotency lookup, mark outcome_unknown; do not start another paid job automatically.

MCP later: map tools/list input schema into reviewed actions, tools/call results into this envelope; server-provided annotations do not grant trust. Connect-time review + fixed tool set/version; newly advertised tools require qualification. CLI and HTTP profiles never become an escape hatch to arbitrary MCP execution. SKILL.md later: import as untrusted, bounded advisory text referencing approved action IDs; no automatic shell/install instructions, no replacement of operating policy. OpenAPI import later compiles supported operations into the same HTTP profiles; unsupported auth/schema/features remain adapter-required.
