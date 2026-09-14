# Architecture Proposal — Relevance-Scoped Memory & Context Retrieval

**Status:** ARCHITECTURE PROPOSAL — not a milestone plan, not implementation.
No acceptance criteria, no test plan in the AO-4 sense; this document exists
to settle the *shape* of the problem before any milestone plan is drafted.
**Author:** Claude Code (Planner)
**Baseline:** M22.3, commit `8acbad5`. M22.4 is `ACCEPTED` and currently
`FIXING` under Antigravity's audit — **this document changes nothing about
M22.4** and assumes it completes independently.
**Grounding:** every claim about current behavior below is cited to actual
source (file:line), verified by direct inspection, not recalled from an
architecture doc. Where the repo is silent or a path is dormant/unwired,
that is stated explicitly rather than assumed.

---

## 0. The objective, restated from the User's brief

URI must stop growing the Brain's active working context in proportion to
how much durable state (memory, conversation, experience, evidence) a user
accumulates. Durable state stays external and persistent; the Brain sees
only a small, **relevance-selected** (not merely recent or fixed-size)
slice of it per turn, filtered through existing provenance/consent/status
gates, assembled deterministically, never auto-promoted back into durable
storage, and built on the existing M18/M21 stores rather than replacing
them. The goal is relevance and efficiency — not a bigger context window.

---

## 1. Current state, as it actually is today

This is the factual baseline every section below builds on.

### 1.1 The assembly pipeline today

`orchestrator.py`'s per-turn flow builds each `query_context.py` section
independently, then calls the pure assembler:

```
build_query_context(policy_text, soul_text, personalization, session_context,
                     verified_facts, capabilities, diagnostics, experience,
                     attachments, conversation) -> Dict[str, Any]
```

(`query_context.py:84-95`). It returns a fixed 9-key dict — `identity, soul,
personalization, session, verified_facts, capabilities, diagnostics,
experience, attachments, conversation` (`query_context.py:179-197`) — and
does **no filtering or bounding itself**; it only degrades a missing
section to empty (`query_context.py:172-174`). All selection and bounding
happens in the callers that build each section's input, before this
function ever sees it.

### 1.2 What each section's selection logic actually is today

| Section | Source | Selection today | Bound today |
|---|---|---|---|
| `personalization` | `personalization_context.build_personalization_context` | consent-eligible only (`is_eligible_for_personalization`), then sorted by `updated_at` descending | `MAX_MEMORY_ENTRIES = 10` (`personalization_context.py:42,89-99`) |
| `verified_facts` | `evidence_context.get_verified_evidence` | `fact.status == "VERIFIED"` only | none beyond that filter (`evidence_context.py:4-22`) |
| `experience` | `experience_store.summarize_for_query_context(store.recent(limit=5))` | most-recent 5, no ranking | `MAX_EXPERIENCE_CONTEXT_TOKENS = 300` via `fit_within_budget` (`orchestrator.py:93`) |
| `conversation` | `orchestrator._build_conversation_context` | last `MAX_CONVERSATION_TURNS_CONSIDERED = 20` turns, no ranking | `MAX_CONVERSATION_CONTEXT_TOKENS = 500` (`orchestrator.py:94-95,3048,3060-3061`) |
| `capabilities`/`diagnostics` | registry/audit trail | not memory — out of scope here | n/a |

**Every selection rule wired into the live path today is recency-and/or-
consent-based. None is relevance-based.** A `ContextBudget` class exists
(`context_budget.py:111-317`) that does keyword-overlap scoring, but it is
**never instantiated anywhere in the codebase** (confirmed by a repo-wide
call-site search) — its own module comment says it "stays unwired per the
M20 decision" (`context_budget.py:13-16`). A second keyword-taxonomy
function, `evidence_context.get_relevant_evidence`, also exists and is also
explicitly never used for Brain context per `query_context.py`'s own
docstring (`query_context.py:31-38`) — only `get_verified_evidence` is used.
**Both of the repo's existing relevance-scoring attempts were built and
then deliberately left disconnected.** Any new design should ask why
before reusing their shape wholesale.

### 1.3 `context_budget.py`'s actual contract

- `estimate_tokens(text)`: `len(text)//4`, a rough proxy, not a real
  tokenizer (`context_budget.py:19-25`).
- `fit_within_budget(items, max_tokens, item_estimator=None)`: caller must
  pre-order items most-important-first; returns the longest leading prefix
  that fits; always keeps at least one item even if oversized
  (`context_budget.py:28-67`). **It makes no judgment about what an item
  is — only whether the already-ordered list fits** (its own docstring,
  lines 35-37).
- `bound_json_value(value, max_chars=800)`: returns the value unchanged if
  small enough, else a `{"_truncated": True, "preview": ...}` stand-in
  (`context_budget.py:70-90`).
- There is **no single global prompt-budget ceiling** — every section is
  bounded independently against its own constant; nothing sums them
  against one total.

### 1.4 The durable stores and their real status/consent model

`server.py::_build_user_context(user_id)` builds exactly **9 per-user
stores**, each via `portable_paths.user_scoped_path(user_id, ..., root=
"uri_workspace/users")` (`server.py:233,256-339`): `profile_store,
memory_store, growth_ledger_store, approval_store, session_manager,
experience_store, skill_memory, conversation_history, file_store`. Of
these, only `memory_store, session_manager, experience_store, file_store,
conversation_history`, plus evidence attached to the session and the
capability registry, actually feed the live Brain-facing query context.
`growth_ledger_store` and `approval_store` are explicitly **not**
Brain-facing (growth is cosmetic XP, approvals are execution-path state).

- **`MemoryStore`** (`uri_core/core/user_memory.py`): `consent ∈
  {"user_provided", "user_confirmed", "pending_confirmation"}`
  (line 62-66); `is_eligible_for_personalization` is exactly `consent in
  {"user_provided", "user_confirmed"}` (line 134-140). `propose()` creates
  `pending_confirmation`/`fact.status="PROVISIONAL"`; `confirm()` flips to
  `user_confirmed`/`"CONFIRMED"` (lines 208-309). This consent gate is the
  one invariant everything downstream must never bypass.
- **Facts** (`facts.py:6-13`): `status ∈ {CONFIRMED, VERIFIED, PROVISIONAL,
  HISTORICAL, SUPERSEDED, EXPIRED}`. `SUPERSEDED` is actively set by
  `fact_manager.py` when a fact is replaced (lines 49,76,141,167).
  **`EXPIRED` is declared in the enum but no code path ever sets it** — it
  is currently dead. This gap predates this proposal and is not something
  retrieval should invent a fix for; retrieval should simply exclude
  non-`VERIFIED` statuses exactly as today's filter already does, and this
  document names the `EXPIRED` gap so it is not silently assumed solved.
- **Skill memory** (`uri_core/core/skill_memory.py`): `confidence =
  successes/(successes+failures)`, default 1.0; `CONFIDENCE_RECALL_FLOOR =
  0.34` below which a skill is never recalled, though never deleted
  (lines 16,102-120). **Not currently part of `query_context.py`'s 9 keys
  at all** — it's consulted separately for skill recall. Out of scope for
  this proposal unless the milestone plan later decides to fold it in.

### 1.5 What this means for the objective

Points 1, 4, 6, 7 of the User's objective (external durable storage,
provenance/consent respected, no auto-promotion, reuse of M18/M21 stores)
are **already true today** — they're the existing architecture, not a gap.
The actual gap is narrower than "build external memory": it is specifically
points 2, 3, 5, 9 — **selection is recency/consent-based, never
relevance-based, and nothing bounds the *total* context across sections.**
This sharply scopes what the new milestone actually needs to add.

---

## 2. What information is eligible for retrieval

Eligibility is a **strict pre-filter**, applied before any relevance
scoring, reusing the exact gates that already exist — retrieval never
operates over a raw, unfiltered store:

- Memory entries: `consent ∈ {"user_provided", "user_confirmed"}` only
  (today's `is_eligible_for_personalization`, unchanged).
- Facts/evidence: `status == "VERIFIED"` only (today's
  `get_verified_evidence`, unchanged) — `PROVISIONAL`, `HISTORICAL`,
  `SUPERSEDED`, and (once it exists) `EXPIRED` are never eligible.
- Experience records: all of them are already Brain-written/Brain-gated
  (via the acceptance-retention step), so no additional consent gate is
  needed beyond existing category/shape validation.
- Conversation turns: all turns in the current user's own history are
  eligible by definition (they are this user's own verbatim exchanges);
  eligibility here is really about relevance ranking, not a consent gate.
- Skill memory: explicitly **out of scope** for this proposal's eligible
  set unless a future milestone plan folds it in — it has its own recall
  mechanism (`CONFIDENCE_RECALL_FLOOR`) that already does something
  relevance-adjacent and is not part of `query_context.py` today.

**Non-negotiable:** the new relevance-scoring step must re-apply these
filters itself rather than trusting an upstream caller to have applied
them — defense in depth, so a future code path that forgets the old filter
still can't leak unconfirmed memory or non-`VERIFIED` facts through the
new one (see §9).

---

## 3. How relevance is determined

**This section states required properties, not a chosen algorithm** — per
the User's instruction not to design implementation yet, the actual
scoring method is a decision for the milestone plan, informed by real
measurement, not fixed here.

Required properties of whatever scoring function is eventually chosen:

1. **Deterministic.** Same `(user_id, task_signal, store_state)` input
   always produces the same selected set and ordering — no model call
   inside the retrieval step itself (consistent with `context_budget.py`'s
   existing purely-deterministic design, and necessary for the
   determinism invariant in §11).
2. **Computed from the current turn's task signal** — the user's message
   text, the active session/capability context — against each eligible
   item's own existing metadata (category, fact subject, session linkage,
   turn content), not a fixed "last N" slice and not the whole store.
3. **Bounded cost**, independent of how large the underlying store has
   grown — a user with 10,000 experience records must not make retrieval
   scan-and-score in a way that grows unbounded with store size (see §8
   for how storage/indexing addresses this).
4. **Explainable/auditable** at the level `diagnostics` already is today
   — it should be possible to answer "why was this item retrieved" for
   debugging, even if that reasoning isn't shown to the end user.

Two relevance-scoring kernels already exist in the repo and were
deliberately left unwired: `ContextBudget`'s keyword-overlap scorer
(`context_budget.py:111-317`) and `evidence_context.get_relevant_evidence`'s
keyword taxonomy (`evidence_context.py:25-117`). The milestone plan should
explicitly decide whether to rehabilitate one of these, replace them, or
delete them as dead code — this proposal does not pre-decide that, but
flags that "a relevance scorer" is not a blank slate in this repo; two
already exist and were rejected or shelved once.

---

## 4. Where retrieval occurs in the Brain/context pipeline

`query_context.build_query_context()` itself **stays a pure, untouched
assembly function** — it must not gain store access or filtering logic.
Retrieval is a new stage inserted exactly where size-bounding already
happens today: inside the per-section builder functions that currently
call `store.recent(limit=5)` or slice the last 20 turns
(`orchestrator._build_conversation_context` and its siblings).

Concretely, a new stage sits **between the durable store and the existing
`fit_within_budget`/`bound_json_value` calls**:

```
durable store (full history)
     │
     ▼
[NEW] relevance selection  ← eligibility filter (§2) + relevance scoring (§3)
     │  (produces a small, ranked candidate list)
     ▼
context_budget.fit_within_budget / bound_json_value  ← UNCHANGED
     │  (existing size-based bounding, now operating on a pre-curated list)
     ▼
query_context.build_query_context()  ← UNCHANGED
```

This preserves the existing separation of concerns: retrieval narrows by
*relevance*, `context_budget.py` still narrows by *size*, and
`query_context.py` still only assembles. No existing module's contract
changes; a new module (name TBD in the milestone plan — e.g.
`memory_retrieval.py`) is added and called from the same orchestrator
methods that already do per-section assembly.

---

## 5. How provenance and confirmation status are preserved

Retrieved items must carry their **original store fields through
retrieval unchanged** — `MemoryEntry.consent`/`category`,
`Fact.status`, `ExperienceRecord` fields, `ConversationTurn` fields —
never flattened into prose before eligibility is checked. Filtering
happens on the structured record, before formatting for the Brain, not by
pattern-matching already-formatted text afterward. This is not a new
provenance model: retrieval is strictly an additional filter-and-rank pass
*downstream* of the filters that already exist (§2), never a replacement
for them, and never an alternate path that reads a store's raw file
directly instead of going through the store's own accessor methods.

---

## 6. How stale/superseded/expired information is handled

- `SUPERSEDED` facts are excluded by the same eligibility gate as
  non-`VERIFIED` facts generally (§2) — no separate handling needed.
- `EXPIRED` is currently dead code (no writer exists, §1.4). This proposal
  recommends the retrieval milestone **exclude it from eligibility exactly
  like the other non-`VERIFIED` statuses** (cheap, consistent, and
  future-proofs the gate for whenever a writer is eventually added) but
  explicitly **not** take on building the expiry-writing logic itself —
  that is a `fact_manager.py` concern, named here so it is not silently
  assumed to be in scope.
- Conversation turns and experience records have no staleness status
  field today, and none is proposed — recency already degrades their
  presence (old turns physically drop past `MAX_TURNS_PER_SESSION`), and
  relevance scoring (§3) should naturally deprioritize a stale-but-still-
  stored item because it no longer matches the current task signal,
  without needing a new explicit expiry flag on these record types.

---

## 7. How retrieval interacts with `context_budget.py`

No change to `context_budget.py`'s bounding algorithm. Retrieval produces
the *candidate* list (relevance-ordered, already small); `fit_within_budget`
still does the final size-based cut using that same ordering as its
"most-important-first" input, and `bound_json_value` still truncates any
individual oversized item. Retrieval and budget-fitting are two distinct
narrowing passes with two distinct jobs — relevant vs. fits — and neither
replaces the other. The dormant `ContextBudget` class and
`get_relevant_evidence` function (§3) are not proposed for reuse as-is;
whether to revive, repurpose, or delete them is an open decision for the
milestone plan, not settled here.

---

## 8. How much state should remain in the active working context

The working context's *shape* (the same 9 `query_context.py` keys) does
not change. The point of this milestone is to improve what is *selected*
into the existing per-section ceilings, not to raise them. One concrete
improvement this proposal does recommend for the milestone plan to define:
introduce a single **total** prompt-budget ceiling that the sections
compete for (today, §1.3 confirms no such ceiling exists — each section is
bounded independently and nothing sums them), so a future new section
can't silently grow total context size by staying within its own limit
while the aggregate keeps climbing.

---

## 9. Storage/indexing requirements

No new database, broker, or cache server — this stays consistent with the
standing M22 architecture rule against such dependencies
(`URI_M22_ARCHITECTURE.md` §11.3, "no database, no broker, no cache
server"). Given every relevant store's size is already bounded at write
time (`MAX_TURNS_PER_SESSION=200`, `MAX_MEMORY_ENTRIES=10`,
`experience_store.recent(limit=5)`, etc.), a full in-memory scan-and-score
at request time is very likely sufficient and is the simplest option —
no embedding/vector index is required to meet the stated objective, and
none is proposed. If a future milestone plan finds real latency pressure
that changes this, a lightweight *derived* index (e.g. a small per-user
keyword/category index file, rebuildable from the durable store) is the
fallback — never the sole copy of the information, and never itself the
source of truth. This is explicitly left as an implementation decision,
not fixed here.

---

## 10. Portability implications

Any new per-user derived file (should one turn out to be needed per §9)
must go through `portable_paths.user_scoped_path` exactly like the 9
existing stores (`server.py:233,256-339`) and must **never** be keyed by
`device_id` — `portable_paths.py` deliberately excludes device identity
from its path contract (`portable_paths.py:14-16`) and this must not be
reintroduced. Relevance scoring must not depend on a machine-specific
model or service (e.g. a local-only embedding model) as its only path —
whatever scoring approach the milestone plan picks must degrade
gracefully or run identically on any machine URI is installed on, per the
User's portability requirement (point 8) and consistent with the
previously-recommended Portability & Packaging Foundation milestone's "no
environment-specific configuration hardcoded" direction. Any derived index
must be fully rebuildable from the durable store alone, so moving machines
or reinstalling loses nothing but a trivially-regenerated cache.

---

## 11. Security/privacy implications

- Retrieval must re-apply the consent/status eligibility gates itself
  (§2) rather than trusting an upstream caller — defense in depth against
  a future code path leaking unconfirmed memory or non-`VERIFIED` facts.
- Retrieval is always scoped to exactly one `user_id`'s own store
  instances (the same ones `_build_user_context` already builds) — no new
  shared or global index across users.
- Retrieval is **read-only** with no new write path back into
  `MemoryStore`/`ExperienceStore`/any durable store — this makes the
  User's point 6 ("the Brain may reason over retrieved material but must
  not promote it into durable memory automatically") a literal security
  invariant, not just a behavioral guideline: promotion to durable memory
  stays exactly where it is today (the explicit Brain-gated
  `propose()`/`confirm()` flow and the orchestrator's existing acceptance-
  retention step), and the new retrieval module should be provably
  incapable of calling any store's write methods — enforceable with the
  same AST import-boundary technique already used for the capability/
  approval authority boundary (`test_capability_authority_boundary.py`).

---

## 12. Testable invariants

1. Retrieval never returns a memory entry with `consent ==
   "pending_confirmation"`.
2. Retrieval never returns a fact whose `status != "VERIFIED"`
   (explicitly including `SUPERSEDED` and, once it exists, `EXPIRED`).
3. Retrieval is provably scoped to one `user_id` — an isolation test in
   the same shape as M21's existing per-user isolation suite.
4. Retrieval has zero write-capable call paths to any durable store —
   an AST/import-boundary test, same technique as
   `test_capability_authority_boundary.py`.
5. Determinism: identical `(user_id, task_signal, store_state)` produces
   an identical retrieved set and ordering across repeated calls.
6. Scalability bound: seeding a store with a very large number of
   records (e.g. thousands of experience records or conversation turns)
   still produces a context whose assembled size stays within the
   defined ceiling (§8) — proving the bound holds independent of store
   growth, not just at today's small scale.
7. Degradation: an empty or missing store for any section still produces
   a valid, empty-for-that-section context rather than raising — this is
   the same pattern `query_context.py` already guarantees
   (`query_context.py:172-174`) and must not regress.
8. No module in the new retrieval path imports `ModelProvider`/
   `ModelRouter` — same AST technique already used to keep authority
   boundaries clean of provider identity (`URI_M22_ARCHITECTURE.md` §18.1
   invariant 1).

---

## 13. Does this deserve its own milestone, and what number

**Yes, its own milestone.** It is not a natural extension of any single
existing M22.x item — it touches a cross-cutting concern (every
Brain-facing store) rather than one subsystem, it introduces a genuinely
new kind of logic (relevance scoring) that nothing else in M22.1–M22.9
needs, and bundling it into another milestone would blur that milestone's
own risk profile, the same reasoning M22.4's own plan used to keep
packaging separate from authorization work.

**Dependency analysis:** this work depends only on the M18/M21 baseline
(memory/experience/conversation stores, `context_budget.py`,
`query_context.py`) — all already complete. It has **no dependency on
M22.4's `CapabilityResolver`, M22.5's provider registry, or M22.6's
`ModelRouter`**, and nothing in M22.5–M22.9 depends on it either. It is
schedulable independently of the rest of the M22.4→M22.9 chain.

**Proposed number: M22.10.** It is additive to the existing roadmap
(M22.1–M22.9 keep their numbers and order unchanged — nothing about
M22.4 or any other milestone in this document changes), placed after the
existing nine rather than renumbering anything. Given it touches
privacy-sensitive personal memory/evidence filtering directly, it should
be classified at the same **independent deep review** tier as M22.2/
M22.3/M22.4/M22.5 in `URI_M22_ARCHITECTURE.md`'s review table (§17.4) —
not the lighter implementation/test tier.

**Recommended scheduling (not a hard dependency, a judgment call):** draft
M22.10's actual milestone plan next, immediately after M22.4 reaches
`VERIFIED` — ahead of M22.5–M22.9 and ahead of the previously-recommended
Portability & Packaging Foundation milestone. Reasoning: every later
milestone's own testing and iteration benefits from a smaller, more
relevant working context sooner rather than later, and nothing is blocked
waiting for it — but this is a prioritization recommendation, not a
technical requirement, and the User may reorder it freely.

**Relationship to Portability & Packaging:** kept as a **separate**
milestone from Portability & Packaging (per the User's point 7 and the
same reasoning M22.4 §8 already established) — different risk profile
(context/memory correctness and privacy vs. build/distribution), and
M22.10's own portability implications (§10) are satisfied by following
the existing `portable_paths` convention, not by anything packaging-
specific.

---

**This document is an architecture proposal, not a milestone plan.** No
implementation should begin from it. The next step, if the User agrees
with the framing and numbering above, is a full M22.10 milestone plan
(scope, acceptance criteria, test plan, security considerations, UI
impact) drafted the same way M22.4's was — through AO-4 step 1, waiting
for ACCEPT/MODIFY before Gemma/Antigravity touch anything.
