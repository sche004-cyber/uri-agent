# M28: Consent-Aware Passive Memory Candidate Pipeline

## Status: ACCEPTED (auto-approved per ORCHESTRATION.md §1.5, 2026-09-12)

## Origin

User accepted the M27-adjacent explicit-disclosure fix (capability_planner
+ provider_semantic_interpreter, 2026-09-12) and explicitly asked for a
follow-on, NOT unrestricted always-on profiling: URI should gradually
build useful context from ordinary conversation without requiring trigger
phrases, while keeping most of what's said out of durable storage.

## Investigation findings (why this was left unbuilt, and what already exists)

`uri_core/core/user_memory.py`'s own module docstring already answers the
"why unbuilt" question directly: `MemoryStore.propose()` and `.confirm()`
were built and tested in an earlier milestone, but nothing has ever called
`propose()` from a live conversation - that requires "URI/the model
noticing something during a live conversation and proposing it, which is
explicitly deferred to a later, separately-reviewed milestone (touching
orchestrator.py)". This is that milestone.

What already exists and needs zero changes:
- `MemoryStore.propose()` - writes `consent="pending_confirmation"`,
  `fact.status="PROVISIONAL"`, `fact.source="uri_proposed"`.
- `MemoryStore.confirm()` / `POST /memory/{id}/confirm` - user accepts (with
  optional correction), consent flips to `user_confirmed`, `status`
  becomes `CONFIRMED`.
- `POST /memory/{id}/reject` - discards a pending entry.
- `is_eligible_for_personalization()` / `personalization_context.py` -
  already the single, tested gate that excludes every
  `pending_confirmation` entry from ever influencing a response. This is
  the hard safety boundary the whole design leans on, and it does not
  need to change.
- Flutter already has a working Confirm/Reject review UI for pending
  entries (`test_m18_history_memory_test.dart`).
- `Fact.source` is a free `Optional[str]` (no enum/schema constraint) -
  new provenance values need no migration.
- `ConversationHistoryStore.get_session(session_id)` already gives
  per-turn recent conversation (user text + response), the natural input
  for a passive extractor - no new storage needed for "recent context".
- Session-scoped, non-durable facts already have a home distinct from
  `MemoryStore`: `uri_core/core/facts.py` / `fact_manager.py` (task-
  execution facts, explicitly described in `user_memory.py`'s own
  docstring as the place for things that "stay session-scoped").

So this milestone adds exactly one new thing: a bounded, deterministic-
first classifier that decides, per turn, whether to call an *existing*
API (`propose()`, a session-scoped `Fact`, `update()`, or nothing) - never
a new storage tier, never a new confirm/reject surface, never a change to
what personalization is allowed to read.

## Architecture

```
user message
  -> ConversationHistoryStore recent turns (already exists)
  -> explicit-disclosure detector (already exists, 2026-09-12 fix, UNCHANGED)
       -> matched: existing remember_fact path (UNCHANGED)
       -> not matched: passive_memory_pipeline.evaluate(...)  [NEW]
            -> deterministic pre-filter (cheap, no model call)
                 -> no durable-seeming signal: return, nothing stored
            -> bounded classification call (existing model provider infra)
                 -> category 1 (shouldn't reach here; explicit path already caught it)
                 -> category 2 (durable preference/context, high confidence)
                      -> dedup/refinement check against existing entries
                      -> MemoryStore.propose(..., source="passive_candidate")
                           OR MemoryStore.update(existing_id, ...) if superseding
                 -> category 3 (temporary/session fact)
                      -> session-scoped Fact only (facts.py/fact_manager),
                         source="session_context" - MemoryStore untouched
                 -> category 4 (ambiguous inference)
                      -> discarded, nothing stored, nothing returned
                 -> category 5 (sensitive)
                      -> discarded by default (never silently promoted);
                         existing security_guards.looks_like_credential_value
                         plus a new coarse sensitivity heuristic (health,
                         financial, legal, political/religious topics)
```

New module: `uri_core/core/passive_memory_pipeline.py`. `orchestrator.py`
gains exactly one call site (fire-and-forget, after the turn's response is
already decided - never blocks or branches the reply), consistent with the
standing "orchestrator.py must never grow" rule: the logic lives in the
new module, not inlined.

## Classification taxonomy (maps directly to the User's 5 examples)

1. **Explicit durable disclosure** ("I work at NIT Sikkim") - already
   handled by the existing, just-fixed explicit-disclosure path. This
   pipeline never sees these turns (the detector runs first).
2. **High-confidence durable preference/context** ("I usually prefer
   short official notes...") - `propose()`, source `passive_candidate`,
   surfaces in the existing pending-review UI. Never auto-confirmed.
3. **Temporary/session fact** ("I'm working from home today") - written
   only as a session-scoped `Fact` (existing mechanism), never touches
   `MemoryStore`, naturally does not outlive the session.
4. **Ambiguous inference** (repeated hiking mentions, never stated as a
   preference) - explicitly not stored anywhere. The pre-filter and
   classifier are both biased toward silence on this category; the
   classification prompt is a narrow yes/no/unsure with unsure -> discard.
5. **Sensitive information** - never silently promoted regardless of
   confidence. A sensitive-topic heuristic runs before category 2/3
   storage and, if it matches, the candidate is dropped rather than
   proposed - never appears even as `pending_confirmation` unless the
   user disclosed it explicitly (which is the unchanged, already-consent-
   inherent explicit path).

## Recency / no-override guarantee

This pipeline is write-only with respect to durable memory - it never
changes how or when `personalization_context.py` reads memory into a
turn, and never changes the existing recency-priority prompt guidance in
`model_reasoning_adapter.py` (reinforced earlier this session: latest
user turn and recent action results outrank older memory). Because
`pending_confirmation` entries are already excluded from
`is_eligible_for_personalization()`, a passive candidate literally cannot
influence a future response before the user confirms it - the "old memory
must never override the current topic" requirement is therefore already
structurally satisfied for everything this milestone adds; it only
becomes a live concern for `user_confirmed` memory, which is unchanged,
existing, already-covered behavior.

## Dedup / refinement

Before calling `propose()`, check existing entries (both consent tiers)
in the same `category` for a near-duplicate or superseding relationship
(normalized substring/keyword overlap against `fact.value` - no new NLP
dependency). Three outcomes:
- No related entry: `propose()` a new one.
- An existing `pending_confirmation` entry already covers it: skip,
  don't create a second pending duplicate.
- An existing `user_provided`/`user_confirmed` entry on the same subject
  is superseded (e.g. a new workplace): call `MemoryStore.update()` on
  that entry rather than adding a new one - the User's own explicit
  instruction ("use the existing memory refinement/update mechanism").

## Provenance

`Fact.source` gains new values (no schema change - it is already a free
string): `passive_candidate`, `session_context`. `tool_result` is
reserved for a later milestone (facts derived from an action result, not
the user's own words) - out of scope here. Small additive API change:
`_memory_entry_to_dict` in `server.py` currently drops `fact.source`;
add it so the client can label provenance ("you told me" vs "URI
noticed"). Purely additive (new response key), no existing contract
changes.

## Non-goals (explicit)

- No change to the just-fixed explicit-disclosure path.
- No change to `personalization_context.py`'s read-side filtering.
- No new storage backend, no new confirm/reject surface.
- No auto-confirmation of any passive candidate, ever.
- No persistence of category 4 (ambiguous inference) under any
  confidence threshold.
- No expansion of `orchestrator.py` beyond one call site.
- No UI redesign - the existing pending-review screen gains a provenance
  label only.

## Cost / noise control

A cheap deterministic pre-filter runs on every turn (regex/heuristic,
no model call) and only turns that pass it reach the classification
call - addresses "normal conversation does not create excessive memory
entries" directly, and keeps this from becoming a per-message LLM tax.

## Required tests (mapped to the User's list)

- `test_passive_memory_pipeline.py` (new): explicit disclosure still
  bypasses this pipeline entirely; a clear embedded preference produces
  exactly one `propose()` candidate; a temporary fact produces a
  session-scoped `Fact` and zero `MemoryStore` entries; an ambiguous
  repeated-topic conversation produces nothing; a sensitive disclosure
  is never silently promoted; duplicate facts across turns do not
  accumulate; a superseding disclosure calls `update()` not `add`/
  `propose`; a normal multi-turn conversation with no durable signal
  produces zero entries.
- Existing `test_capability_planner.py`, `test_provider_semantic_
  interpreter.py`, `test_remember_fact.py` - re-run unchanged, must stay
  green (proves the explicit path is genuinely untouched).
- Server-level: `_memory_entry_to_dict` now includes `source` - update/
  add a test asserting old clients still work (additive key only).

## Release gate (unchanged)

Same as M27: Claude does not commit/push this work until the User has
personally live-verified it and given explicit direction to do so.

## History log

- 2026-09-12: Drafted and marked ACCEPTED by Claude under the standing
  auto-approval rule, per the User's explicit request to investigate and
  plan before implementing. Not yet implemented - awaiting the User's
  direction on whether Claude implements this directly (as with the
  explicit-disclosure fix) or it routes through Antigravity/Codex per
  the standing AO-4 process for substantial/architectural work.
