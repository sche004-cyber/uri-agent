# Reference-clarification card (M33.3-R S12) — 2026-09-27

**Status:** implemented fixture-backed only (`uri_ui/lib/widgets/clarification_card.dart`, `uri_ui/lib/models/clarification.dart`). Not placed in any screen and not connected to the backend; production integration is S13. Selected by the implementer inside the frozen S1 contract; the independent M33.3 closing audit and the User may revisit the visual treatment.

**Backend capability (step 1).** The frozen S1 contract (`uri_v1/turn/rar_clarification_contract.py`): kinds `CHOOSE_ONE`, `CONFIRM_ONE`, `CHOOSE_ATTRIBUTE`, `FREE_INPUT_ONLY`; at most 5 options (`MAX_OPTIONS`); slot keys `s*` for candidates and `a*` for attribute values; `ESCAPE_LABEL` appended by URI; responses `CANDIDATE` (candidate_id + fingerprint), `ATTRIBUTE` (option_key), `FREE_INPUT` (text). No `/ask` field carries this today.

**Reference structure (steps 2, 5).** `docs/design_library/chat/README.md` requires the chat stream to leave room for an inline decision card, which the reference repos do not model; URI's own inline decision block (`TurnCard` `_ProposalBlock`, `uri_ui/lib/widgets/turn_card.dart:396`) is the structure reused. Quick-reply chips (Kiranism chat, `DESIGN_INDEX.md` `screenshots/kiranism_chat.jpg`) are the pattern for the `a*` attribute filters.

**Mapping (step 6).** Question text → body line; candidates → full-width outlined option buttons in RAR rank order (no padding beyond the grounded set); `a*` options → "Filter by <axis>" chips; escape → text button that opens a free-input field; free input → "Use this" button; after any answer the card locks and shows "Using: …".

**Invariants tested.** Clicks emit candidate IDs and the fingerprint, never labels; malformed or over-cap cards fail closed; free input is emitted verbatim (trimmed) as the authoritative answer. Emitted payloads are replayed through the frozen S1 `BindingService` (`tests/test_m33_3_r_s12_fixture_bridge.py`).

**Not decided here.** Placement inside the Chat workspace, compact-mode treatment, and the Change affordance on a tentative binding ("Using X · Change") belong to S13 integration.
