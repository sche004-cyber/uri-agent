# URI Hybrid UI — Batch 2 Implementation Report

**Initiative:** URI Hybrid UI Implementation
**Governing Blueprint:** `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`
**Batch:** Batch 2 — Standalone Chat, actions, Tasks
**Implementer this batch:** Claude (see §0 — explicit, scoped role divergence, User-directed)
**Reviewer:** not yet run (see §7)

---

## 0. Role divergence from the Frozen Blueprint (disclosed, not silent)

The Frozen Blueprint's §1 assigns this initiative to Antigravity (primary implementer), Qwen (review), and states three times over that "Claude and Codex... neither writes UI or reconciled-backend production code for this initiative" and "no step in this loop is performed by Claude or Codex."

This batch was implemented by Claude directly, under an explicit, detailed, current-session User instruction that authorized Claude to review Batch 1, and — on acceptance — implement Batch 2 itself, stopping before Batch 3. The instruction was specific enough (exact acceptance/rejection verdicts, exact fix/report/stop conditions, explicit "You are authorized to use normal local development actions... including repository reads, file edits within scope, tests") to read as a deliberate, bounded exception rather than an oversight of the frozen role table. It is scoped to this batch only — the instruction explicitly says stop before Batch 3 — so it is **not** treated as a standing revision of the Hybrid UI role table, and Antigravity/Qwen's roles resume unchanged for Batch 3 unless the User says otherwise. This divergence and its scope are recorded here per the repository's auditable-correction-history convention, not silently substituted.

---

## 1. Batch 1 Review Verdict — BATCH_1_ACCEPTED

Independently re-verified from source rather than trusted from `docs/plans/UI_HYBRID_BATCH_1_REPORT.md`'s claims:

| Claim | Independent verification |
|---|---|
| `flutter analyze`: 0 errors, 0 warnings, 1 pre-existing info | Re-ran fresh: identical result (`providers_screen.dart:697:5`) |
| `flutter test` on the 5 Batch 1 targeted suites: 53/53 | Re-ran fresh: 53/53 (identical) |
| Python non-regression, `test_m31_model_brain_ux.py` + `test_security_boundary.py`: 33/33 | Re-ran fresh: 33/33 in 17.31s |
| Exactly 4 Home tiles, no "Upcoming Deadline"/"Halted Workflows" | Confirmed by direct grep of `home_screen.dart` — exactly the 4 required labels present, neither forbidden label present |
| 5-destination sidebar, correct order and labels, Chat at index 1 | Confirmed by direct read of `app.dart`/`app_shell.dart` — Home, Chat, Tasks, Connections & Providers, Settings, in order |
| R1 (tri-state fetch failures, no false "0"/`[]`) | Confirmed: `listTasks()` throws `TasksFetchException` on network/status/parse failure; no `return [];` anywhere in `http_uri_client.dart` |
| M31 gate satisfied before Batch 1 started | Confirmed: `git log` shows `5c31d25 M31 COMPLETE: Model & Brain UX, Claude VERIFIED and released` as the base commit, matching the report's stated baseline |

**No fixes were required.** Verdict: **BATCH_1_ACCEPTED**, proceeding directly into Batch 2 per this turn's authorization.

---

## 2. Batch 2 Implementation Summary

Scope per Blueprint §6 Batch 2: standalone Chat (§4.3, including the mandatory M31 model-selector reconciliation, §7), Tasks (§4.5), Suggested-Actions wiring (§4.2/§5).

### 2.1 Model-selector reconciliation (§7) — real shipped structure differs from the blueprint's assumption, as §7 itself anticipated

§7 assumed M31 shipped separate `ModelSelectorChip`/`ChooseModelPopover` components. The actual shipped structure (verified by direct read) is a private `_ModelSelectorChip` class inside `ask_uri_screen.dart`, built on `PopupMenuButton`/`RawChip`, with the "Conversation model: <model>" caption rendered on `TurnCard` rather than as a separate composer caption. This is exactly the "genuinely missing/changed contract" case §5/§7 tell implementation to record rather than improvise around — recorded here, not worked around silently.

The real state/logic layer §7 cares about was already present and correct: real discovered/verified provider inventory (`providers` from `AppState.providerInventory`), unverified entries disabled with a red/teal dot indicator and a "Not verified"/provider-name detail, `URI Auto` as a real routed entry, per-conversation override via the existing `onChooseModel`/`AskRequest.model_override` plumbing (untouched), and the persisted caption on `TurnCard` (untouched). Per §7's instruction to restyle only presentation: added a trailing chevron (`Icons.expand_more_rounded`) so the trigger reads as "label + chevron" per the reference spec, and kept the icon **position** (already correctly between attachment and mic/send) and the `RawChip`-not-`Chip` distinction that `attachment_ui_test.dart` depends on as a regression guard.

### 2.2 Chat (§4.3)

- `AskUriScreen` converted from a plain `Column` to a three-tab surface (`Conversation` / `History` / `Activity`), reusing `HistoryScreen` and `ActivityScreen` as-is per COMPONENT_MAPPING.md's "Internal history/activity views" row (not a new top-level destination — `ShellIndex` still has only 5 entries).
- `HistoryScreen` gained an optional `onResumed` callback so resuming a conversation from inside Chat's History tab switches back to the Conversation tab in place, rather than navigating away via the shell (its previous behavior navigated to `ShellIndex.home`, which — after Batch 1 retired Home's embedded conversation — would have landed the user on a screen with no transcript at all; this was a latent Batch 1 collateral gap, fixed here). Standalone use of `HistoryScreen` (if any future caller needs it) still falls back to shell navigation, now correctly targeting `ShellIndex.chat` instead of the now-conversation-less `ShellIndex.home`.
- Per-message Copy action added to `TurnCard` (`_CopyMessageAction`), copying the user's prompt plus whatever reply content the turn actually has (understanding, result summary/detail, draft) — never a placeholder. Clipboard-failure-safe: the transient "Copied" state is only set after `Clipboard.setData` resolves without throwing; a failure leaves the icon unchanged.
- Empty-state copy and composer hint text updated to match the reference ("New conversation" / "Ask URI anything to begin." split across `EmptyState`'s existing title/message fields rather than as one literal dash-joined string — a deliberate reuse-the-existing-component decision, not a literal transcription; disclosed here per the same principle as the model-selector reconciliation). Hint text: `Message URI…`.
- Composer icon row order was already correct (attachment → model selector → mic → send) from Batch 1; no restructuring needed. The blueprint explicitly permits the single-row arrangement already in place ("either arrangement satisfies the authority's ordering requirement").

### 2.3 Tasks (§4.5) — full rebuild

Replaced the Batch-1-era card-list `TasksScreen` with the required structure: page header, 4 client-computed summary tiles (Total Pending, Low Risk, Needs Review, High Risk — bucketed from the real `TaskItem.risk` string the backend already returns; no second endpoint, no fabricated field), a search field (`Search tasks…`) plus an "All risk levels" filter chip/menu, and a `DataTable` with Description/Capability/Risk/Created columns and an action column. Kept both Approve and Cancel as icon buttons in the action column (the blueprint's prose names only "an approve icon button," but dropping Cancel would silently remove existing functionality, which §8's review guidance explicitly warns against for reference-gap screens — Tasks isn't one of the four listed gaps, but the same principle applies). Clearing the filter (via the empty-filtered-state's "Clear filters" action) restores the full list. Approve/cancel continue to call the same `AppState.approveTask`/`cancelTask` real runtime methods, unchanged.

**Disclosed judgment call, not a blueprint requirement:** the three risk buckets (`low`/`controlled` → Low Risk; `high` → High Risk; everything else, including `variable`/`unknown`/absent → Needs Review) are a display-only grouping of the real `risk` string. This mapping is mine, not specified verbatim anywhere in the blueprint or COMPONENT_MAPPING.md; it should be treated as a reviewable choice, not settled architecture.

### 2.4 Suggested-Actions wiring (§4.2/Batch 2)

Already correctly implemented in Batch 1 (verified, not touched): urgent-email fills a read-only prompt via `setComposerDraft` then navigates to Chat (never launches directly); approvals opens Tasks; Connect opens Connections & Providers; Brain setup opens Settings → Model Providers. No suggestion executes a write on tap.

**Disclosed gap, not fabricated:** the blueprint's Batch 2 line "personalization opens Settings → Preferences" has no corresponding suggestion trigger anywhere in the current suggestion generators, and no real signal (e.g., an incomplete-profile flag) exists to drive one. Rather than invent a fake trigger — which §5's "no fabricated metrics anywhere" rule would forbid by the same logic it applies to tiles — this is left unimplemented and recorded here for disposition.

### 2.5 Test reconciliation

Three pre-existing test files were broken by Batch 1's navigation retirement (Home's embedded composer and the old 13-item manifest nav were both removed) but were never exercised by Batch 1's own targeted suite, because none of the three appear in Batch 1's declared test list — they are explicitly Batch 2's to fix, per Blueprint §6 Batch 2's targeted-test list, which names all three:

- `ask_uri_flow_test.dart` — all 4 cases typed into `find.byType(TextField)` while still on Home, which has had no `TextField` since Batch 1. Fixed by navigating to Chat first, in the shared test helper.
- `m18_history_memory_test.dart` — navigated via `find.text('Files')`, an artifact of the retired 13-item nav. Fixed to navigate to Chat then tap the new History tab, and updated the post-resume assertion to check the Conversation tab (in place) instead of a shell navigation to Home.
- `m25_ui_defects_test.dart` — asserted a "Brain: <provider> (<model>)" topbar status pill that Batch 1 correctly retired per §4.1's topbar spec (breadcrumb + theme swatches + Compact toggle only; brain status moved to Home's "BRAIN / PROVIDER" tile). The obsolete assertion was inverted into a regression guard proving the retirement is intentional and permanent, rather than deleted outright or left broken.

None of these three were weakened: each now asserts real, current behavior at the same or greater specificity than before, not a relaxed condition.

---

## 3. Files materially changed

Production:
- `uri_ui/lib/screens/ask/ask_uri_screen.dart` — three-tab Chat surface, model-selector chevron, empty-state/hint copy.
- `uri_ui/lib/widgets/turn_card.dart` — per-message `_CopyMessageAction`.
- `uri_ui/lib/screens/tasks/tasks_screen.dart` — full rebuild per §4.5.
- `uri_ui/lib/screens/history/history_screen.dart` — optional `onResumed` callback; standalone fallback target corrected from `ShellIndex.home` to `ShellIndex.chat`.

Tests:
- `uri_ui/test/ask_uri_flow_test.dart`, `uri_ui/test/m18_history_memory_test.dart`, `uri_ui/test/m25_ui_defects_test.dart` — reconciled with Batch 1's navigation model (see §2.5).

No backend (`uri_core/`) files were touched. No files owned by Batch 1 (`app.dart`, `app_shell.dart`, `home_screen.dart`, `app_state.dart`, the client files) or reserved for Batch 3 (`providers_screen.dart`, `connections_settings_screen.dart`, `settings_shell.dart`, theme files) were modified.

---

## 4. Acceptance criteria satisfied (Blueprint §6 Batch 2 completion gate)

| Criterion | Status |
|---|---|
| Standalone Chat with real model-selector behavior (§7) | Met — state/logic layer unchanged, presentation restyled, real shipped structure documented (§2.1) |
| Real Tasks (filterable table, 4 client-computed summary tiles) | Met (§2.3) |
| All functional/regression checks pass | Met (§5) |
| No model/session/Brain leakage between conversations | Not independently probed this batch — existing `AppState`/session plumbing was not touched, and `chat_lifecycle_test.dart`'s existing turn-identity assertions still pass unchanged, but no new cross-session leakage test was added. Disclosed as untested rather than claimed. |

---

## 5. Test / analyzer evidence

All commands re-run fresh from a clean invocation, not carried over from Batch 1's report.

**Static analysis** (`flutter analyze`, `uri_ui/`): **0 errors, 0 warnings**, 1 pre-existing info (`providers_screen.dart:697:5`) — identical to the Batch 1 baseline.

**Batch 2 targeted suites plus Batch 1 regression guard**, run together:
```
flutter test test/ask_uri_flow_test.dart test/chat_lifecycle_test.dart test/turn_card_test.dart \
  test/attachment_ui_test.dart test/m18_history_memory_test.dart test/m25_ui_defects_test.dart \
  test/dashboard_shell_test.dart test/widget_test.dart test/redesign_test.dart test/http_uri_client_test.dart
```
Result: **72 / 72 passed.**

**Full `flutter test` (entire `uri_ui/test/` suite, unscoped):** **124 / 129 passed, 5 failed.** All 5 failures are in `connections_screen_test.dart` (3) and `m22_ui_parity_test.dart` (2), both entirely outside Batch 2's file scope (Connections & Providers is Batch 3's). `git status`/`git diff` confirm zero modifications to `connections_screen.dart` or anything it depends on this session, by any batch. These are pre-existing baseline failures, not introduced by Batch 1 or Batch 2 — consistent with this repository's established convention (M31's own baseline separately tracked pre-existing failures the same way). Not fixed here: doing so would be scope expansion into Batch 3's declared file ownership.

**Python backend non-regression:** not re-run this batch — no `uri_core/` file was touched, so Batch 1's fresh result (33/33, re-verified independently in §1) stands unchanged.

---

## 6. Remaining defects, blockers, deviations

1. **Role divergence (§0).** Recorded, scoped to this batch, not standing.
2. **"Personalization opens Settings → Preferences" (§2.4).** No real trigger signal exists; left unimplemented rather than fabricated. Needs a User/Claude planning decision on whether a real signal should be added, or the blueprint line should be struck.
3. **Risk-bucket mapping (§2.3).** A disclosed, reviewable display choice, not blueprint-specified.
4. **Empty-state string split (§2.2).** The reference's single dash-joined sentence was mapped onto `EmptyState`'s existing title/message fields rather than reproduced as one literal string, to keep reusing the same component every other screen uses. Flag if literal reproduction is required instead.
5. **Cross-session leakage untested (§4).** No new test added this batch; existing coverage is unchanged, not expanded.
6. **5 pre-existing failures outside Batch 2 scope (§5).** Belong to Batch 3 or an earlier, unrelated baseline gap — not investigated further here to avoid scope expansion.
7. **No mobile/Compact work.** Correctly out of scope — Batch 4's.

No destructive Git operations were performed. Nothing was committed, pushed, or released.

---

## 7. Ready for independent review

**Yes**, with the six items in §6 flagged for the reviewer's attention, and the role divergence in §0 flagged for the User specifically (this batch's implementation path does not match the Frozen Blueprint's §1, by explicit current-session User direction — Batch 3 should resume the blueprint's normal Antigravity/Qwen loop unless told otherwise).

Per this turn's instruction, stopping here. Batch 3 not started.
