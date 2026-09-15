# URI Native Tool Capability Audit — Outcome-Level Verification

**Auditor:** Claude (architect/pre-audit authority, AO-4 standing role).
**Scope:** every registered native capability in `uri_workspace/capabilities_registry.json`, audited against the acceptance principle below — not against whether a call merely returns `status: success`.
**Status:** AUDIT ONLY. No repair implemented in this pass, per instruction. UI milestone work remains paused/held, not resumed.

> **Acceptance principle (given verbatim):** A tool is not working merely because it returned SUCCESS. It is working only when the requested user outcome is actually achieved.

---

## 1. Acceptance Criteria for This Audit

1. Every claim is checked against real source and, wherever feasible, a real live `/ask` call against the actual running backend + real `gemma4:12b` + real Tavily API — not inferred from a tool's own docstring alone.
2. Each of the 6 User-flagged areas gets a real end-to-end trace: request → Brain decision → capability → execution → evidence/result → next capability if required → final answer.
3. Every registered capability in the registry gets a classification, not only the 6 flagged ones.
4. A defect is labeled by its real category (tool / orchestration / result-status / missing-downstream-continuation / evidence-provenance) — never lumped together.
5. Root causes are traced to the actual shared code responsible, not restated per-symptom, when multiple flagged items share one cause.

## 2. Headline Finding: Two Root Causes Explain Five of the Six Flagged Areas

### Root Cause A — `document_composition` role is not covered by the Active Brain override, and its hardcoded default model is not installed

`model_roles.py` defines `ROLE_DOCUMENT_COMPOSITION = "document_composition"`, defaulting to `{"provider": "ollama"}` with no model override — which resolves through `ModelProviderConfig.from_env()` to `DEFAULT_OLLAMA_MODEL = "qwen3:14b"` (`model_providers/base.py:74`). The per-user Active Brain override (`apply_active_brain_override`) only ever applies to `ROLE_SEMANTIC_INTERPRETATION`, `ROLE_REASONING`, and `ROLE_DRAFTING` — **`document_composition` was never included**. `qwen3:14b` is not installed on this machine (confirmed live: `ollama /api/tags` lists only `gemma4:12b` and `qwen3.5:9b`).

Net effect, confirmed live: **every** document-composition call (`draft_institutional_note`, `draft_institutional_order`, `generate_document`, and `convert_document`'s optional edit step) always tries the uninstalled `qwen3:14b`, always fails, and always falls back to `DocumentComposer._fallback_document()` — a placeholder ("DRAFT (...)... unpolished draft prepared without the reasoning model") — **regardless of the user's configured Active Brain, and regardless of whether a perfectly good local model is installed and healthy.**

Compounding this: `DocumentComposer.compose()`'s own docstring states plainly — *"status is always 'success' (a document is always produced); detail explains a fallback."* The tool-level contract makes no distinction the caller can see without reading `composed_by`, which `institutional_drafting.py`'s own docstring admits **"existing consumers simply ignore."** `real_tool_status()` (the exact M19 mechanism built to catch a tool silently degrading under an outer "success") cannot catch this either — it reads `data.status`, which is hardcoded to `"success"` in both the Brain and fallback branches.

**Live reproduction:**
```
POST /ask "create a PowerPoint presentation about the water cycle with 3 slides"
→ execution: {"status": "success", "tool": "generate_document"}
→ response.composed_by: "fallback"
→ response.detail: "The reasoning model was unreachable... (All providers exhausted
   for role 'document_composition'. Chain attempted: ['ollama(unhealthy)'].)"
→ response.preview: "DRAFT (PRESENTATION)\n\nSubject: Create a PowerPoint presentation
   about the water cycle with 3 slides\n\ncreate a PowerPoint presentation about the
   water cycle with 3 slides\n\n[This is an unpolished draft prepared without the
   reasoning model; review and complete before use.]"
```
A real `.pptx` file was produced and stored — but its content is a single placeholder slide restating the request, not a water-cycle presentation. The user-visible `execution.status` never says anything but `success`.

This single root cause directly explains **item 2** (fallback not surfaced as degraded) and **item 4** (generated files not matching requested content) in full, and is one of the two reasons item 3's `convert_document` modification path is unreliable.

### Root Cause B — general-capability orchestration is single-tool-per-turn, and the one real multi-step mechanism is unreliable and boundary-blocked

Tracing the actual dispatch path (canonical execution is OFF in this deployment — `URI_ENABLE_DECISION_ENGINE_LIVE` is unset — so the **legacy** orchestrator is what's live):

- `WorkflowPlanner._create_steps()` always builds a fixed generic scaffold (`retrieve_evidence → identify_missing_information → prepare_decision_context → draft_output/prepare_output → review_result`). `retrieve_evidence` only reads **internal session memory/facts** — it never calls `web_search`, `gmail_search`, `drive_search`, or `fetch_url`.
- The **only** place any real capability gets selected is `CapabilityPlanner.plan()`, called exactly once (inside `draft_output`), and it picks exactly **one** `tool_name` — the single highest-scoring candidate. There is no concept of a plan/sequence in this path at all.
- `MultiActionDispatch` supports real chained steps (`execute_chain`) — but its registry is Gmail-only (`MultiActionCapabilityRegistry([GmailCapability()])`); it cannot chain `web_search`/`fetch_url`/`generate_document` together.
- A **third**, separate mechanism exists and is real: a **"model_reasoning"-sourced workflow**, where the Brain itself proposes a multi-step plan with `depends_on` edges across arbitrary registered capabilities. This is architecturally the right shape for item 6 — but it is (a) inconsistently triggered (an essentially identical compound request triggered the single-tool legacy path in one run and this real 3-step plan in another, non-deterministically), and (b) when it *does* trigger correctly, it runs into a hard wall: `fetch_url`'s own documented argument boundary — *"The URL must appear literally in the request text; the Brain cannot supply an arbitrary URL of its own choosing"* — correctly blocks the Brain from feeding it a URL that only exists in a **prior step's own tool-returned evidence** (i.e., a URL `web_search` just found), because the boundary check doesn't distinguish that from an arbitrary Brain-invented URL. The workflow then terminates as `failed`, and the user gets nothing — not even the research that did succeed.

**Live reproduction (two consecutive, near-identical requests, same session type, same account):**

Run 1 — `"research the current CEO of OpenAI on the web and then create a PowerPoint slide about it"`:
```
execution: {"status": "success", "tool": "generate_document"}
```
`web_search` was never called. The single-tool legacy planner picked `generate_document` directly and the Brain had to invent/recall the answer from its own training knowledge with **zero real research performed**, despite the user explicitly asking for web research — yet the narrative confidently states *"I have created the PowerPoint slide regarding the current CEO of OpenAI."*

Run 2 — same request text, fresh session:
```
execution.status: "failed"
workflow.source: "model_reasoning"
steps:
  1. research_ceo_details   [web_search]   → completed, 5 real results
  2. fetch_ceo_source_content [fetch_url]  → failed: "No URL was found in the
                                              request, so URI does not know
                                              what to fetch."
  3. create_presentation    [generate_document] → pending, never ran
response.message: "URI could not complete the Brain-composed workflow."
```
Here the Brain correctly planned research → read-source → create-slide, real web research actually ran — and the whole thing still ends in **total failure with no file produced at all**, a worse outcome than Run 1's fabricated one.

This directly explains **item 6** (multi-action execution does not reliably continue through the full goal), **item 1**'s second half (web_search never reads pages or continues into downstream work — because nothing routes it there reliably), and **item 5** (retrieval tools have no reliable path to feed a downstream capability within one turn; whether they run at all is inconsistent).

---

## 3. Per-Item Findings (the 6 flagged areas)

### 3.1 `web_search`

**Classification: PARTIAL.**

- Tool itself (`web_search.py`) does exactly what it honestly documents: one real Tavily call, returns title/url/content snippets, never fabricates. Confirmed live for a simple factual query (*"the current CEO of OpenAI"*) — real 5-result set, and the orchestrator's narrative-drafting step **does** synthesize the snippet content into a direct, correct answer ("The current CEO of OpenAI is Sam Altman.") — this part works.
- Never calls `fetch_url` to read a full source page — synthesis is snippet-only. For a request needing real page content (not just a search-result blurb), this is insufficient.
- Never "continues into downstream work" reliably — see Root Cause B. When it's part of a compound request, whether it even runs at all is inconsistent from one otherwise-identical request to the next.
- **Defect categories:** missing-downstream-continuation (primary); orchestration defect (selection inconsistency, Root Cause B).

### 3.2 `draft_institutional_note` / `draft_institutional_order`

**Classification: DEGRADED.**

- Both delegate to the exact same `institutional_drafting.py` → `DocumentComposer.compose()` path as `generate_document` — Root Cause A applies identically. Not separately live-forced-reproduced in this pass (would need a synthetic note/order request), but the shared code path is confirmed live-broken via `generate_document` above, and the "status always success" contract is confirmed by direct source read (`document_composer.py:88-92`, `institutional_drafting.py:196-202`).
- **Defect categories:** result/status defect (fallback reported as success) — this is the *exact* item 2 concern, confirmed at the shared root.

### 3.3 `convert_document`

**Classification: PARTIAL (honestly-disclosed capability gap) + DEGRADED (shared fallback defect on its optional edit path).**

- The core PDF→DOCX conversion is real text extraction (with OCR fallback) rendered into a real DOCX — and it is **honest** about its own limitation: the tool's own success message states verbatim *"this is a plain-text conversion — original layout, tables, and fonts from the PDF are not preserved."* This is not a hidden defect; it's a real, disclosed gap between what the tool does and what the User's stated expectation is (layout/style-preserving conversion). Rendering that fully would require a substantially different approach (a layout-aware converter, not text-extraction-and-rebuild) — a design decision for a follow-up plan, not a bug fix.
- Its optional `_apply_modification` step (when the user asks to also edit content during conversion) reuses `DocumentComposer.compose()` directly — inheriting Root Cause A. A requested edit can silently fail to apply for the same reason `generate_document`'s content silently degrades, though the tool's own `edited` flag and unedited-fallback path at least prevent losing the file entirely.
- **Defect categories:** evidence/provenance weakness relative to the stated user expectation (disclosed, not hidden); result/status defect on the edit sub-path (shared with 3.2/3.4).

### 3.4 `generate_document`

**Classification: DEGRADED.** Live-reproduced in full above (§2, Root Cause A). All four renderers (DOCX/XLSX/PPTX/PDF, in `office_document_writer.py`/`document_writer_service.py`) are real and reasonably well-designed — XLSX correctly parses markdown tables into real rows, PPTX correctly parses `# Slide Title` headings into real multi-slide decks, PDF paginates real text — **when the Brain actually composes matching content**. The defect is entirely upstream of rendering: with `document_composition` silently resolving to an uninstalled model, the renderers faithfully render a placeholder instead of real content, and report success throughout.
**Defect categories:** result/status defect (primary, shared root cause); not a rendering/tool defect.

### 3.5 Gmail / Drive / Files

**Classification: UNVERIFIED (live) for Gmail/Drive downstream chaining this pass; WORKING for the isolated read path per source inspection.**

- Could not live-test with a connected Gmail/Drive account from this audit session (the diagnostic account used for the other live tests has no Google connection; using the User's own connected `Uri_admin1` account for exploratory multi-step testing was avoided without explicit direction).
- By source inspection: `gmail_search`/`drive_search`/`gmail_find_draft` are honest, real, evidence-only reads (never fabricate), matching the same pattern already proven live for `web_search`.
- The **same Root Cause B applies structurally**: nothing guarantees a Gmail/Drive search's results reliably feed into a downstream drafting/creation step within one turn — it depends on the same inconsistent single-tool-vs-model-workflow selection already demonstrated live for web research.
- `gmail_create_draft` additionally composes its subject/body via the Brain — **need to verify which role it uses**; if it shares `document_composition`, it inherits Root Cause A too (not confirmed in this pass — flagged for the next audit round with a connected account).
- **Defect categories:** UNVERIFIED for the specific "downstream use" claim; orchestration defect suspected structurally (shared with 3.1/3.6).

### 3.6 Multi-action execution (research → analyze → create)

**Classification: BROKEN (unreliable) for the general case; WORKING for Gmail-only chains via `MultiActionDispatch`.**

Live-reproduced in full above (§2, Root Cause B, Run 1 vs Run 2). The system has three independent orchestration mechanisms with no clear, deterministic rule for which one a given compound request uses, and the one mechanism actually capable of the requested shape (model-authored multi-step workflow) hits a real architectural boundary (`fetch_url`'s literal-URL-in-request-text check) that blocks the single most common legitimate case: reading a page `web_search` just found.
**Defect categories:** orchestration defect (mechanism-selection non-determinism); tool/boundary defect (`fetch_url`'s argument boundary doesn't distinguish a prior-step's own trusted evidence from an arbitrary Brain-invented URL).

---

## 4. Full Registry Classification

| Capability | Classification | Basis |
|---|---|---|
| `web_search` | PARTIAL | Live-verified (§3.1) |
| `fetch_url` | PARTIAL | Works for its own documented scope (URL literal in user text); is the specific blocker in Root Cause B for the chained case |
| `draft_institutional_note` | DEGRADED | Shared root cause, source-confirmed (§3.2) |
| `draft_institutional_order` | DEGRADED | Shared root cause, source-confirmed (§3.2) |
| `generate_document` | DEGRADED | Live-reproduced (§3.4) |
| `convert_document` | PARTIAL | Honestly-disclosed layout gap; DEGRADED on optional edit path (§3.3) |
| `gmail_search` | UNVERIFIED | No connected test account this pass; sound by inspection |
| `gmail_find_draft` | UNVERIFIED | Same as above |
| `gmail_create_draft` | UNVERIFIED | Same as above; composition role not yet confirmed |
| `drive_search` | UNVERIFIED | Same as above |
| `drive_upload` | UNVERIFIED | Same as above |
| `extract_student_records` | WORKING | Self-contained, honest not-found reporting; not implicated by any flagged item |
| `fetch_drive_spreadsheet` | UNVERIFIED | Registry reports `unavailable_missing_dependency`; not tested |
| `system_performance` | WORKING | Live-confirmed all session (real CPU/RAM/disk on the dashboard) |
| `remember_fact` | WORKING | Approval-gated, consent-scoped; exercised and audited in prior milestones (M30-PFC) |
| `recall_memory` | WORKING | Read-only, honest-empty by design; not implicated |
| `read_attached_file` | WORKING | Self-contained, honest-failure by design; not implicated |
| `pc_system_optimization` | N/A (planned, not implemented) | Registry itself discloses this honestly |

**Note on the registry's own `availability` field:** several entries (`gmail_search`, `gmail_find_draft`, `fetch_drive_spreadsheet`) are statically marked `unavailable_missing_dependency` in `capabilities_registry.json`, yet the live dashboard shows Gmail genuinely `Connected` for the real account. This mirrors the exact static-catalogue-vs-real-state issue found and fixed for the Ollama model list earlier in this project (Batch 3) — the registry's `availability` field is a deployment-wide default description, not a live per-user check, and should not be trusted as current status without live verification. Flagged as an evidence-provenance weakness in its own right, not yet corrected in this pass.

---

## 5. Defect Summary by Category

- **Result/status defect:** `document_composition`'s hardcoded "status always success" contract (§2 Root Cause A) — affects `draft_institutional_note`, `draft_institutional_order`, `generate_document`, and `convert_document`'s edit path.
- **Orchestration defect:** single-tool-per-turn legacy planning + non-deterministic selection against the separate model-authored multi-step mechanism (§2 Root Cause B) — affects `web_search`, Gmail/Drive downstream use, and general multi-action requests.
- **Tool/boundary defect:** `fetch_url`'s literal-URL-in-request-text check doesn't distinguish a prior-step's trusted tool evidence from an arbitrary Brain-invented URL — blocks the one chain the User specifically wants.
- **Missing downstream continuation:** confirmed structurally for every evidence-gathering tool (`web_search`, `gmail_search`, `drive_search`, `fetch_url`) — none reliably feeds a subsequent capability within one turn.
- **Evidence/provenance weakness:** the registry's static `availability` field does not reflect live per-user connection state (§4 note).

## 6. What Was Not Done in This Pass (by instruction)

No repair was implemented. No new external skill integration was started. No UI work resumed. No commit/push performed. Gmail/Drive live chaining and `gmail_create_draft`'s composition role remain UNVERIFIED pending a connected test account or explicit direction to use the live account.

## 7. Suggested Next Step (for User decision, not started)

Root Cause A (§2) is narrow and high-value: add `document_composition` to `ACTIVE_BRAIN_OVERRIDE_ROLES`, and make `DocumentComposer.compose()`/`real_tool_status()`-visible status actually distinguish a fallback from a Brain-authored success rather than reporting both as `"success"`. Root Cause B is larger and needs a scoping decision (which of the three orchestration mechanisms should own general multi-step requests, and how `fetch_url`'s boundary should recognize same-workflow trusted evidence) before any implementation starts.
