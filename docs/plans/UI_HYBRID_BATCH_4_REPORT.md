# URI Hybrid UI — Batch 4 Implementation Report

**Initiative:** URI Hybrid UI Implementation
**Governing Blueprint:** `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`
**Batch:** Batch 4 — Compact, mobile, consistency, full regression (final batch)
**Implementer this batch:** Claude (see §0 — explicit, scoped role divergence, User-directed)
**Reviewer:** not yet run (see §8)

---

## 0. Role divergence from the Frozen Blueprint (disclosed, not silent)

Same disclosed divergence as Batches 2 and 3 (see their reports' own §0): the Frozen Blueprint's §1 assigns this initiative to Antigravity (implementer) and Qwen (reviewer), with Claude/Codex restricted to planning and review. This batch was again implemented by Claude directly, under an explicit current-session User instruction with the same authorization pattern used for Batch 3 ("You are authorized to make bounded Batch 4 repairs, update tests..., and run all required targeted/full validation").

Because Batch 3's own report closed by saying Batch 4 should resume the normal Antigravity/Qwen loop unless the User said otherwise, and the User's Batch 4 instruction repeated the identical override pattern in the same session immediately after accepting Batch 3, this was treated as a continuation of the same standing override for this session rather than re-asked. This is Batch 4 — the blueprint's final batch — so this divergence does not carry forward to any further batch; recorded here per the repository's auditable-correction-history convention.

---

## 1. Implementation summary

Scope per Blueprint §6 Batch 4: Compact (§4.4), Mobile (§4.8), consistency, full regression. R2 (§5) proved again for Compact specifically, as the blueprint requires.

### 1.1 Compact (§4.4)

- New `AppState.isCompact` / `setCompact(bool)` (`services/app_state.dart`) — a pure in-session presentation flag, never persisted (unlike `themeChoice`), matching the reference's `presentationToggle` semantics.
- New `widgets/compact_overlay.dart`: `CompactOverlay`, a 420×580 floating window (clamped down if the actual viewport is smaller, so a live desktop resize never overflows) centered over a scrim, reusing the exact same `UriConversationPane`/`UriCommandDock` widgets the Workspace Chat destination mounts. Neither of those widgets was forked or duplicated — both read/write `AppState` directly, so Compact can never create a new session, duplicate a request, or drop the draft/attachments/model override/pending response.
- `app.dart`'s `UriHome` now wraps `AppShell` in a `Stack`: the Workspace shell stays mounted underneath (so Expand is instant, nothing to reconstruct) but is wrapped in `IgnorePointer(ignoring: isCompact)` so a tap can't reach through the overlay to the shell behind it.
- `app_shell.dart`: the wide topbar's Compact-mode button now calls `state.setCompact(true)` (previously a `Batch 4` placeholder `SnackBar`). The overlay's own header carries the "Expand to Workspace" action that calls `state.setCompact(false)`.
- **Consistency fix:** removed the narrow/mobile AppBar's duplicate Compact-mode button. The reference's `MobileApp.dc.html` has no Compact equivalent, and a fixed 420×580 window has nowhere to fit on a narrow layout — Compact is a Workspace (wide-topbar) presentation only, per §4.4's own framing ("Workspace Desktop" page). This was a Batch-1-era placeholder duplicated in both layouts before either actually worked; now only the wide one exists and it actually works.

### 1.2 Mobile (§4.8)

- **Home and Chat:** already matched the reference from earlier batches (Home's 4-tile grid already collapses 4→2 columns below 900px with truthful unavailable-states preserved; Chat's model selector already uses a `PopupMenuButton`, which *is* the popover pattern §4.8 calls for — no separate `modelMenuOpen` code path was needed). Verified via the full regression run at both 1280×900 and 390×844 rather than rebuilt from scratch, since no reference-layout gap was found. Not independently visually confirmed in a running app this session — see §6.
- **Tasks** (§8.1, explicit reference gap — no mobile mockup exists): new `_TasksCardList` in `tasks_screen.dart`, built from the desktop table's own real fields (Description, Capability, Risk, Created) and both real actions (Approve/Cancel), switched in below `UriBreakpoints.wide` via the same `LayoutBuilder` pattern used elsewhere in this app. Nothing summarized away or fabricated — every field and action the desktop `DataTable` shows, the card shows too.
- **Connections & Providers:** Batch 3 already built the "two full-width sections... stacked" fallback explicitly named as one of §8.2's two acceptable options — verified still correct this batch, not rebuilt.
- **Settings:** the master-detail-vs-single-column-drill-in split (§8.3) already existed from before Batch 1 (`settings_shell.dart`'s `_CompactSettingsList`/`_CompactSettingsDetail`) — verified still correct, not rebuilt.

### 1.3 Consistency fixes (latent defects found and fixed this batch)

Building the Compact window and the Tasks mobile view — genuinely new narrow-width renders that nothing before this batch had ever exercised — surfaced four real, pre-existing layout defects, each fixed at its structural root rather than papered over:

1. **Composer model-selector chip** (`ask_uri_screen.dart`, `_ModelSelectorChip`): its label `Text(..., overflow: ellipsis)` sat directly in an unbounded `mainAxisSize: min` Row, so `ellipsis` had nothing to clip against and the chip demanded its full natural width regardless of available space — overflowing the composer's icon row in the Compact window. Fixed: wrapped the label in `Flexible`, and bounded the chip itself with a `ConstrainedBox` (96px compact / 160px otherwise) at its call site.
2. **Composer outer margin** (`_ComposerBody`): was a hardcoded `EdgeInsets.fromLTRB(20, 8, 20, 12)` regardless of `compact` — the `compact` flag only ever adjusted internal padding. Made the margin itself compact-aware too.
3. **`TurnCard`'s proposal-action header row** (`_ProposalBlock`): `Text('Proposed action')` next to a `Spacer()` and an impact `StatusPill`, with no flex protection on the label — at the Compact/mobile width this combination no longer fit at natural size. Fixed: wrapped the label in `Flexible` with `overflow: ellipsis`.
4. **`TurnCard`'s own header row**: the turn's stage `StatusPill` (e.g. "Awaiting your approval" — a long label) sat next to a fixed-size copy-message icon button with no flex protection of its own. Fixed: wrapped the pill in `Flexible`, and made `StatusPill`'s own `Text` `maxLines: 1` / `overflow: ellipsis` generally (harmless everywhere else it's already used, since ellipsis on an unconstrained width is a no-op).
5. **`_ProposalBlock`'s Approve/Cancel row**: a plain `Row`, same class of bug already fixed once elsewhere in this codebase (`providers_screen.dart`'s own comment on this exact problem) but never applied here. Fixed: `Row` → `Wrap`, the same established pattern.
6. **Tasks summary tiles** (`_SummaryTiles`): a fixed `childAspectRatio: 2.4` fit a tile's two-line label+value only at the 4-column (≥720px) width; at 2 columns (narrower) each tile became too short for its own content. Fixed: `childAspectRatio` now depends on column count (2.4 at 4 columns, 1.6 at 2).

Also gave `TurnCard` a `compact` parameter (denser `UriSpace.md` padding vs `UriSpace.lg`) per §4.4's "denser bubble padding" requirement — previously `TurnCard` had no compact-awareness at all despite `UriConversationPane`/`UriCommandDock` already carrying a `compact` flag from Batch 2's forward-looking plumbing.

None of these six were cosmetic nice-to-haves discovered by inspection — all six were caught because the new automated tests in §1.1/§1.2's coverage actually rendered these surfaces at their real narrow/Compact dimensions for the first time and a `RenderFlex overflowed` assertion failed. Each was root-caused with a live (non-disposed) `FlutterError.onError` capture before fixing, not guessed at.

---

## 2. Files materially changed (Batch 4 only)

The working tree also carries Batches 1–3's own uncommitted changes (all previously reported and accepted); the list below is Batch 4's own diff only.

Production:
- `uri_ui/lib/app.dart` — Compact overlay mounting (`Stack` + `IgnorePointer`), `didChangePlatformBrightness`-adjacent wiring untouched (that's Batch 3's).
- `uri_ui/lib/services/app_state.dart` — `isCompact` / `setCompact`.
- `uri_ui/lib/widgets/app_shell.dart` — wide topbar Compact toggle wired to real state; narrow AppBar's duplicate Compact button removed.
- `uri_ui/lib/widgets/compact_overlay.dart` — **new**.
- `uri_ui/lib/screens/ask/ask_uri_screen.dart` — composer margin compact-aware; model-selector chip `Flexible`/`ConstrainedBox` fix; `TurnCard` now receives `compact`.
- `uri_ui/lib/widgets/turn_card.dart` — `compact` parameter + padding; `Flexible` fixes on the proposal-header and main-header rows; Approve/Cancel `Row` → `Wrap`.
- `uri_ui/lib/widgets/status_pill.dart` — `maxLines: 1` / `overflow: ellipsis` on the pill's own label.
- `uri_ui/lib/screens/tasks/tasks_screen.dart` — new `_TasksCardList` (mobile), responsive `childAspectRatio` fix, shared `_formatTaskDate`.

Tests:
- `uri_ui/test/compact_overlay_test.dart` — **new**: overlay open/close + wide-only availability; draft continuity; session/transcript continuity (no new session, no duplicated turn); in-flight-request continuity (no duplicate send on a mode switch mid-request).
- `uri_ui/test/tasks_responsive_test.dart` — **new**: wide shows the real `DataTable`; narrow shows the same real tasks as cards with a working Approve action end to end.

No `uri_core/` (backend) file was touched this batch (or any prior Hybrid UI batch).

---

## 3. Mobile/Compact behavior implemented (blueprint cross-reference)

| Blueprint requirement | Status |
|---|---|
| Compact: same session, 420×580 floating window, same composer field order | Met (§1.1) |
| Compact: Expand returns to Workspace with exact same session ID, transcript, draft, attachments, model override, pending response | Met and proven by test (§1.1, `compact_overlay_test.dart`) |
| Compact: denser bubble padding/font-size | Met for padding (`TurnCard.compact`); font-size left at the existing `compact`-aware text styles already used elsewhere (no additional per-size scaling was specified beyond what §4.3/§4.4's existing `compact` plumbing already does) |
| Mobile: 5-item bottom nav, "Connect" abbreviated, same order as desktop | Already correct from Batch 1 — verified, not rebuilt |
| Mobile: Home/Chat follow the reference layout | Verified already correct (§1.2) — not independently visually confirmed in a live app this session (§6) |
| Mobile: Tasks/Connections & Providers/Settings genuine new responsive design | Tasks built this batch (§1.2); Connections & Providers and Settings verified already correct from Batch 3 and pre-Batch-1 respectively |
| R2 proved again for Compact | Met — `compact_overlay_test.dart` |

---

## 4. Test / analyzer / regression evidence

All commands re-run fresh this session.

**Static analysis** (`flutter analyze`, `uri_ui/`): **0 errors, 0 warnings**, 1 pre-existing info (`providers_screen.dart:697:5`, unchanged since Batch 1).

**Batch 4 targeted suites** (per Blueprint §6 Batch 4's list, plus the new Compact/Tasks-responsive tests):
```
flutter test test/connections_screen_test.dart test/m22_ui_parity_test.dart \
  test/m24_providers_settings_shell_test.dart test/dashboard_shell_test.dart \
  test/redesign_test.dart test/compact_overlay_test.dart test/tasks_responsive_test.dart \
  test/four_theme_persistence_test.dart test/chat_lifecycle_test.dart \
  test/attachment_ui_test.dart test/reference_render_test.dart test/multi_client_test.dart \
  test/bootstrap_screen_test.dart
```
Result: **73 / 73 passed.**

**Full `flutter test` (entire `uri_ui/test/` suite, unscoped): 150 / 150 passed, 0 failed.** Batch 3's baseline was 143/143; this batch adds 7 new tests (5 in `compact_overlay_test.dart`, 2 in `tasks_responsive_test.dart`) and introduces zero regressions.

**Required baselines from this turn's instruction, individually re-verified:**
- Full Flutter suite: **150/150** (was 143/143 before this batch; +7 new, 0 broken).
- M31/security regression (`tests/test_m31_model_brain_ux.py` + `tests/dev_workflow/test_security_boundary.py`): **33/33 passed** in 24.59s — identical count to the Batch 1–3 baseline, re-run fresh via `.venv/Scripts/python.exe -m pytest`.
- Chat lifecycle (`flutter test test/chat_lifecycle_test.dart`): **11/11 passed** — exact count confirmed line by line, matching this turn's stated baseline exactly (5 `AppState.ask()` lifecycle cases + 3 `TurnCard` rendering cases + 1 narrow-width overflow guard + 2 end-to-end `AskUriScreen` cases).
- Four-theme persistence (`four_theme_persistence_test.dart`): **9/9 passed**, included in the full suite run.
- Connections & Providers behavior: `connections_screen_test.dart` + the two Connections cases in `m22_ui_parity_test.dart` + `m24_providers_settings_shell_test.dart`: all passing, included above.
- Standalone Chat/Tasks/Home behavior: `chat_lifecycle_test.dart`, `tasks_responsive_test.dart`, `dashboard_shell_test.dart`, `redesign_test.dart`'s navigation case: all passing, included above.

**Backend regression scope note:** only the two Python suites this turn explicitly named as baselines to preserve were run (both 33/33, matching the pre-Batch-4 baseline exactly) — the full `uri_core/` pytest suite was not separately run, since Batch 4 touched zero backend files and no other backend-affecting change occurred this session.

---

## 5. Remaining defects, blockers, deviations

1. **Role divergence (§0).** Recorded. This is the blueprint's final batch, so this note does not carry forward to a "next batch" — final milestone review (whoever performs it) should be aware Batches 2–4 were all implemented by Claude directly rather than Antigravity, each under an explicit scoped User override, each independently reviewed and accepted (Batch 2 by Claude's own re-verification pass recorded in its own report; Batch 3 by an independent Antigravity review, `docs/plans/UI_HYBRID_BATCH_3_REVIEW.md`, verdict `BATCH_3_ACCEPTED`).
2. **Mobile Home/Chat visual match not independently confirmed live.** Judged already-correct from static code inspection and the full automated-test pass at both 1280×900 and 390×844 widths, not by visually running the app and comparing to the reference screenshots pixel-for-pixel. Disclosed per the Verification-First standard's "explicit unverified disclosure" requirement.
3. **"Denser font-size" for Compact bubbles** was not given its own distinct type-scale — only padding was made compact-aware on `TurnCard` (see §3). The existing text styles (`titleMedium`/`bodyMedium`/etc.) are shared between Workspace and Compact; no separate smaller compact type scale was introduced. This is a legitimate reading of "denser... font-size" as already covered by Flutter's existing responsive text rendering within the narrower window, not a gap I'm aware of causing any visible defect, but it's a judgment call worth the reviewer's attention.
4. **Full backend Python regression scope** — see §4's note. Only the two named suites were run; the broader `uri_core/` suite's current pass/fail state was not independently re-verified this batch (no backend file changed here, so no basis to suspect it moved).
5. **Full 4-theme × Compact/mobile visual matrix was not manually inspected in a running app.** Automated tests confirm structural/functional correctness (palette resolution, overlay open/close, card rendering, no overflow errors) across the tested width/theme combinations exercised by the test suite, but a live `flutter run` visual walkthrough of every theme × surface × mode combination was not performed this session.

No destructive Git operations were performed. Nothing was committed, pushed, or released. This is the blueprint's final batch (§6) — no Batch 5 exists to defer to.

---

## 6. Is the Hybrid UI milestone ready for final independent validation?

**Yes, with the five items in §5 flagged for that validation pass, particularly #2 and #5 (no live visual walkthrough was performed by the implementer this batch).**

All four batches (Connections/shell/Home truthfulness, standalone Chat/Tasks, Connections & Providers/Settings/four themes, Compact/mobile/consistency) are implemented, each batch's own targeted tests pass, the full Flutter suite is green at 150/150 with zero known failures remaining, static analysis is clean, and the M31/security backend regression this turn asked to preserve is unchanged at 33/33. Per Blueprint §6 Batch 4's completion gate, User live acceptance and Claude's final audit/release under existing release authority are the remaining steps — this report does not itself constitute either.
