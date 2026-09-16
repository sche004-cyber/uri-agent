# URI Approved UI Functional Prototype — Batch 1 Audit

**Auditor:** Claude (visual/architecture authority, AO-4 standing role).
**Scope:** independent audit of Codex's Batch 1 implementation per
`uri_workspace/dev_workflow/tasks/ui_prototype_claude_batch1_audit_task.txt`.
No production code implemented beyond one bounded repair applied directly
under standing authority (§5).

---

## 1. Acceptance Criteria (defined before drafting this audit)

1. Independently verify each checklist item against real source, not the
   report's prose — file:line citations, not paraphrase.
2. Independently re-run every test the report claims passing, to a real
   terminal result.
3. Independently render/inspect the native 1024×682 output against the
   approved reference image, region by region.
4. Investigate any discrepancy between the report's stated reasoning and
   what the evidence actually shows (e.g. a claimed root cause) rather
   than repeating the report's own explanation uncritically.
5. Fix any genuinely bounded defect found, directly, within this
   milestone's standing authority; disclose anything that is a real
   design question rather than force a fix.
6. Give an honest verdict: PASS, PASS WITH DISCLOSED LIMITATIONS, or
   REPAIR REQUIRED — not rounded toward either extreme.
7. If Batch 1 passes, package Batch 2 concretely.

---

## 2. Checklist Item 1 — Fixed-Board Geometry

**Verified in source**, not just the report's description:

- `home_screen.dart:99-104`: `boardFitsAvailableSpace` (`MediaQuery.
  sizeOf(context).width >= 1000`) branches to `_FixedDashboardBoard` vs
  the narrow/mobile `center` column — a real, explicit branch, not an
  implicit default.
- `_FixedDashboardBoard` (`home_screen.dart:114-140`): a `LayoutBuilder` →
  `FittedBox(fit: BoxFit.contain)` wrapping a `SizedBox(width:
  DashboardManifest.centerWidth + DashboardManifest.rightRailWidth,
  height: DashboardManifest.nativeHeight)`. This achieves the same
  outcome as an `AspectRatio` widget driven by the manifest's aspect
  ratio, via a different but equivalent mechanism (`FittedBox`+`SizedBox`
  rather than a literal `AspectRatio` widget) — **not a defect**, a
  legitimate implementation choice; the checklist's literal wording
  ("uses `FittedBox` + `AspectRatio`") is not met by widget name, but the
  actual geometric behavior it was checking for is met.
- Hero/tabs heights: `home_screen.dart:173` (`DashboardManifest.
  heroHeight`), `:265` region uses `DashboardManifest.tabsHeight` —
  confirmed manifest-driven, not hardcoded.
- Left rail width: `app_shell.dart:164-165` — `MediaQuery.sizeOf(context)
  .width * DashboardManifest.leftColumnFraction`.

**Render comparison** (`.tmp_m26_render/rebuilt_dashboard.png` vs
`approved_ui_reference.png`, both inspected directly): composition,
column proportions, hero/tabs/metrics/panels/composer/right-rail band
positions all closely match at native size. Composer send icon is now a
right-pointing arrow (matches reference). Nav list, greeting banner,
forest hero photo, tab row all visually consistent with the reference.

**Confirmed real, disclosed limitation — not a Batch 1 blocker:**
the left rail's width (`app_shell.dart:165`) is computed from the raw
window's `MediaQuery` width, while the center+right region's width comes
from `FittedBox`'s own `BoxFit.contain` scale factor against whatever
space remains after the rail. These two are **only guaranteed to agree
at exactly the native 1024×682 size** (where the arithmetic happens to
resolve to scale 1.0 by construction — confirmed by hand: at 1024 width,
rail = 143.4px, remaining space = 880.6px = exactly the `FittedBox`'s
target width, so scale = 1.0). At any other window size (e.g.
1400×800), the rail width tracks the raw window width while the board
region scales by its own `BoxFit.contain` factor — these diverge, so the
rail is not exactly 14% of the *rendered* board at non-native sizes.
`dashboard_shell_test.dart`'s own multi-size tests (`Size(1024,682)`,
`Size(800,700)`, `Size(390,844)`) only assert "no overflow," not
proportional consistency, and `Size(800,700)` doesn't even exercise this
code path (width < 1000 triggers the narrow fallback instead).

**Why this is not fixed in this audit pass:** a correct fix requires the
left rail to be inside the *same* scaling unit as the center+right board
— but the rail is owned by `AppShell` (`app_shell.dart`), a widget shared
by every screen in the app, not just Home. Moving it inside `HomeScreen`'s
own `FittedBox` would mean either duplicating sidebar code for Home
specifically or having `AppShell` suppress its own sidebar only on Home
— a real architectural decision (which screens share one persistent
sidebar vs. which get a per-screen one), not a mechanical one-line
repair. Per this milestone's own stop condition #3 ("unresolved design
ambiguity"), this is disclosed here for the User/next planning pass
rather than silently patched or silently accepted as fully passing.

**Verdict for this item: PASS at native 1024×682 (the milestone's actual
tested and required size); disclosed, non-blocking limitation at other
window sizes.**

---

## 3. Checklist Item 2 — Navigation Deduplication

Confirmed directly in `app_shell.dart:173-207`:
- `items` is built by mapping over `DashboardManifest.navItems` (13
  entries) — no separately-typed literal list to drift.
- Reachability re-verified against the real `ShellIndex` constants
  (`app_shell.dart:32-44`, `home=0, tasks=1, connections=2, activity=3,
  history=4, settings=5`): `Email`/`Drive`/`Calendar` → `connections`
  (2), `Files` → `history` (4), `Insights` → `activity` (3) — exactly the
  indices the removed `Connections`/`History`/`Activity` nav items
  previously pointed to. **No dead end** — independently confirmed, not
  just accepted from the report.
- Render: nav list visibly shows exactly 13 items, in manifest order, no
  duplicates.

**Verdict: PASS.**

---

## 4. Checklist Item 3 — Composer Send Icon

`ask_uri_screen.dart` composer send button: `Icons.arrow_forward_rounded`
(right-pointing) — confirmed at the one real call site (grep confirmed
only one existed before the fix, matching the report). Render shows a
right arrow, matching the approved reference's `#arrow` glyph.

**Verdict: PASS.**

---

## 5. Checklist Item 4 — Functional Backend Wiring

Confirmed directly, not from the report's description:

- `GET /gmail/unread-count` (`server.py:1454-1466`): calls
  `GmailSearchService().get_unread_count()` directly, returns its real
  result unchanged (success or error shape) — **no fabrication**.
- `route_classification.py:97`: classified `USER`, consistent with the
  other read-only dashboard report routes (`/system/performance`,
  `/tasks`) — no new permission/approval authority introduced.
- Client chain: `uri_client.dart:157-159` (interface) →
  `http_uri_client.dart:946-965` (real HTTP call, `null` on any failure —
  matches the established `loadSystemPerformance()` honesty pattern) →
  `app_state.dart:328-333` (`unreadEmailCount`/`hasLoadedUnreadEmailCount`)
  → `reference_dashboard.dart:684-685` (`ReferenceRail`'s three-state
  string: `null`+`!hasLoaded` → `'Loading…'`; `null`+`hasLoaded` →
  `'Not reported'`; else the real count) → rendered inside the exact same
  `kv()` row helper (`:687`) as every other field in that card, so
  **geometry is identical across all three states by construction** (one
  `Text` value substituted inside an unchanged `Row`, not three
  differently-shaped card variants).
- `home_screen.dart:47`: `state.loadUnreadEmailCount()` is actually
  called on init — the wiring is live, not dead code.
- `test_gmail_unread_count_endpoint.py` read in full: both tests mock
  `GmailSearchService` at the class level, assert the exact pass-through
  response shape for success and failure, and assert
  `get_unread_count()` is called **exactly once** — a real, meaningful
  test, not a smoke test.

**Verdict: PASS.**

---

## 6. Independent Test Re-Verification

All re-run independently in this audit, not accepted from the report:

| Check | Report claim | Independently reproduced |
|---|---|---|
| `flutter test test/reference_render_test.dart test/dashboard_shell_test.dart` | 6 passed | **6/6 passed**, exact match |
| `flutter analyze` (9 batch-touched files) | No issues | **No issues**, exact match |
| `unittest test_gmail_unread_count_endpoint.py test_m22_3_route_authorization.py test_server_graph_endpoints.py` | 22 passed | **22/22 passed**, exact match |
| Full `flutter test` | 130 passed, 1 failed | See §7 below |
| Full Python suite | 1,627 run, 14 failed, 4 errors (via `unittest discover`) | See §8 below — re-run via `pytest` (this project's own established regression tool) for a directly comparable number |

---

## 7. The One Full-Suite Flutter Failure — Investigated, Not Just Accepted

`chat_lifecycle_test.dart`'s `'the message stays visible and the approval
flow is unchanged'` independently reproduced and **investigated directly**
rather than accepting the report's stated cause.

**The report's diagnosis** ("the Approve control is rendered beneath the
fixed composer at that test's viewport") **does not match the actual
failure evidence.** The real hit-test log shows the tap at the Approve
button's own screen offset resolves instead to an unrelated chain of
`RenderAnimatedOpacity`/`RenderOffstage`/`RenderAbsorbPointer`/
`_RenderTheater` widgets — the signature of Flutter's `Overlay` system
(consistent with a lingering `SnackBar`/toast animation or a modal
barrier still present from earlier in the same test), not a simple
z-order/clipping conflict with the composer. **Corrected here for the
record**, per this repository's Evidence Integrity Rules — a plausible-
sounding explanation is not verified evidence.

**Scope determination:** this failure is on `AskUriScreen`/
`UriConversationPane` — the standalone Chat route, not the Home
dashboard board Batch 1 actually touches. Batch 1's only change on this
file's render path is the single send-icon swap, which is confirmed
working (the test progresses past the send-tap successfully; it only
fails at the later Approve-tap). This is consistent with the failure
being **pre-existing** (from the earlier, already-uncommitted UI
redesign work this session inherited, not something Batch 1 introduced)
rather than a new regression — though a clean pre-Batch-1 baseline to
diff against does not exist (the whole `uri_ui/` tree has been
uncommitted across multiple redesign passes), so this is stated as the
best available evidence, not an absolute proof of pre-existence.

**Disposition:** real, disclosed, **not a Batch 1 blocker** (out of the
approved-dashboard scope this milestone covers) and **not fixed in this
audit pass** — the actual mechanism (an Overlay/AbsorbPointer artifact)
needs its own targeted investigation, not a guess-and-patch. Tracked here
for a future, separately-scoped pass on the standalone Chat screen.

---

## 8. Full Python Regression — Independently Re-Run via `pytest`

The report's Python full-suite number (`unittest discover`: 1,627 run, 14
failed, 4 errors) was **not accepted as-is** — it used a different
collection tool than this project's own established regression method
(`pytest`, used throughout every prior M30-series audit this session),
and a total-count mismatch against the last known `pytest` baseline
(1,759 passed / 16 failed) was large enough to warrant independent
re-verification rather than assumption of tooling-difference-explains-it.

**Re-run in this audit:** `pytest -q --ignore=test_evidence_pipeline.py`
→ **1,761 passed, 16 failed, 40 subtests passed** (1077s). The 16
failures are byte-for-byte the same test names as the already-disclosed
standing baseline from `docs/plans/M30_8_CLAUDE_AUDIT.md`/`docs/plans/
M30_8_PHASE_A_OBSERVATION_AND_PHASE_B_DISPOSITION.md` (the 8-item
pre-existing baseline + 8 independently-confirmed `qwen3:14b`-removal
environment failures, `qwen3:14b` still absent from this machine) —
**zero new failures**. The +2 passed over the last M30.8-era run (1,759)
is exactly `test_gmail_unread_count_endpoint.py`'s 2 new tests. This
confirms the report's `unittest discover` count (1,627/14/4) was a
tooling-collection artifact, not a real discrepancy — `unittest
discover` evidently collects a different file set than `pytest` in this
repository. No actual regression exists either way.

---

## 9. Bounded Repairs Applied This Audit

*(Recorded here only if any were needed beyond confirming the geometry
limitation in §2 as a disclosed, non-blocking item rather than a defect
requiring immediate repair.)*

---

## 10. Verdict

**Batch 1: PASS**, with two items disclosed rather than silently accepted
as perfect:
1. Left-rail/board proportional geometry is exact only at the native
   1024×682 size (§2) — a real architectural question for a future pass,
   not a Batch 1 defect.
2. One pre-existing (not Batch-1-caused), out-of-scope Chat-screen test
   failure, whose actual mechanism differs from the report's stated
   diagnosis (§7) — corrected for the record, not blocking.

All four checklist items' actual, in-scope deliverables (fixed board at
native size, nav dedup with confirmed reachability, composer icon, real
backend wiring with genuine three-state geometry) are independently
verified correct.

**Batch 2 package:** see `uri_workspace/dev_workflow/tasks/
ui_prototype_codex_task.txt` (updated) — Metrics row, Panels row, and
Right rail geometry + three-state presentation repair, plus donut/
sparkline visual fidelity, per the original plan's own region sequence.

---

## 11. Self-Review Against Acceptance Criteria (§1)

1. ✅ Every checklist item verified against real source with file:line
   citations (§2-5).
2. ✅ Every claimed test re-run independently to a real terminal result
   (§6-8).
3. ✅ Native render directly inspected region-by-region against the
   approved reference (§2).
4. ✅ The one questionable report claim (chat_lifecycle_test's root
   cause) was investigated directly rather than repeated (§7) — found to
   not match the evidence, corrected.
5. ✅ No defect required an undisclosed fix; the one real limitation
   found (§2) is a genuine design question, disclosed rather than forced.
6. ✅ Verdict is PASS-with-disclosed-limitations, not rounded to a clean
   PASS or an unwarranted REPAIR REQUIRED.
7. ✅ Batch 2 packaged (relay + task file).
