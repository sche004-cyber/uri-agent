# URI Approved UI Functional Prototype — Batch 2 Audit & Final Prototype Report

**Auditor:** Claude (visual/architecture authority, AO-4 standing role).
**Scope:** independent audit of Codex's Batch 2 implementation, plus one
bounded repair (right-rail vertical fit) applied directly under standing
authority, plus the final prototype-readiness determination.
**Verdict: `UI PROTOTYPE READY FOR USER REVIEW`.**

---

## 1. Acceptance Criteria (defined before drafting this audit)

1. Verify the three-state geometry contract is real (test + source), not
   asserted from the report alone.
2. Verify every DEFER item (GPU, model-usage, storage) stayed honestly
   unavailable — no fabricated data introduced to look more finished.
3. Verify CPU/RAM/Disk/Activity/unread-count stayed real and live.
4. Independently render and compare, region by region, against the
   approved reference — not accept "visually compared" from the report.
5. Apply the explicitly-authorized right-rail bounded fix directly,
   re-verify, re-render — don't just note the problem.
6. Give an honest final verdict, disclosing every known limitation by
   name rather than rounding toward "ready."

---

## 2. Three-State Card Geometry Contract — Verified

`uri_ui/lib/widgets/dashboard/reference_dashboard.dart` (Batch 2 diff)
and `uri_ui/test/dashboard_shell_test.dart`'s new test **`dashboard cards
keep identical geometry in every presentation state`** were both read in
full, not accepted from the report's description:

- The test pumps every touched metric/panel/right-rail card with stable
  `ValueKey`s (`card('Today at a glance', ...)` etc., confirmed present)
  across `loading`/`live`/`unavailable` and compares each card's complete
  `Rect` (offset + size) — a real geometry assertion, not a smoke test.
- **Independently re-run:** `flutter test test/reference_render_test.dart
  test/dashboard_shell_test.dart` → **7/7 passed**, including this test,
  both before and after this audit's own bounded repair (§5) — confirming
  the repair (pure spacing constants, applied identically regardless of
  state) did not break geometry equivalence across states.
- Read the actual `unavailable` rendering for GPU, Model Usage, and
  Storage directly in source: GPU keeps the sparkline painter and device
  caption slot, drawing a flat neutral-color baseline instead of a real
  curve; Model Usage's `UsageRing` (`reference_dashboard.dart:715-731`)
  draws a real stroked circle at the manifest's donut size in a
  desaturated token color instead of the old hollow/absent ring; Storage
  keeps its full-width meter bar filled in a neutral color rather than
  empty. **None of these collapse to a dash-only or blank card** — the
  exact regression the second-pass audit found is confirmed repaired.

**Verdict: PASS.**

---

## 3. Honest Data / No Fabrication — Verified

| Field | Source | State observed |
|---|---|---|
| CPU / RAM / Disk | Real `/system/performance` | `live`, real sparklines and values |
| GPU | No backend telemetry (confirmed DEFER) | `unavailable`, neutral baseline + honest label — never a value |
| Activity | Real `/activity` | `live`, real 6-stat bar chart |
| Model Usage | No backend request accounting (confirmed DEFER) | `unavailable`, neutral filled ring + honest label — never a fake percentage split |
| Storage | No confirmed backend category source | `unavailable`, neutral meter + per-category "Not reported" rows — not presented as real disk telemetry mislabeled as storage categories (the Batch 1 render's actual defect, now corrected) |
| Unread email count | Real `GET /gmail/unread-count` (Batch 1) | `Not reported` in this render (Gmail not authenticated at the host level in this dev environment) — an honest `unavailable` result, not a stale/fake number |
| Current Model name/provider | Real active-brain config | `live` |
| Current Model usage stats (Requests/Context/Cost) | No confirmed backend source | `unavailable`, `Not reported` per row |

No field anywhere in this render shows a value that isn't either real or
explicitly labeled unavailable. **Verdict: PASS.**

---

## 4. Native Render vs. Approved Reference — Directly Compared

`.tmp_m26_render/rebuilt_dashboard.png` (this audit's own re-render,
post-repair) inspected side-by-side against
`docs/design_references/approved_ui_reference.png`, region by region:

- **Left rail:** logo, tagline, 13-item nav, forest-photo footer with
  quote — matches.
- **Hero:** greeting, forest photo, quote block — matches.
- **Tabs:** 7 pills, active state — matches.
- **Metrics row:** 5-card layout matches; CPU/RAM/Disk populated and
  real; GPU and System Health honestly unavailable with preserved shape
  (reference shows populated values here since it's a static mock — this
  divergence is expected and correct, not a defect, per the milestone's
  own "real data or honest unavailable, never fake" directive).
- **Panels row:** 4-panel layout matches; Activity populated and real;
  Model Usage and Storage honestly unavailable with preserved shape
  (same expected/correct divergence as above); Active Connections
  populated and real.
- **Composer:** right-pointing send arrow — matches.
- **Right rail:** profile, date, and all 4 cards (Today at a glance,
  Current Model, Sandbox & Permissions, Tools & Skills) now **fully
  visible within the native 682px height**, matching the reference's own
  fully-visible right rail — see §5 for the fix that closed this gap.

**Verdict: PASS**, with the expected/correct divergence noted (populated
mock data in the static reference vs. real/honest data in the live
prototype) — not a defect, the entire point of a functional prototype.

---

## 5. Bounded Repair Applied This Audit — Right Rail Vertical Fit

**Defect, independently confirmed before fixing:** the render inherited
from Batch 2 showed the right rail's total content height exceeding the
682px native board height — the "Tools & Skills" card fell entirely
below the capture, and "Sandbox & Permissions" was visibly clipped.
Computed by hand from `reference_dashboard.dart`'s pre-fix spacing
constants: ~786px of content against ~658px of available height inside
the rail's own container padding — a ~128px overflow, consistent with
what the render showed.

**Fix applied** (`reference_dashboard.dart`, `ReferenceRail.build()`,
two passes): reduced purely cosmetic spacing constants — `GlassPanel`
padding (12→7), inter-card bottom padding (8→4), `kv()` row vertical
padding (5→3), the post-heading `SizedBox` gaps in all four cards
(10-12→6), two secondary in-card gaps (8→4), the rail's own top spacer
(20→6) and profile-row `IconButton`'s default 48×48 tap-target padding
(removed via `padding: EdgeInsets.zero, constraints: BoxConstraints()`),
and the date row's padding (15→5). **No content, copy, card, field, or
logic was added, removed, or changed** — every value shown before the
fix is shown identically after it; only whitespace shrank. Applied in
two small passes, re-rendering after each, since the first pass (~108px
saved) left a small remaining clip that the second pass (~34px more)
closed cleanly.

**Re-verified after the fix:**
- `flutter analyze lib/widgets/dashboard/reference_dashboard.dart` — no issues.
- `flutter test test/reference_render_test.dart test/dashboard_shell_test.dart` — **7/7 passed**, including the geometry-equivalence test (confirming the fix preserves state-to-state geometry identity — it changed the *absolute* size uniformly, not the *relative* consistency across states).
- Full `flutter test` — **131 passed, 1 failed** — the exact same, already-disclosed `chat_lifecycle_test.dart` failure (§6), zero new failures from this repair.
- Fresh native 1024×682 render (this audit's own): Tools & Skills fully visible with its "Manage Tools & Skills" button clear of the capture boundary, comfortable margin below it — confirmed visually, not assumed.

---

## 6. Known, Disclosed, Non-Blocking Limitations

Carried forward from the Batch 1 audit, still accurate, not re-litigated:

1. **Left-rail/board proportional geometry is exact only at the native
   1024×682 size** (`docs/plans/URI_APPROVED_UI_BATCH1_AUDIT.md` §2). At
   other window sizes the rail (sized from raw window width) and the
   `FittedBox`-scaled board region can diverge slightly. Fixing this
   properly requires a real architectural decision (whether `AppShell`'s
   shared sidebar should be visually independent from the Home board at
   non-native sizes) — appropriately deferred pending User/architecture
   sign-off, not silently patched.
2. **One pre-existing Chat-screen test failure**
   (`chat_lifecycle_test.dart`'s approval-flow test) — independently
   re-confirmed still present and still isolated to the standalone
   `AskUriScreen` route, not the dashboard. Its actual mechanism (an
   Overlay/`AbsorbPointer` widget intercepting the tap, per the Batch 1
   audit's own investigation) has not been root-caused; it needs its own
   targeted pass, unrelated to this dashboard milestone's own scope.
3. **DEFER items remain deferred, correctly**: GPU telemetry, model-usage
   request accounting, and a real storage-category breakdown all still
   have no backend source. The prototype shows them honestly unavailable
   — this is the intended, approved behavior for this milestone, not an
   outstanding gap to close before "ready for review."

None of these block "ready for review": (1) and (2) are pre-existing/
architectural, not dashboard defects; (3) is the explicitly-approved
scope boundary this milestone was built around from the start.

---

## 7. Comprehensive Prototype Report

1. **Latest rendered prototype:** `.tmp_m26_render/rebuilt_dashboard.png`
   (this audit's own fresh render, post-repair).
2. **Approved reference:** `docs/design_references/approved_ui_reference.png`
   — compared directly in §4; composition, proportions, and all four
   region bands match at native size; the only differences are the
   expected real-vs-mock-data divergence.
3. **Functional elements completed:** fixed-board framing at native size
   (Batch 1); 13-item deduplicated navigation with confirmed reachability
   (Batch 1); right-pointing composer send icon (Batch 1); real unread
   Gmail count wired end-to-end with honest three-state rendering (Batch
   1); three-state geometry contract enforced across metrics, panels, and
   right-rail cards (Batch 2); Model Usage/Storage/GPU honest-unavailable
   treatments with preserved chart/meter/ring geometry (Batch 2); right
   rail now fits cleanly within the native board height (this audit).
4. **Bounded backend additions made:** `GET /gmail/unread-count`
   (`server.py:1454-1466`), read-only, classified `USER`, no approval/
   permission/dispatcher change — the only backend addition across both
   batches.
5. **Deferred items (unchanged, explicitly approved scope boundary):**
   GPU telemetry, model-usage/request accounting, storage-category
   breakdown, reminders/scheduled tasks (never in scope for this
   milestone).
6. **Tests and build status:** Flutter focused (`reference_render_test`
   + `dashboard_shell_test`): 7/7 pass. Flutter full suite: 131 passed, 1
   failed (pre-existing, disclosed, unrelated to the dashboard — §6 item
   2). `flutter analyze` on every touched file: no issues, both batches
   and this audit's own repair. Python focused (unread-count endpoint +
   route classification + graph endpoints): 22/22 pass. Python full
   regression (independently run via `pytest`, this project's own
   established tool, not the report's `unittest discover`): **1,761
   passed, 16 failed** — the exact standing baseline (8 pre-existing +
   8 disclosed `qwen3:14b`-environment failures), zero new failures.
7. **Known limitations:** §6 above, both explicitly disclosed and
   assessed as non-blocking for this verdict.

---

## 8. Final Verdict

**`UI PROTOTYPE READY FOR USER REVIEW.`**

Every region of the approved dashboard reference is now implemented,
tested, and independently verified to match at native 1024×682
resolution, with real backend data wherever it exists and honest,
geometry-preserving unavailable states wherever it doesn't — the
functional prototype goal ("not just a visual mockup") is met: the
unread-email count, system performance, and activity data are real, live
values a user can actually rely on, not a static image. The two disclosed
limitations (§6) are pre-existing/architectural questions outside this
milestone's own scope, not defects in the delivered dashboard.

**No commit or push has been performed.** Per this milestone's own
standing rules, that remains the User's own, separate, explicit
instruction — this verdict is a readiness determination, not a release.

---

## 9. Self-Review Against Acceptance Criteria (§1)

1. ✅ Geometry contract verified via direct source read + independent
   test re-run, not accepted from the report (§2).
2. ✅ Every DEFER item's actual rendered state checked field-by-field for
   fabrication (§3) — none found.
3. ✅ Every live-data field's real backend source cited and confirmed
   (§3).
4. ✅ Native render independently produced and compared region-by-region
   against the approved reference (§4), not assumed from "visually
   inspected" in the report.
5. ✅ The right-rail fit issue was fixed directly (two passes, re-verified
   each time), not merely logged for a future batch (§5).
6. ✅ Final verdict names every known limitation explicitly (§6) rather
   than presenting an unqualified "ready."
