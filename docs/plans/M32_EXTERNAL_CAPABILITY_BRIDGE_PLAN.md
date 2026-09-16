# M32 — External Capability Bridge

Date: 2026-09-15. **Plan ready for review; DRAFT, implementation NOT AUTHORIZED.** Prepared by Codex at User request; not a Claude architecture approval or final audit. No installation, production changes or tests performed. [State](M32_STATE.md) · [Contract](../architecture/EXTERNAL_CAPABILITY_CONTRACT.md).

## 1. Objective and scope

Make reviewed external tools usable through ordinary URI prompts with minimal per-integration work: Tools & Skills → Add source → detect compatible profile/type → show requirements → reviewed Install/Connect → Configure → Health check → Enable. Use existing URI Brain, runtime gates, grants, approvals, user isolation, evidence and history.

Agent Reach and Firecrawl prove the same bridge with two different transports. They do not define URI's integration architecture. Subsequent supported integrations primarily add a reviewed profile/configuration/normalizer, not branches throughout URI Core. Research/crawling, video, document, productivity and local tools fit action descriptions; future MCP/REST/OpenAPI/SKILL.md/specialist-agent support has defined extension points. Unsupported source types truthfully require an adapter; no universal automatic integration claim.

**In v1:** CLI + HTTP transports, manual qualification records, versioned action descriptors, user-local managed install/connect, health/config/enable/disable/update/remove lifecycle, bounded operation ledger, normalized evidence, deterministic discovery/explicit selection, one compatible fallback, bounded chaining, simple Settings page and two live acceptance proofs.

**Deferred:** marketplace, unattended installs/updates, dependency solver platform, automated security evaluator/scanner, sandbox infrastructure, signing/reputation, automatic quarantine, arbitrary dynamic imports, full OpenAPI importer, MCP execution implementation, account-wide integrations sync, browser-cookie harvesting, cloud transcription fallback, self-hosted Firecrawl deployment, specialist-agent orchestration, sophisticated model-based task evaluator. SKILL.md content is advisory, never a capability grant. Tools & Skills is not Model Providers.

## 2. Baseline, governance and stage gates

Reuse completed M30.8 canonical cutover rather than re-auditing earlier architecture. Source inspection at HEAD `8fa9ac61857871a287ff976aac7b12c6ac49908b` found the concrete seams in [Stage 1 audit](../research/M32_ROOT_CAUSE_AUDIT.md). Current active milestone remains M31 REPAIRING; this next-milestone plan does not close it or change its write ownership. Hybrid UI planning also remains separate; M32 adds one Settings category without rebuilding the shell.

User-directed loop: Claude architecture/planning review and independent read-only audit; Codex implementation/tests/runtime repairs; User live acceptance. Antigravity is not involved. No auto-start or release. Existing Claude release authority and explicit applicable commit/push instruction remain intact.

Four-stage records: [root-cause audit](../research/M32_ROOT_CAUSE_AUDIT.md) → [canonical architecture](../architecture/M32_CANONICAL_ARCHITECTURE.md) → [migration](M32_MIGRATION_PLAN.md) → implementation reports/live validation. Drafts supplied now; no false claim that live Stage 1 evidence or Claude freeze exists. Before implementation, resolve M31 overlap, freeze source/dependency review and these stages, then receive an implementation handoff. Ordinary plan auto-approval does not override this User's explicit “do not implement yet.”

## 3. Reference integrations and route choice

### Agent Reach — reviewed platform profile over CLI

Chosen source identity: [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach), subject to exact revision/manual review before installation. Do not install an unrelated same-name registry package. This project's platform layer configures/checks upstream tools; use its reviewed platform profile through URI's CLI transport, not an invented universal Agent Reach API.

Initial action set: `search_videos(query, limit)`, `read_video_metadata(url)`, `read_transcript(url, languages)`. All public read-only. Use pinned `yt-dlp` from the reviewed Agent Reach environment; typed argv search/metadata/subtitle templates and VTT-to-segment normalizer live in the profile/adapter. Record Agent Reach profile version plus actual upstream executable version in provenance. The [current video reference](https://raw.githubusercontent.com/Panniantong/Agent-Reach/main/agent_reach/skill/references/video.md) documents these routes. Enable only qualified channels; platform breadth in marketing is not proof every channel works.

Install/connect the reviewed Git revision and locked dependencies in a URI-owned per-integration environment using existing Python tooling, without admin/system modifications. Detect existing reviewed local installation as an alternative. Show yt-dlp/JS runtime/config requirements separately; doctor output is advisory readiness input. Run a small real transcript probe before enabling transcript availability. No global upstream installer/uninstaller, no modifications to Claude/Codex skills folders. Optional upstream transcription needs separate qualification/credentials and is deferred. A future reviewed public web/GitHub/RSS channel is another profile action, not a new Core branch.

### Firecrawl — HTTP v2 profile

Choose hosted authenticated HTTP API for lowest prototype setup burden; no SDK or server deployment required. [API introduction](https://docs.firecrawl.dev/api-reference/v2-introduction) is the source for this route. Connect accepts a user-scoped key reference and declared endpoint, then verifies a bounded non-mutating probe. Key presence alone is not Ready.

Profile actions: `map_site(url, limit)`, `crawl_site(url, max_pages, max_depth)`, `read_document(url)` and shared operation poll/cancel. Adapter maps [map](https://docs.firecrawl.dev/api-reference/endpoint/map), [crawl](https://docs.firecrawl.dev/api-reference/endpoint/crawl-post), [job status/paging](https://docs.firecrawl.dev/api-reference/endpoint/crawl-get) and [scrape/PDF support](https://docs.firecrawl.dev/features/scrape) into normalized results. Parse content/metadata/pages when present, preserve failed/omitted URLs and credits/limits, never claim every page was read from completion counts alone.

No Firecrawl-specific logic in planner, gates or evidence consumers. Paid crawl-job creation is not treated as a harmless retryable GET: require configured budget/data-destination scope, record job ID, poll without resubmitting, and report ambiguous submission as outcome_unknown. Public research is read-only with respect to target sites but can consume service credits. No live API use or spend authorized by this plan-writing request.

### Integration extensibility proof

In addition to both live profiles, register a tiny fixture-only third profile backed by a local JSON CLI or test HTTP service. It must install/connect, disclose schema, be discovered, execute through gates and produce EvidenceRecord using only a new profile/normalizer and tests. Assert no changes to decision_engine, canonical_execution, dispatcher or orchestrator to add this third profile. This demonstrates extensibility without expanding the product rollout.

## 4. Production integration and implementation batches

### Selection architecture clarification

Target: **External tool → adapter/manifest → URI capability registry → existing capability planner → dispatcher → evidence.** No separate external-tool router is authorized. Detailed metadata, eligibility, explicit selection and three-profile examples are in [contract §7](../architecture/EXTERNAL_CAPABILITY_CONTRACT.md#7-discovery-fallback-and-chaining).

Read-only inspection distinguished the existing canonical planner from the older `CapabilityPlanner` class. The canonical /ask path already uses CapabilityDirectory, deterministic preselect_candidate_ids/plausible_matches and the existing Brain's action proposal. The older class reads active_tools and scores hard-coded names; new names score zero. Do not add product cases there, duplicate its authority or imply that simply inserting JSON makes an external tool executable. Preserve legacy behavior; external execution depends on the canonical path, including honest unavailable behavior during rollback/failure.

Small extensions justified by [E11–E16](../research/M32_ROOT_CAUSE_AUDIT.md): optional normalized action/intent metadata through registry/Directory; cheap runtime-owned eligibility reasons; raw-positive-overlap tie-break for shared research affordances/top-K; generic explicit-alias request constraint; consistent Unsupported Gate interpretation. All belong in existing registry/planning/gate modules. No external router module, learned evaluator or new planner. registry_bridge is a descriptor publisher only.

Proposed module paths below are implementation targets, not files claimed to exist. Preserve dirty work; record scoped diff/hash baseline and test commands before editing. Keep orchestrator.py unchanged; composition belongs in server's existing user-context setup and small external modules. Core modifications must be vendor-neutral and confined to demonstrated seams.

### Batch A — contract, lifecycle and isolation

- New `uri_core/external/{contract,profiles,lifecycle,store,qualification}.py`; reuse SkillValidator digest/static-validation patterns, portable_paths, existing principal/credential/grant mechanics. One lifecycle authority for new instances; avoid maintaining a duplicate legacy skill state.
- Source metadata/requirements detection must not execute unreviewed code. Manual review record bound to exact source/profile/dependency revision; install user-local approved artifacts only. No raw model-supplied command/hook. Provide explicit enable/disable, stage-update/swap, scoped remove, per-user configuration and health reasons.
- Keep existing SkillInstaller API/ledger behavior intact; existing enabled skills are metadata-only, never silently migrated into executable registration. Generic ID collisions/version incompatibilities rejected.
- Tests: lifecycle transition table; missing dependency/config/auth, stale review, failing update rollback, optional hooks unsupported, dirty-worktree preservation, path escape rejection, user A/B config isolation, secrets redaction, source inspection cannot execute code. Approval request binds immutable lifecycle plan/version.
- Exit: deterministic contract and lifecycle pass tests; no adapters exposed to normal execution yet; report ready for Claude review.

### Batch B — gated registry/discovery/dispatch/evidence

- New `external/{registry_bridge,permission_binding,result_normalizer,operation_store}.py`. Modify `core/multi_action_dispatch.py`, `core/canonical_execution.py`, `core/capability_directory.py`, bounded `core/decision_engine.py` candidate metadata/alias handling, `core/capability_relevance.py` shared-affordance ranking and `core/decision_gates.py` consistent eligibility/constraint enforcement as justified by E11–E16. Extend optional metadata in `capabilities/base.py`/`registry.py` and existing `discovery.py` projections only as needed; `capabilities/executor.py` only for shared validation/fallback hooks and correct result recording. Composition in `app/server.py` user-context construction. No product conditions or external-only scoring stage.
- Replace the Gmail-only canonical multi-action selection with lookup of registered capability/action. Preserve Gmail alias permissions and legacy fallbacks. Registry publication is an atomic immutable generation; per-user dispatch checks enabled/readiness/grants again. Never assume registry presence equals authorization.
- Wire actual permission checker to gates and invocation; external absent grants deny despite legacy resolver defaults. Action approvals come from reviewed metadata/runtime stores, never tool/model booleans. Failures never enter success-only context resolver state. Add audit sink to production path explicitly; an in-memory executor audit_log alone is insufficient.
- Reuse Directory/preselection for deterministic affordance matching. Exact known aliases implement explicit tool selection. Preserve foundational candidates, model failure behavior and canonical Brain narrative. Fallback/chaining follow contract caps and scope constraints; all alternate actions traverse the same gates.
- Normalize into EvidenceRecord; scoped durable operation/result artifacts rehydrate evidence and preserve history. Shared operation completion feeds canonical Brain once and updates existing conversation turn/result, not a separate chat. Implement one scoped operation poll service; no arbitrary public tool-execution endpoint.
- Tests: existing canonical/multi-action/Gmail/approval tests; new no-checker denial, grant revoke between selection and execution, disable race, cross-user/session IDs, output schema bounds, credential redaction, partial/no_result/errors, explicit selection, alternate reauthorization, cancellation/no retry of unknown effect, duplicate completion/restart behavior.
- Exit: fixture profile works through actual `/ask` production path into Brain-visible evidence, denied cases invoke no adapter, existing Gmail/remember_fact behavior unchanged. Claude review before live profiles.

### Batch C — two real profiles, bounded research chains

- New `external/adapters/{cli,http}.py`, reviewed integration profiles and product-specific normalizers below `uri_core/external/integrations/`. Install plans/health checks/result parsers live here; Core remains generic.
- Agent Reach profile connects exact reviewed environment; Firecrawl profile connects authenticated endpoint. Implement only listed initial actions. Same lifecycle manager, Registry, executor and normalized result contract for both.
- Add CLI timeout/output caps/argv validation, HTTP endpoint/auth allowlist and redirect checks, asynchronous job tracking/paging, no duplicate POST retry, VTT timestamps, generated captions and missing PDF-page metadata handling.
- Tests: recorded protocol fixtures + deterministic fake process/HTTP tests; integration health disabled/unhealthy states; quota vs rate limit vs no result; remote-job partial/error/restart; invalid JSON/oversized output; third-profile no-Core-change proof. Scoped external smoke tests require prior manual review/installation decision and configured account.
- Exit: real source results can traverse canonical pipeline; no CLI-only demo accepted as URI integration. Both live acceptance tasks required before milestone completion, even if external availability delays one.

### Batch D — Tools & Skills and full acceptance

- Backend API lives in new `app/external_capability_routes.py` included by server; classify all routes in `app/route_classification.py` and test auth roles. No anonymous package detail/secrets exposure. API namespace `/external-capabilities` (avoid overloading legacy metadata-only `/skills`).
- Planned API: GET list/detail (authenticated, filtered safe metadata); POST detect (ADMIN, static); POST `/{id}/lifecycle-plan` and `/{id}/apply` (ADMIN, exact plan/version + idempotency token); PUT own config/credential reference (authenticated and scoped); POST health; PUT own enabled (requires reviewed registration + grant); GET owned operations; POST owned operation cancel. No execute action endpoint outside canonical `/ask` and its approved runtime continuation. Host registration affects ceiling only; user config cannot change executable/source/permissions.
- Flutter `services/uri_client.dart`, `http_uri_client.dart`, `app_state.dart`, typed external models and `screens/settings/tools_skills_screen.dart`, settings_shell category. Reuse URI UX skill/reference-library Settings master/detail and shared semantic tokens; no new primary navigation, marketplace, shell redesign or topbar theme control. Coordinate with Hybrid UI batch ownership before touching shared files.
- List/detail: name, purpose, version, installed/connected, enabled, action categories, configuration, per-action health + checked time, update availability, Configure/Check/Enable/Disable/Update/Remove or Reconnect. Show who can manage host install. Add flow recognizes supported source/profile, shows exact requirements/review state, then explicit Install/Connect and health. Backend failure is unavailable, never empty list/Ready. Empty list offers Add; failed operation keeps retryable detail and prior working configuration.
- Chat displays pending external operation, evidence links/timestamps, partial coverage and recovery suggestions using existing result surfaces. Compact/Workspace must keep the same active turn/session; M32 does not create a parallel chat. No reset of composer draft while opening Settings. Appearance follows existing four-theme direction; pixel fidelity remains subject to the approved Hybrid Artifact access, not the old dashboard.
- Tests: new Tools & Skills widget/client tests, route auth matrix, lifecycle idempotency and error states; retained chat/attachments/history/model-selector tests. Full regression plus live cases below; independent Claude audit and User acceptance after Codex repairs.
- Exit: all ten acceptance requirements in §6 evidenced, no new regressions, Claude final audit/User live acceptance. No commit/push by Codex.

## 5. Compatibility, limits and rollback

Existing skills metadata, Gmail, local memory, model provider/override and approval history keep their semantics. Do not introduce a second grants store or permission auto-expansion. Keep external instance metadata separate from legacy SkillInstaller status and clearly label legacy metadata-only entries. External install/update may never mutate application dependencies or global agent configuration.

Rollback point: scoped pre-batch patch plus metadata backup captured before first change; disable external bridge publication, restore only batch-owned code/metadata, retain evidence/history and reviewed environment for diagnosis. Never reset whole dirty tree or auto-remove shared packages. Installation failure leaves recorded failed state; update failure retains previous version; unknown remote submission is reconciled, not retried. Removing integration does not remove prior answer citations.

Contract defines limits and failure policy. Prototype fallback is deliberately small: at most one compatible alternative, no silent alternative for explicit selection, no side-effect replay, no denial bypass, bounded six-step chain. A partial supported answer is preferable to claiming completeness or terminating without showing usable evidence. Firecrawl and Agent Reach need not support identical actions: fallback only where declared semantics overlap. Test fallback with compatible fixture actions instead of pretending YouTube can replace a site crawler.

## 6. Acceptance evidence

Each row records PASS/FAIL/NOT RUN, source/version, exact request/session/operation IDs, redacted logs, evidence IDs, screenshot/result and independent audit reference. All currently NOT RUN.

| # | Required proof |
|---|---|
| 1 | Versioned generic contract validates CLI and HTTP profiles; unsupported schema rejected |
| 2 | Agent Reach reviewed profile invokes actual public video search/transcript through URI |
| 3 | Firecrawl hosted HTTP profile uses same lifecycle/registry/executor/evidence architecture |
| 4 | User-local install/connect, missing requirements, real health, enable/disable work from Settings |
| 5 | Normal goal-only prompts discover actions and invoke through canonical gates; no product keyword required |
| 6 | Explicit “Use Firecrawl…” / “Use Agent Reach…” selects exactly that integration or reports its failure truthfully |
| 7 | Normalized content/locators/timestamps returns to Brain, grounded answer/history and follow-up references |
| 8 | Disable/remove/restart/in-flight races preserve URI/Gmail/chat/history; no adapter called while disabled |
| 9 | Third fixture profile requires profile/config/normalizer only, no additional Core branching |
| 10 | Manual qualification required; future policy hook denial prevents install/enable without changing bridge; no automated security platform |

### Real deep-site task D1

Prompt: “Go through the UPSC recruitment advertisement website and its linked PDFs and find references to age relaxation. Give document titles, dates, links and the relevant extracts; distinguish historical notices from current rules and state what you could not inspect.” Seed: `https://upsc.gov.in/recruitment/recruitment-advertisement`.

Known real document fixture: [2024 Personal Assistant special advertisement](https://upsc.gov.in/sites/default/files/AdvtNo-51-2024-Spcl-PrsnAsst-engl-070324_0.pdf), whose indexed text includes age-relaxation sections. It is a historical retrieval test, not legal guidance or evidence of current policy. The seed page could not be opened by this planning web reader; its current link graph must be confirmed in Stage 1/live setup. No assumption that this older PDF is currently linked from the seed.

At preflight freeze a currently reachable page→linked PDF pair from that real site and record the actual href, date and content hash. The known historical PDF can independently verify parsing, but cannot substitute for the link-discovery part. Run ordinary prompt then explicit Firecrawl variant on the same bounded target. Required: map/discover links, fetch at least two HTML pages and one genuinely linked PDF within configured limits, preserve document URL and page/heading locators, extract at least one independently checked occurrence, show actual coverage/failed URLs, and feed evidence back through Brain. Follow up “Which document supports the first finding?” and resolve same evidence. If target blocks access or no PDF is linked, mark blocked external evidence and select a documented equivalent real recruitment subpage before freezing fixture; never claim a canned output is a live crawl.

### Real video/transcript task V1

Prompt: “Find Andrej Karpathy’s YouTube discussion ‘Intro to Large Language Models’ and show the relevant timestamps where he explains model training versus inference, with transcript evidence.” Real target: [Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g). Search result and target identity were verified via the primary video page; caption availability has NOT been tested.

Run normal prompt and explicit “Use Agent Reach…” variant. Required: actual bounded video search returns title/author/URL; select correct video; retrieve nonempty captions, not only metadata; normalize at least two segments with real start/end times; answer cites playable timestamp links and segment evidence, labeling auto-generated captions if applicable. Independently compare cited segments to the retrieved subtitle file and video. Follow up “Show the source for the second explanation” using same-session evidence. Missing/blocked captions must report unavailable/auth/no_result accurately; no invented transcript, no automatic audio upload/transcription fallback. If the real video's captions change, freeze another documented public subtitled video before acceptance; no fake live success.

### Negative, regression and live UI cases

**Selection-specific acceptance:** add metadata-only fixture profile for unrelated attached-document table extraction; assert correct candidate/action versus Firecrawl's web PDF action. Test ordinary goal-only site/video/document prompts, explicit aliases, exact name boundaries, quoted/negated mentions, ambiguous duplicate aliases, and explicit unavailable/unsupported integration with no silent fallback. Add a third candidate with identical research signals and prove top-K still includes viable alternatives; zero-overlap unrelated tools must not win. Test per-action health, stale refresh, disable/revoke between selection and dispatch, source-kind mismatch, foundational candidate retention and active-goal continuation. Under canonical rollback/terminal model failure, external requests must not execute a vaguely matching legacy tool. Assert same normal dispatcher/evidence/Brain path and no additional Core edits for the third profile. Re-run `test_capability_planner.py`, `test_capability_directory.py`, `test_decision_engine.py`, `test_decision_gates.py` and multi-action/canonical execution suites. All remain NOT RUN during planning.

Missing executable; broken runtime; missing key; rejected key; quota; 429 rate limit; 5xx; no result; invalid/oversized output; disabled/deleted integration; stale health; revoke permission after selection; expired qualification; another user's operation/evidence ID; denied approval; explicit-tool unavailability; fallback destination outside scope; partial crawl; duplicate click; restart pending remote job; update failure; uninstall preserving unrelated files; new unknown action after update. None can bypass authority or falsely report Ready/success/empty.

Run scoped component/integration tests per batch, then existing full Python regression and Flutter `flutter analyze`/`flutter test`. Determine exact established Python invocation/interpreter from current baseline, record it rather than invent counts. Include canonical execution, multi-action, approval, user isolation, route classification, evidence integrity, provider failure/override and chat/attachment/history suites. Validate actual Brain discovery → proposal → gate → execution → evidence → grounded answer plus live Tools & Skills states. Claude traces real production paths; mocks alone are insufficient.

## 7. Risks and release conditions

- **Real seams, not just adapters:** Gmail-specific dispatch/grant aliases and unbound gate checker must be generalized once and regression-proven; registration-only completion prohibited.
- **Host trust:** manual review is required; local processes are not sandboxed against malicious packages. Scope initial profiles to public read-only actions and refuse profiles needing ambient cross-user secrets.
- **Upstream drift:** pin exact reviewed source and dependencies; current main/version observations are not a security approval. Health probes are per-action, not a blanket product badge.
- **Asynchronous cost/duplicates:** persist job IDs and completion; unknown outcome prevents automatic resubmission. Budget and data-destination scope must cover alternate tools.
- **Evidence quality:** zero output versus failure, flattened PDF versus real page numbers, caption timing/duplication, truncation and publication dates remain explicit.
- **UI/state regression:** resource fetch failures must not look like empty lists; shared composer drafts/session IDs must survive navigation to Tools & Skills. Reuse Hybrid R1/R2 acceptance principles.
- **Availability prerequisites:** manually reviewed install pin, Agent Reach/yt-dlp/JS runtime on target Windows host, Firecrawl account/key/budget, reachable real fixtures. These block live validation, not preparation of this plan.

Completion requires all ten proofs, no new unresolved regression, Claude pre-final audit → User live acceptance → Codex repair if needed → Claude final audit. Source qualification, Stage 1 freeze and implementation authorization remain outstanding. No installation or production work is authorized by the existence of these documents.
