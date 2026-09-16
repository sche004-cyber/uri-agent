# Hybrid UI acceptance and evidence checklist

Status: NOT RUN. Each item requires PASS/FAIL/NOT RUN, actual-versus-expected result, command or reproducible live steps, screenshot/log path and source/reference version. Unit success does not imply live acceptance. Claude audits actual production paths read-only; Codex repairs; User supplies live acceptance.

## Reference and visual checks

- [x] Published Artifact `https://claude.ai/artifact/FtXLngXPXiRMCY9YQBefht` accessible — **VERIFIED 2026-09-16** via the Artifact tool (`Main.dc.html`, `MobileApp.dc.html`, `Palettes.dc.html`, `canvas.json` all read in full; the 2026-09-15 "sign-in wall" applied only to unauthenticated browser access). Implementer must still re-read it directly before building each screen and compare production against it at the same dimensions — hierarchy, region placement, spacing, typography, colors, radius, selection, hover/focus and empty states — and list every discrepancy. No legacy preview substitution. Mobile reference covers Home/Chat only (Tasks/Connections & Providers/Settings are placeholders in the reference itself — see `UI_DESIGN_AUTHORITY.md`); those three require new responsive design, not reference comparison.
- [ ] Exactly Home / Chat / Tasks / Connections & Providers / Settings in one global navigation; collapsed rail has accessible labels/tooltips and same destinations; expanded labels visible; toggle/pin/restart preserve preference and selected route within session.
- [ ] Home contains metrics/actions and no composer/transcript; Chat is a separate full workspace. Legacy 13-item tree and scaled dashboard are absent from active production paths.
- [ ] No theme control outside Settings → Appearance. All four themes cover every screen, modal, popover, toast, status, file card and Compact/mobile surface.

## Data, actions and runtime checks

- [ ] **R1 — failed task read ≠ empty queue:** test timeout/network error, 401/403/500 and malformed response independently; Home and Tasks show unavailable/error, never zero/all-clear. A successful `tasks: []` alone shows confirmed zero. Retry restores the authoritative result; stale prior count is labeled. Test actual HttpUriClient path, not only mocked AppState.
- [ ] **R2 — draft disposal during navigation:** type an unsent draft, stage an attachment and choose a model; navigate Chat → Home → Tasks → Chat and toggle sidebar. Assert exact text, attachment identity, override and session ID preserved. Repeat Compact → Workspace and during in-flight ask; no duplicate submission. New Chat/logout isolation remains intentional and separately tested.

- [ ] Feed real successful task/connection/unread/provider responses, then separately delay/fail/malform each response. Loading is visible; confirmed zero differs from error; stale data labeled; retry works. Pending tasks/approvals clearly share one source. No unsupported calendar/project/health metrics.
- [ ] New Chat changes session ID; history resume loads existing transcript without execution; navigation leaves session ID unchanged. Late replies cannot populate a different conversation. Drafts/attachments/overrides do not leak between users/sessions.
- [ ] Send actual read-only prompt and attachment through canonical Brain discovery/selection → runtime validation → execution → results fed back to Brain → grounded visible response. Capture session/turn IDs and redacted request/result evidence.
- [ ] User and URI messages copy exact displayed content; relevant draft/prompt copy works; Copied feedback clears; clipboard failure does not claim success.
- [ ] All turn stages, proposal/risk details, approval/cancel, memory confirmations, tool/workflow failure, files and attachments survive presentation migration. Double click cannot cause duplicate mutation. Cancellation causes no external write; unauthorized request rejected by runtime.
- [ ] Suggestions open correct workspace or fill/submit explicit canonical prompt. Review approval/draft uses real ID. Connect/Verify/Brain/preferences links work. No side-effect request merely from rendering/tapping a review suggestion. Unsupported halted-project resume never implied working.
- [ ] Tasks filters use actual fields; clear-filter restores list; pending rows open correct session; approve/cancel refresh queue with success/failure feedback; no invented completed/due totals.
- [ ] Connections setup/error/disconnect and provider config/key/verification/fallback flows preserve real server errors. Test USER/ADMIN restrictions; UX tier grants nothing.
- [ ] One visible model selector, real discovered/verified inventory, unverified choices disabled with explanation, URI Auto retained. Verify sent override and persisted serving-model caption against response/history; selection does not change global Brain. Unavailable model produces honest error/recovery.
- [ ] Mic indicates current unavailable status; no false recording/transcription. Every retained Settings capability remains reachable, including server/bootstrap, memory/context, profile, preferences, diagnostics and admin controls.

## Responsive and accessibility matrix

Run all four themes at desktop 1440×900 and 1024×682, intermediate 768×1024, mobile 390×844 and 360×640, and Compact 420×600 (provisional test sizes, not approved prototype geometry). Include expanded/collapsed navigation, long labels/content, keyboard open, and text scale 1.0/1.5/2.0. Final reference-native sizes must be added when artifacts arrive.

- [ ] No overflow, clipped composer/buttons or whole-screen horizontal scrolling; long transcripts/files remain usable. Mobile uses adaptive layout, not scaled desktop.
- [ ] Keyboard reaches navigation, New Chat, Copy, model selector, attachments, actions and Settings; focus remains visible; Escape closes transient popovers; semantic names/selected/disabled states available; touch targets at least 44×44 logical pixels.
- [ ] Text contrast ≥4.5:1 for ordinary text; status/control boundaries ≥3:1; status not color-only. Measure actual token combinations, including light-theme links and disabled controls. Animations respect reduced motion.
- [ ] Compact → Workspace → Compact preserves exact session/turn IDs, unsent text, selection/attachments, model override, pending approval and in-flight response. One request per send. Expand opens Chat. Repeat after navigating Tasks/Settings and after resize/rotation.
- [ ] Theme/sidebar settings survive relaunch; unknown/old preference values recover deterministically; local-only scope explicit. Switching themes changes no navigation, session, permissions or capability availability.

## Regression and sign-off

- [ ] Capture pre-edit dirty baseline; compare only batch-owned diff; preserve M31/unrelated work. Test failures classified with reproducible baseline evidence.
- [ ] Each batch runs specified targeted tests and records runtime checks, then receives Claude read-only audit and Codex repair where required.
- [ ] Final Flutter analysis/full test suite, Python full regression and canonical-loop/approval/isolation checks recorded with exact command, versions, counts and logs; no unresolved new regressions.
- [ ] Claude pre-final audit complete; User live acceptance explicitly recorded; Codex repair if required; Claude final audit complete. Missing platform/runtime evidence remains NOT RUN, never PASS.
- [ ] Release checkpoint recorded only after authorized Claude commit/push. No production implementation or release is claimed by these planning files.
