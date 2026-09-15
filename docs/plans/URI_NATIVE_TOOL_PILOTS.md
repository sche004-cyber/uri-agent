# URI Native Tool Pilots — Connecting the Audit to Real Repairs

**Authority:** Claude implemented directly in this session (no separate Codex session was reachable as a tool from here; this is the same standing exception already used and disclosed earlier in this project — e.g. M30-PFC, "Claude root-cause audit → bounded Codex implementation if needed" collapses to Claude alone when Codex cannot be invoked). Each pilot below still follows the required method: inspect → define bounded repair → implement → independently re-inspect source → execute a real scenario → inspect the actual artifact → audit goal achievement → bounded repair if still needed.
**Baseline:** `docs/plans/URI_NATIVE_TOOL_AUDIT.md`.
**Standing constraints honored:** UI work not resumed; Gmail/Drive not touched; no external skill integration started; scope held to the 3 named pilots; no commit/push.

---

## PILOT 1 — `generate_document` (Root Cause A + completion semantics)

### Inspection

Confirmed by direct source read (already the audit's own finding, re-verified here before touching anything): `document_composition` was one of the four original M21 call sites (`model_roles.py`'s own module docstring names it explicitly) but was never added to `ACTIVE_BRAIN_OVERRIDE_ROLES` when `semantic_interpretation` joined that tuple in an earlier repair this session — a scope oversight, not a deliberate design choice. Its default model (`qwen3:14b`, hardcoded in `model_providers/base.py`) is not installed on this machine. `principal` is already correctly threaded from `generate_document.py`/`draft_institutional_note.py`/`draft_institutional_order.py` through to `DocumentComposer.compose(principal=...)` — the ONLY missing piece was the override-eligibility check itself.

**Decision: no parallel architecture.** The existing `apply_active_brain_override()` mechanism (used by `ModelRouter` for the other three roles) is extended by exactly one tuple entry. No second override path, no new state, no new store.

### Bounded repair (implemented, then independently re-verified)

1. **`model_roles.py`** — added `ROLE_DOCUMENT_COMPOSITION` to `ACTIVE_BRAIN_OVERRIDE_ROLES`, with the reasoning recorded inline.
2. **`document_composer.py`** — `compose()`'s fallback branches now return `"status": "degraded"` instead of a hardcoded `"success"`. `composed_by`/`detail` unchanged (they already existed; the bug was that the outer `status` field never reflected them).
3. **`institutional_drafting.py`** / **`generate_document.py`** — both now propagate `result["status"]` from the composer instead of re-hardcoding `"success"`.
4. **`workflow_capability_router.py`**'s `draft_output()` — now treats `real_tool_status(result) in ("success", "degraded")` as a real completion (was: `== "success"` only), so a degraded-but-real artifact is no longer discarded as a hard failure and its honest status is preserved rather than forced back to `"success"`.
5. **`workflow_executor.py`** — the per-step completion check (`§313`) now accepts `"degraded"` alongside `"success"` (a brand-new status value no pre-existing step handler returns, so this cannot change behavior for any of the other 15 tools' shared use of this engine). `_complete_workflow()` now inspects all steps' own output status and reports the overall workflow result as `"degraded"` if any step degraded, instead of unconditionally `"success"`.
6. **`orchestrator.py`** — the Brain-proposed-workflow response builder (`_execute_brain_proposal`) now handles `"degraded"` as a real completion (distinct, honest user-facing message: *"...but at least one step fell back to a plain result instead of a Brain-authored one - review before relying on it."*), and the iterative re-evaluation loop's `_clear_active_workflow` call now fires on `"degraded"` too (previously only `"success"` — a degraded-but-finished workflow would otherwise have stayed marked "active" indefinitely).
7. **`generate_document.py`**'s own, separate, real defect found during live testing: `_FORMAT_KEYWORDS`'s `pptx` entry never matched the literal words "ppt" or "slide" (singular) — the exact words the User's own acceptance phrase uses (*"Create a 3-slide water cycle PPT"*). Added `"ppt"` and `"slide"` to the keyword list.

All of this reuses the **existing** `real_tool_status()` mechanism (M19) end-to-end — a tool that honestly reports its own `"degraded"` status now automatically propagates through every layer that already existed to catch exactly this class of problem; no new status-propagation machinery was built.

### Verification

- `pytest test_m22_6_institutional_drafting_principal_threading.py test_model_router_auth_failure_boundary.py test_model_router_budget_seam.py test_model_router_degraded_mode.py test_model_router_freshness.py test_model_router_import_boundary.py test_model_router_resolution.py test_workflow_capability_router.py test_workflow_executor.py test_capability_planner.py test_m19_office_readiness.py` — **109/109 passed** (2 pre-existing tests updated in place — they asserted the old, now-deliberately-changed "always success" behavior; both now assert the correct `"degraded"` status, matching the audit's own stated defect).

### Real acceptance scenario: *"Create a 3-slide water cycle PPT."*

Live `/ask` against the real backend, real `gemma4:12b` as the account's configured Active Brain:

```
execution: {"status": "success", "tool": "generate_document"}
response.status: "success"       response.composed_by: "brain"
response.output_format: "pptx"   response.file: {filename: "...pptx", size_bytes: 30365}
```

**The artifact was downloaded and physically opened with `python-pptx`** (not just trusted from the response envelope):

```
REAL slide count: 3
Slide 1: The Water Cycle Overview — 4 real bullets (definition, movement, key
  processes, sun as energy source)
Slide 2: Key Processes of the Hydrological Cycle — 4 real bullets (evaporation,
  transpiration, condensation, precipitation)
Slide 3: Collection and Distribution — 4 real bullets (runoff, infiltration,
  groundwater flow, collection)
```

Every acceptance point holds: meaningful, topically-correct content; exactly the requested slide count; a real, editable `.pptx` (confirmed by successfully parsing it, not just its byte size); `gemma4:12b` demonstrably composed it (`composed_by: "brain"`, and content quality is well beyond template text); the file exists and opens; the reported status is genuinely earned, not asserted.

The fallback-must-be-honest half of the requirement is covered by the two corrected unit tests above (`test_model_router_degraded_mode.py`, `test_m19_office_readiness.py`), which force a real `AllProvidersUnreachableError`/unreachable-provider condition and assert `"degraded"` — forcing a live Ollama outage against this same diagnostic session was avoided as unnecessarily disruptive given the mechanism is now directly unit-verified at its exact failure point.

### Pilot 1 verdict: **RESOLVED.**

---

## PILOT 2 — `web_search` + `fetch_url` (Root Cause B, trusted evidence, continuation)

### Inspection

Confirmed (audit + re-verified here) that a real, general-purpose multi-step orchestration mechanism already exists: `orchestrator.py`'s `_build_model_workflow`/`_create_workflow_executor`/`_model_workflow_step_handler` lets the Brain propose an arbitrary sequence of registered capabilities with `depends_on` edges, executed one at a time through the same `ApprovalGate.execute_tool()` boundary every other path already uses. **No second workflow engine was needed or built.** The actual defect was narrow: every step's tool call received `request_text = goal` — the ORIGINAL user text, unconditionally, for every step — so a `fetch_url` step downstream of a `web_search` step had no way to receive the URL `web_search` had just found, and `fetch_url`'s own argument boundary (URL must appear literally in `request_text`) correctly, safely refused to invent one.

**Decision: extend, don't weaken.** `fetch_url.py` was not touched. The fix lives entirely in how the ORCHESTRATOR builds a step's `request_text` — the runtime, never the Brain, decides what a step's literal text contains, sourced only from a step this exact workflow run already executed and that the consuming step explicitly `depends_on`.

### Bounded repair (implemented, then independently re-verified)

`orchestrator.py`:
- `_URL_CONSUMING_CAPABILITIES` — the (currently one-member) set of capabilities whose own security boundary needs a literal URL.
- `_extract_trusted_url_from_step_output()` — recognizes the two real evidence shapes `web_search`/`fetch_url`/`drive_search` actually return (`{"url": ...}` and `{"results": [{"url": ...}]}`); prefers a non-PDF result when one exists among the search results (a large institutional PDF is real evidence but often exceeds `fetch_url`'s own 10 MB bound — this is source *selection*, never source *invention*: it only ever returns a URL the tool itself already returned).
- `_resolve_step_request_text()` — for a `depends_on`-linked, already-*completed* prior step only, builds `request_text = f"{goal}\n\nSource URL to fetch: {url}"` and stamps `step["evidence_provenance"] = {"source_step", "source_capability", "value_type", "value", "trust": "runtime_verified_same_workflow"}` onto the consuming step — real, inspectable state (reusing `workflow["steps"]`, not a new store), not an invisible side effect.
- `_model_workflow_step_handler`'s `_handler` now calls `_resolve_step_request_text()` instead of always using the bare `goal`.

**Loop ownership (evaluated from real implementation evidence, not assumed in advance):** the existing shape is already the hybrid the task asked to consider — the Brain proposes what to do next (`_continue_brain_evaluation_loop`, `_execute_brain_proposal`), but the RUNTIME owns the trusted state a step actually receives (this pilot's own fix), the deterministic gates (`ApprovalGate`, capability-registry validation), and now the inter-step evidence-passing that lets continuation actually work end to end. No second decision authority was introduced; the existing loop was completed, not replaced.

### Verification

- Targeted suite (`test_multi_action_capabilities.py`, all `test_orchestrator_model_driven_*`/`test_orchestrator_workflow*`/`test_orchestrator_session_workflow.py`/`test_orchestrator_brain_reevaluation.py`): **57 passed, 1 pre-existing failure** (`test_session_facts_are_used_for_clarification` — independently reproduced to fail identically and instantly with `interpretation_unreachable: true`; root-caused directly to this test calling `process_user_input` with no `principal`, so no Active Brain override applies and semantic interpretation/reasoning fall back to the deployment default `qwen3:14b`, not installed on this machine — the same previously-documented "User removed `qwen3:14b` mid-audit" environment change from before this session, unrelated to anything touched by either pilot). One other test (`test_query_context_key_present_with_deduplicated_sections`) needed its call-count assertion updated from 1→2: a degraded document composition now correctly triggers a second Brain re-evaluation call, a deliberate, correct consequence of Pilot 1's honest-status fix, not a defect.

### Real acceptance scenario: *"Research Student Welfare activities from the NIT Sikkim website and create a short PPT."*

Live `/ask`, real Tavily search, real page fetch, real `gemma4:12b`:

```
Step 1: find_nit_sikkim_pages [web_search]  → completed, 5 real results
         (including NIT Sikkim's real Annual Report PDF with genuine
         "Student Welfare Initiatives" content)
Step 2: fetch_relevant_content [fetch_url]  → completed
         evidence_provenance: {source_step: "find_nit_sikkim_pages",
           source_capability: "web_search", value_type: "url",
           value: "https://nitsikkim.ac.in",
           trust: "runtime_verified_same_workflow"}
Step 3: create_ppt [generate_document]      → completed, composed_by: "brain"

execution.status: "success"   response.message: "URI completed the Brain-composed workflow."
```

**Artifact physically downloaded and opened with `python-pptx`:** a real, valid 6-slide deck ("Student Welfare Activities at NIT Sikkim", "Institutional Support Framework", "Campus Life and Amenities", "Health and Wellness", "Student Engagement Initiatives", "Summary of Welfare Objectives").

**The negative requirement was also verified, live, not assumed:** the first attempt at this exact scenario picked the Annual Report PDF as the source, which exceeded `fetch_url`'s own 10 MB bound; `create_ppt` (correctly `depends_on: ["fetch_welfare_page"]`) never ran, and the workflow honestly reported `"URI could not complete the Brain-composed workflow"` rather than fabricating a presentation from unresearched content. The source-selection improvement above (prefer a non-PDF result) was added specifically because of this live observation, and the retry then completed all three steps for real.

**Disclosed, honest limitation:** the page `fetch_url` actually retrieved this run was NIT Sikkim's homepage — mostly navigation text ("Jobs / Tenders / Administration / Deans / HODs...") rather than deep Student Welfare detail (that detail lives in the large PDF the size bound correctly excludes). The generated slides are topically correct and well-structured, but are not densely citation-grounded in specific facts from the fetched page the way a richer source would allow — the *mechanism* (search → trusted fetch → synthesize → generate, with no fabrication on failure) is proven working end to end; the *depth* of evidence-grounding is bounded by which single page gets selected and by `fetch_url`'s own 8000-character extraction cap. A smarter source-ranking pass (e.g. preferring a specific sub-page over a homepage, or fetching more than one source) is a natural next increment, not implemented in this bounded pilot.

### Pilot 2 verdict: **RESOLVED** (core mechanism); **evidence-depth quality is a disclosed follow-up, not a defect in this pilot's own scope**.

---

## PILOT 3 — `convert_document` (artifact fidelity + structural evidence)

### Inspection

Confirmed by direct source read: `convert_document.py`'s PDF→DOCX path was plain-text-extraction-and-rebuild only (`PDFReader` → `DocumentWriterService.render_docx_bytes(text)`), honestly disclosed as such in its own response message, but a real capability gap against what "convert this to Word" actually means to a user — page layout, tables, fonts, images, and spacing were discarded entirely, every time, not only on failure. No layout-preserving path existed anywhere in the codebase. `pdf2docx` (real, purpose-built, MIT-licensed) was not installed.

**Decision: no parallel architecture.** The existing `ConvertDocumentTool.convert()` control flow (attachment lookup → format detection → conversion → `FileStore.save()`) is kept exactly as-is; a new PRIMARY path is inserted ahead of the existing plain-text path, which becomes an honest FALLBACK rather than being replaced. The existing `status`/`FileStore` contract (`real_tool_status()`, containment-checked storage, `to_reference()`) is reused unchanged.

### Bounded repair (implemented, then independently re-verified)

1. **Installed `pdf2docx`** (pulled in `PyMuPDF`, `python-docx`, `fonttools`, `numpy`, `opencv-python-headless` as real dependencies — no fake/stub layer).
2. **New file `uri_core/services/pdf_layout_converter.py`** — a thin, honest wrapper: `convert_pdf_to_docx_preserving_layout(pdf_path, docx_path)` returns `{"status": "success", "docx_path", "preserved": [...], "not_preserved": [...]}` on a real conversion, or `{"status": "error", "message", "error"}` on genuine failure — never raises, never fakes success, matches every other tool's honesty discipline in this codebase.
3. **`convert_document.py` restructured**: for an ordinary (non-edit) "convert this to Word" request, the layout-preserving path now runs FIRST. On success: `status: "success"`, `layout_preserved: true`, and the real `preserved`/`not_preserved` lists are surfaced to the user rather than asserted blindly. On genuine failure, or when the user also asked for a content edit (a text-level operation the reconstructed layout cannot accommodate), it falls through to the existing plain-text path — now honestly reported as `status: "degraded"` (was unconditionally `"success"` before this pilot, the same class of defect Pilot 1 fixed for `document_composer.py`), with a message naming the specific reason (layout failure vs. edit-required) rather than a generic disclaimer.
4. No changes were needed to `fetch_url`, `workflow_executor.py`, or `orchestrator.py` for this pilot — `convert_document` is a single, non-multi-step capability; the `"degraded"` status value it now emits already propagates correctly through `real_tool_status()` end to end because Pilot 1 already taught every consuming layer about that status value.

### Verification

- `test_convert_document.py` — rewritten to match the new two-path contract: the old single "successful conversion" test (which mocked `PDFReader`/`DocumentWriterService` but not the new layout converter, so it exercised the fallback path while asserting the OLD unconditional `"success"`) was split into `test_layout_preserving_conversion_is_the_real_success_path` (mocks the layout converter to succeed; asserts `status: "success"`, `layout_preserved: True`) and `test_plain_text_fallback_is_honestly_degraded_not_success` (mocks the layout converter to fail; asserts `status: "degraded"`, `layout_preserved: False`) — both real, distinct paths now have their own test rather than one test ambiguously covering both. The two existing modification-path tests (which always exercise the plain-text path, since edits are incompatible with layout reconstruction) had their status assertions corrected `"success"` → `"degraded"`, the identical pattern already applied twice in Pilot 1. **8/8 passed.**
- Regression: `test_canonical_execution.py` + `test_orchestrator_top_level_error_surfacing.py` (the only other test files referencing `convert_document`/`ConvertDocumentTool`) — **46 passed, 13 subtests passed**, no regressions.

### Real acceptance scenario

A real PDF was generated (via `PyMuPDF`, since no sample PDF was available in the repo) containing a heading, a wrapped body paragraph, and a 4×3 shaded table — deliberately exercising all three structural categories the User's acceptance criteria named (paragraph hierarchy, fonts/spacing, tables/shading). `convert_pdf_to_docx_preserving_layout()` was called directly against this real file (not mocked):

```
[INFO] Start to convert ...quarterly_report.pdf
{'status': 'success', 'docx_path': '...quarterly_report.docx',
 'preserved': ['page size/orientation', 'margins', 'paragraph structure',
   'fonts and styles', 'spacing/alignment', 'tables', 'images'], ...}
```

**The generated `.docx` was physically opened with `python-docx`** (not trusted from the return value alone):

```
Paragraph "Quarterly Report" — run font size 304800 EMU (24pt, matches source heading)
Paragraph body text — run font size 152400 EMU (12pt, matches source body), full text intact
Table: 1 real table, 4 rows x 3 columns, cell text exactly matching source
  (Region/Revenue/Growth header row + North/South/East data rows)
Page size: 7772400 x 10058400 EMU = 8.5in x 11in (US Letter, matches source)
```

**Visual comparison was performed for real, not skipped as unverifiable**: the source PDF's page was rendered to PNG directly (`PyMuPDF`); the generated `.docx` was then round-tripped back to PDF using a genuinely available renderer on this machine (Microsoft Word via COM automation, `docx2pdf`) and rendered to PNG the same way. Both images were visually inspected side by side: heading position/size, paragraph wrapping, table position/column widths/header shading, and cell text all match the source. The one visible difference is cosmetic, not a fidelity loss — Word's default table style renders a slightly heavier outer border than the source PDF's thin hand-drawn grid lines; the actual table dimensions, shading, and every cell's text are identical.

Every acceptance point holds: layout (headings, paragraph structure, tables with shading, page size) is genuinely reconstructed, not just extracted text; the output is a real, editable `.docx` (edited and re-verified via `python-docx`, and independently opened/rendered by real Microsoft Word); the honest fallback path is now correctly `"degraded"`, never silently `"success"`; the source PDF and generated DOCX were compared visually, per the User's explicit requirement, and matched.

**Disclosed, honest limitation** (already stated by `pdf_layout_converter.py` itself, not newly discovered): scanned/image-only PDF pages have no extractable text layout for `pdf2docx` to reconstruct and will come through empty on the layout path — such pages correctly fall through to the honest `"degraded"` plain-text path only if `PDFReader`'s own OCR/extraction succeeds; a PDF that is both layout-unreconstructable AND text-unextractable (e.g. a pure image scan with no OCR layer at all) will honestly report `status: "error"`, never fabricate content. This was not separately live-tested this pilot (it is the pre-existing, already-covered `test_extraction_failure_is_reported_not_raised` path), since the acceptance scenario's own PDF has a real text/graphics layer by construction.

### Pilot 3 verdict: **RESOLVED.**

---

## Cross-Cutting Contract Status

All three pilots converged on the same small set of real, load-bearing patterns — extracted here only because they were actually proven working, not designed abstractly in advance:

1. **Canonical model authority.** `ACTIVE_BRAIN_OVERRIDE_ROLES` (in `model_roles.py`) is the single place a role becomes eligible for the User's configured Active Brain to override the provider default. Pilot 1 proved the fix pattern for a role that was mistakenly left out (`document_composition`): add exactly one tuple entry, change nothing else. This is the correct, minimal migration path for any of the remaining 13 tools found to have the same defect — never a second override mechanism, never a per-tool special case.

2. **Honest three-part status, not a single `success`/`failure` flag.** Every pilot needed to distinguish TOOL EXECUTION (did it run), OUTPUT QUALITY (`success`/`degraded`/`error`/`input_required`/`not_implemented`), and USER GOAL completion (did the multi-step request actually finish). The existing `real_tool_status()` mechanism (M19) already generalizes this correctly across every consumer — a tool need only start honestly returning `data.status`, and the dispatcher, `workflow_capability_router.py`, `workflow_executor.py`, and `orchestrator.py`'s re-evaluation loop all already know how to propagate it, once (as this pilot phase did three times) they are taught that `"degraded"` is a real, non-terminal-failure value alongside `"success"`. This is the single highest-leverage pattern to carry forward: any of the remaining tools that currently hardcode `"status": "success"` on a fallback/partial path can adopt it with a small, local, low-risk change.

3. **Trusted inter-step evidence via `depends_on` + `evidence_provenance`, never a model-supplied literal for a security-sensitive argument.** Pilot 2's fix — the runtime (never the Brain) resolves a completed prior step's real output into a literal value for a dependent step, stamping an inspectable provenance record — is the correct shape for any future tool chain that needs to pass a value across a trust boundary (e.g. a file path, an account identifier, a search result ID). `fetch_url.py`'s own literal-URL boundary was never weakened; the fix worked entirely on the orchestrator side.

4. **Physically inspect the artifact, never trust the response envelope alone.** All three pilots' real acceptance evidence came from opening the actual generated file with the right library (`python-pptx`, `python-docx`, and — for Pilot 3's visual check — rendering both the source and the reconstructed document to images and comparing them) rather than from the tool's own reported `status`/`message`. This should be the standing acceptance bar for any future tool audit in this project, not a one-off used for these three pilots.

5. **No competing workflow engine; the hybrid loop-ownership shape was already correct.** Pilot 2 confirmed from real implementation evidence (not assumed) that `orchestrator.py`'s existing Brain-proposes/runtime-executes loop (`_build_model_workflow`/`_model_workflow_step_handler`/`ApprovalGate`) is the one and only multi-step mechanism; the actual defect was a missing piece of trusted state inside it (pattern 3 above), not a structural flaw in who owns continuation. Any future multi-step tool work should extend this same loop, never introduce a second one.

### Recommended migration path for the remaining 13 native tools

Not touched by these 3 pilots and not re-audited here beyond the original `URI_NATIVE_TOOL_AUDIT.md` classification: `web_search` (as a standalone capability outside the Pilot-2 chain), `draft_institutional_note`, `draft_institutional_order` (both already share `document_composer.py`/`institutional_drafting.py`, so they inherited Pilot 1's status-honesty fix automatically — no separate work needed, only re-verification), Gmail, Drive, and the remaining registry entries marked PARTIAL/DEGRADED/UNVERIFIED in the original audit.

For each: (a) check whether it hardcodes `"status": "success"` on any fallback/partial/best-effort path — if so, apply pattern 2 directly; (b) check whether its default model role is present in `ACTIVE_BRAIN_OVERRIDE_ROLES` — if the tool is meant to honor the User's Active Brain and isn't listed, apply pattern 1; (c) if the tool can meaningfully participate in a multi-step request (e.g. Drive/Gmail retrieval feeding a downstream drafting step), verify it already flows through the existing `_build_model_workflow` loop rather than terminating the turn on its own — if a trust-sensitive value needs to cross from one step to another, apply pattern 3, never invent a second passing mechanism; (d) for any tool producing a real artifact (file, document, structured record), require live acceptance evidence that physically opens/inspects that artifact (pattern 4) before declaring it WORKING. Gmail/Drive repair itself remains explicitly out of scope per the User's own standing instruction and stays classified UNVERIFIED until a dedicated pass is authorized.
