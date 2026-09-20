# ARN — Adaptive Retrieval Narrowing & Task Recovery

**Status:** DRAFT → ACCEPTED (standing auto-approval, `ORCHESTRATION.md`
§1.5 — this is a planning artifact only; it authorizes no implementation,
touches no production code, and does not change URI's core project
structure, product identity, or security/authority model)
**Authorized by:** direct User instruction, 2026-09-20, immediately
following Claude's independent final closure of M33.2 — Edge / Second
Brain Foundation.
**Depends on (reused, not rebuilt):** M33.2 Batch B.4's qualification
verdicts (`docs/plans/M33_2_BATCH_B4_STATE.md`) — specifically, Needle 3's
`RESIDENT` reflex/structured-extraction scope and its explicit exclusion
from unrestricted argument extraction; the canonical USER/BRAIN/URI
interaction loop (see the pinned "uri-canonical-interaction-loop" record);
Graphify (`graphify-out/`) as an optional accelerator only.
**Implements no code.** This document is a plan. Batches below describe a
proposed sequencing for a future session to accept and route.

---

## 1. Purpose, and why this problem is real

URI today treats a failed lookup as a dead end rather than a decision
point. There is no `NOT_FOUND`/`EXHAUSTED` state machine anywhere in
`uri_core/core/` (confirmed by direct grep across `uri_core/core/*.py` and
`uri_core/services/*.py` at plan time — zero matches for either token).
When a search, a document scan, or a capability lookup comes up empty,
the Brain has no structured "what have I already ruled out, what do I try
next, is there a cheap clarifying question that would collapse the
remaining space" contract to draw on. It either escalates immediately or
retries the same action, both of which this project's canonical
interaction loop already identifies as the wrong response to a "try
again" signal — a rejection or failure must flow back to the Brain as
real evidence prompting further reasoning, not a mechanical retry.

ARN's purpose is to give URI (not the Brain) the deterministic
infrastructure to make that recovery cheap and evidence-based: track what
has been tried, what remains, and what a user could tell URI that would
shrink the remaining space, and hand all of that to the Brain as
structured evidence rather than a bare failure. The Brain still decides
what to do with it — ARN does not encode reasoning, task taxonomy, or a
scripted decision tree; it encodes bookkeeping and search-space state that
make the Brain's own reasoning cheaper and more likely to succeed.

### 1.1 Relationship to existing architecture (disambiguation)

This is deliberately **not** the same problem as
`docs/plans/M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md`. That document
governs how much of URI's durable state (memory, conversation, evidence)
is assembled into the Brain's per-turn context window — a context-budget
problem. ARN governs how URI searches an external or internal space
(documents, sources, capabilities) *during* a single task's execution
when the first attempt fails — a task-recovery problem. The two may share
primitives later (e.g., a candidate document surfaced by ARN could later
be summarized into `verified_facts`), but ARN does not modify
`query_context.py`, the nine-key context assembly, or any of M22's
selection/bounding logic. No conflict was found between this plan and
that architecture during review.

### 1.2 Canonical-loop compliance (binding constraint on every batch)

Per the pinned canonical-interaction-loop record, URI's role is to supply
context, capabilities, evidence, memory, and the safety/authorization
boundary; the Brain's role is understanding, reasoning, enquiry, and
choosing words. This constrains ARN's design in one specific, non-
negotiable way: **URI must never author the clarification question shown
to the user.** ARN computes *that* a clarification is warranted, *which*
candidates remain, and *what information* would most reduce the
remaining set (an information-theoretic recommendation: which axis of
ambiguity splits the candidate set most evenly) — but the literal
question text (e.g., "I found 20 recruitment-related items. Do you mean
Faculty, Non-Teaching, Project Staff, or Recruitment Rules?") is always
drafted by a real call to the Brain, exactly as every other user-facing
reply already must be. ARN hands the Brain a structured recommendation
(`suggested_axis`, `candidate_groups`, `why`); the Brain turns that into
words. This mirrors Needle 3's own qualified scope from B.4 — Needle may
propose a *tool call* deterministically, but may never be trusted to
generate unrestricted user-facing content unsupervised.

---

## 2. Core principles (from the User's brief, restated with grounding)

1. **`NOT_FOUND` is a recovery trigger, not a terminal answer.** A search
   or lookup returning empty enters an ARN recovery state rather than
   directly producing a Brain response of "not found." The Brain is still
   the one who decides when to stop trying (see §6, `EXHAUSTED`) — ARN
   only prevents URI from silently treating the first empty result as
   final before the Brain ever sees the option to keep going.
2. **Progressive narrowing using multiple evidence sources**, in order of
   cost (cheapest/most-deterministic first):
   - deterministic structure (known capability/document schemas, IDs,
     paths already known to URI);
   - search/index results (whatever search primitive the task already
     used — Gmail search, file search, a Connected Service query);
   - temporary working-memory (this task's own ARN state — see §4);
   - source/document metadata (filenames, titles, dates, page counts,
     sender, folder — cheap to read, expensive to skip);
   - previous unsuccessful search paths (never repeat a path already
     ruled out this task);
   - Edge intelligence (Needle 3, `RESIDENT` scope only — reflex
     routing/structured extraction over ARN's own candidate list, e.g.
     classifying which of N candidate filenames best matches a query
     term; never trusted for the final answer);
   - user institutional knowledge (a clarification answer, see §3);
   - Main-Brain evidence requests (§5).
3. **One high-information clarification question**, asked only when a
   user's institutional knowledge could materially reduce a large
   candidate set, and only after the cheaper deterministic/metadata
   sources above have already been tried. ARN never asks a clarifying
   question as a first resort — that would just move the "give up
   immediately" failure mode one step later.
4. **User clues become structured retrieval evidence** for the current
   task only — a clue narrows this task's `ARNState.candidates`; it is
   not written back into durable memory/personalization by ARN itself
   (that remains M18/M21's existing, separately-gated mechanism, if the
   Brain later chooses to remember it as a durable fact).
5. **ARN works without Graphify.** Every mechanism in this plan operates
   on live search/metadata/state, never on `graphify-out/`. Where a
   Graphify index exists and is fresh, it may be consulted as one
   additional, optional, cheap evidence source (it is itself a form of
   "deterministic structure") — but no ARN behavior may degrade,
   misfire, or become unavailable when Graphify is absent, stale, or
   disabled (`GRAPHIFY_HINT_ENABLED=0`, per M34's existing killswitch
   pattern).
6. **Temporary candidate maps**, scoped to one task/turn-chain, tracking:
   sources checked, candidates eliminated (with the reason), remaining
   candidates, user clues received, and the successful retrieval route
   once found (recorded for this task's own evidence trail, not as a
   durable cross-task index — that would be a Graphify-shaped
   responsibility, explicitly out of scope here).
7. **PDF search narrows progressively**: metadata → candidate documents →
   candidate pages → targeted extraction. Exhaustive full-text scanning
   of every page of every candidate PDF is an explicit late fallback, not
   a default.
8. **Cost/ambiguity ceiling**: when narrowing would require scanning more
   than a bounded number of candidates/pages (a configurable threshold,
   not hardcoded), URI tells the user why continuing is expensive or
   ambiguous and asks for one useful clue (year, source, document type,
   topic, likely page) rather than silently running an expensive scan.
9. **Edge case-packet contract** (§5): a compact, structured handoff Edge
   may prepare for the Main Brain when escalating, containing `USER_GOAL`,
   `VERIFIED_FACTS`, `USER_CLUES`, `CANDIDATES`, `ELIMINATED_PATHS`,
   `EDGE_DEDUCTIONS` (explicitly marked as deductions, never presented as
   fact), `SOURCES_CHECKED`, `UNRESOLVED_QUESTIONS`, `SOURCE_POINTERS`.
10. **Main Brain may return targeted evidence requirements**, which ARN
    then retrieves before re-escalating — a bounded loop, not unbounded
    back-and-forth (see §6 for the termination condition).
11. **A future small reasoner as ARN search strategist** — next-best-
    search-step, candidate elimination, best clarification-question axis
    (not its text — see §1.2), evidence sufficiency, and escalation
    decision. This role must be filled by a model qualified specifically
    on ARN/search-planning tasks, not assumed. Per M33.2 Batch B.4's own
    measured verdict, **Qwen2.5-0.5B-Instruct is `BYPASS / REDUNDANT`**
    (50% bounded-reasoning accuracy with substantive constraint/set-
    intersection errors, materially worse than the installed
    `qwen3.5:9b`/`gemma4:12b` Main-Brain controls) — it is explicitly
    **not** assumed suitable for this role. A future qualification batch
    must evaluate better small-reasoner candidates against ARN-shaped
    tasks specifically (next-step selection, candidate elimination,
    clarification-axis choice — a different task shape than B.4's
    general bounded-reasoning corpus), reusing B.1–B.4's existing
    benchmark/qualification harness pattern rather than building a new
    one.

---

## 3. Clarification-question mechanics

ARN computes a `ClarificationRecommendation` when, after the deterministic/
metadata narrowing sources in §2.2 are exhausted, more than one candidate
remains and at least one candidate attribute (a facet — category, date
range, document type, sender, folder, or similar) would split the
remaining candidates into materially smaller, non-degenerate groups. The
recommendation is computed deterministically (a straightforward candidate-
count-per-facet-value split, not a model call) and contains:

- `suggested_axis`: the facet with the best split (fewest/most-balanced
  resulting groups, ties broken toward the facet already present as
  cheap metadata).
- `candidate_groups`: the actual grouping, e.g. `{"Faculty": [...ids],
  "Non-Teaching": [...ids], "Project Staff": [...ids], "Recruitment
  Rules": [...ids]}`.
- `why`: the plain evidence — "found 20 recruitment-related items,
  splitting by category yields 4 non-degenerate groups."

This structure is hardened evidence, handed to the Brain as part of ARN's
existing evidence contract (§5). The Brain decides whether to ask, and
drafts the actual words — ARN never emits the question text itself (see
§1.2). If the user's reply names one of the `candidate_groups` keys (or
the Brain's own follow-up reasoning maps a free-text reply onto one), the
candidate set narrows to that group and ARN state records the clue.

---

## 4. Temporary candidate-map state shape

A per-task `ARNState`, held only for the lifetime of the task's turn-chain
(never persisted to durable memory/personalization; may be attached to the
existing session-scoped Turn State the same way `current_turn_attachments`
already is, per M34's precedent), tracking:

```
ARNState:
  task_goal: str                     # restated user objective
  sources_checked: [SourceRecord]    # what was queried/opened, when, result summary
  candidates: [Candidate]            # remaining, with per-candidate metadata
  eliminated: [(Candidate, reason)]  # never re-tried this task
  user_clues: [Clue]                 # structured, task-scoped only (§2.4)
  clarification_asked: bool          # at most one per narrowing round (§2.3)
  successful_route: Optional[Route]  # recorded once found, for this task's evidence trail
  cost_spent: CostAccumulator        # candidates opened, pages scanned, model calls made
```

This is new URI-owned state, not a new authority surface — it carries no
permission, credential, or execution capability of its own. It is pure
bookkeeping consumed by the existing decision/dispatch path exactly the
way `verified_facts` or `experience` already are.

---

## 5. Edge case-packet contract

When Edge intelligence (Needle 3, `RESIDENT` scope) is used to assist
narrowing (e.g., ranking candidate filenames against the query, or
proposing the next search term as a deterministic-schema tool call — never
free-text reasoning presented as fact), and the task then needs to escalate
to the Main Brain, ARN may assemble a compact case packet:

```
CASE_PACKET:
  USER_GOAL
  VERIFIED_FACTS
  USER_CLUES
  CANDIDATES
  ELIMINATED_PATHS
  EDGE_DEDUCTIONS        # explicitly labeled as deductions, never fact
  SOURCES_CHECKED
  UNRESOLVED_QUESTIONS
  SOURCE_POINTERS
```

This reduces Main-Brain context/token cost (one of §7's success metrics)
by replacing "here is everything" with "here is what's already known,
tried, and ruled out." The Main Brain may respond with a targeted
evidence requirement (e.g., "check whether any candidate mentions a
specific year"), which ARN retrieves before re-escalating (§2.10) — bounded
by the same cost ceiling as §2.8, and by the termination condition in §6.

`EDGE_DEDUCTIONS` must never be trusted as `VERIFIED_FACTS`. This
preserves B.4's own qualified-scope finding: Needle's role is proposal,
never unsupervised fact assertion, matching its excluded
argument-extraction scope exactly.

---

## 6. Termination: genuine `EXHAUSTED`, not silent give-up

ARN recovery ends in exactly one of three ways, and the Brain is informed
of which one occurred (this is the actual fix for "premature `NOT_FOUND`"
— not that URI never reports failure, but that it never reports failure
*before* trying the cheap recovery steps and *without* telling the Brain
what was tried):

1. **Found** — `successful_route` recorded, candidate(s) returned.
2. **User-narrowed-to-zero** — the user's own clue eliminates every
   remaining candidate; reported honestly as "your clue ruled out
   everything I found," not as a generic not-found.
3. **Genuinely `EXHAUSTED`** — every deterministic/metadata/Edge/user-clue
   avenue in §2.2 has been tried (or the cost ceiling in §2.8 was hit and
   the user declined or could not supply a useful clue) and no candidate
   satisfies the goal. ARN reports the full `ARNState` (sources checked,
   candidates eliminated and why, cost spent) to the Brain so the Brain's
   own final message can be specific and honest rather than a generic
   apology — again, the Brain drafts the words, ARN supplies the facts.

---

## 7. PDF / document search narrowing (§2.7 detail)

Reusing existing extraction primitives (`uri_core/services/pdf_reader.py`,
`file_extraction.py`, `evidence_processor.py` — confirmed present and
already used for Gmail-attachment evidence processing) under the ARN
narrowing discipline rather than a new extraction stack:

1. **Metadata pass** — filename, title/subject (if present in PDF
   metadata), page count, source (which search/folder produced it), date.
   Cheapest; always run first.
2. **Candidate-document narrowing** — rank/filter candidate documents by
   metadata + any deterministic query-term match against filename/title,
   before opening file contents.
3. **Candidate-page narrowing** — for a surviving candidate document,
   locate likely pages via a cheap pass (table of contents if present,
   heading/keyword scan) before full extraction.
4. **Targeted extraction** — run the existing PDF/evidence extraction
   only on the narrowed page set.
5. **Exhaustive scan (late fallback only)** — full-text extraction across
   every page of every surviving candidate, gated behind the §2.8 cost
   ceiling and, if the ceiling would be exceeded, behind a clarification
   question first.

No new PDF-parsing library is proposed. This batch, if accepted, changes
*ordering and gating* of existing extraction calls, not the extraction
mechanism itself.

---

## 8. Explicit non-goals for this plan (hooks preserved, not built)

Per direct User instruction, the following are named as future extension
points this plan's data shapes must not foreclose, but are **not**
designed or implemented here:

- Cascading interaction layers: API → website → browser → desktop →
  human interaction escalation chains.
- `WAITING_FOR_HUMAN` / `RESUMING` workflows (distinct from, but
  naturally composable with, the existing `WAITING_FOR_MODEL` AO-4
  workflow-state pattern already implemented in
  `scripts/dev_workflow/state_machine.py` for an unrelated purpose —
  development-loop orchestration, not user-facing task execution; ARN
  must define its own state names rather than overload that
  development-tooling enum).
- Authenticated-site interaction, OTP/CAPTCHA/user checkpoints.

`ARNState`'s shape (§4) is deliberately a plain, serializable record with
no hardcoded assumption that a task completes in one turn, so a future
`WAITING_FOR_HUMAN`/`RESUMING` extension could attach to it without a
breaking redesign — but building that attachment point beyond "don't paint
ourselves into a corner" is out of scope for this plan and must not be
implemented under it.

---

## 9. Success metrics (measurable, per the User's brief)

A future qualification/benchmark batch (reusing the M33.2 B.1–B.4 harness
discipline: frozen corpus, SHA-256-manifested fixtures, before/after
comparison against a "no-ARN" control) must measure:

1. **First-search failure recovery rate** — % of tasks where the first
   search attempt fails but ARN recovery still reaches a correct result.
2. **Final task completion rate** — overall, ARN vs. no-ARN control.
3. **Correct-source retrieval rate** — did the final answer come from the
   actually-correct source, not merely *a* source.
4. **Candidate-set reduction** — average candidates eliminated per
   narrowing step (measures whether narrowing is doing real work).
5. **Wasted searches/documents opened** — candidates opened that did not
   contribute to the final answer (measures over-searching).
6. **Useful clarification rate** — % of clarification questions asked
   that the user's answer actually narrowed the candidate set (measures
   whether ARN is asking good questions, not just any question).
7. **Main-Brain invocation reduction** — fewer escalations to the Main
   Brain for tasks ARN/Edge resolve deterministically or via Needle's
   qualified scope alone.
8. **Main-Brain context/token reduction** — case-packet size vs. a naive
   "dump everything" escalation, for tasks that do escalate.
9. **Genuine `EXHAUSTED` rate** — % of failures that reach real
   exhaustion (all avenues tried) vs. premature failure (the defect this
   whole capability exists to eliminate) — measured by comparing against
   a manually-audited sample of "should this have found something."
10. **Latency/cost impact** — wall-clock and model-call cost of ARN
    recovery vs. the value recovered (recovery must not become more
    expensive than the task is worth; ties into the §2.8 cost ceiling).

---

## 10. Proposed batch sequencing (for a future session to accept)

Following the M33.2 batch discipline (small, reversible, independently
audited, additive) rather than one large implementation:

- **Batch ARN.1 — Deterministic narrowing core.** `ARNState` (§4), the
  `NOT_FOUND`-as-trigger seam in the existing dispatch/execution path
  (a hook only — no new authority), source/candidate/elimination
  tracking, and the §2.8 cost ceiling. No Edge, no clarification
  question, no case packet yet. Fully testable without any model call.
- **Batch ARN.2 — PDF/document progressive narrowing (§7).** Reorders
  existing extraction calls behind the metadata → candidate-document →
  candidate-page → targeted-extraction → exhaustive-fallback sequence.
- **Batch ARN.3 — Clarification-question recommendation (§3) +
  canonical-loop wiring.** The deterministic `ClarificationRecommendation`
  computation, and the seam handing it to the Brain for question-drafting
  (never URI-authored text — §1.2 is a hard gate on this batch's
  acceptance criteria).
- **Batch ARN.4 — Edge case-packet contract (§5) + small-reasoner
  qualification.** Wires Needle 3 into its already-`RESIDENT` scope for
  candidate ranking/next-step proposal only; qualifies a small-reasoner
  candidate specifically on ARN/search-planning tasks (not assuming
  Qwen2.5-0.5B) before any reasoner is used as the "ARN search
  strategist."
- **Batch ARN.5 — Success-metric benchmark harness (§9)** and the closure
  comparison against a no-ARN control.

No batch above is authorized by this plan alone; each still requires its
own DRAFT→ACCEPTED cycle (or standing auto-approval where it qualifies)
before implementation, per this project's standing AO-4 process.

---

## 11. Self-review against the Verification-First standard

**Acceptance criteria used for this review:** does the plan (a) restate
the User's brief completely and accurately, (b) ground every architectural
claim in checked primary evidence rather than assumption, (c) respect
already-decided standing constraints (canonical interaction loop, M33.2's
qualification verdicts, zero-egress/authority boundaries), (d) avoid
scope creep into implementation or into the explicitly-deferred
interaction layers, and (e) disclose anything unverifiable.

**Gaps found and repaired before acceptance:**
- First draft did not explicitly reconcile ARN with the existing M22
  memory/context-retrieval architecture; a reader could reasonably ask
  whether these overlap or conflict. Repaired: §1.1 disambiguates both
  scope and non-interference explicitly, based on direct inspection of
  `M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md`.
- First draft's clarification-question mechanic did not explicitly cite
  the canonical-interaction-loop constraint against URI drafting reply
  text; this is a real risk (it would be easy for an implementer to just
  template the question string as the fast path). Repaired: §1.2 states
  it as a binding, non-negotiable constraint and §3 restates it at the
  point of mechanism; Batch ARN.3's acceptance criteria in §10 name it
  explicitly as a hard gate.
- First draft proposed `WAITING_FOR_HUMAN` as if it were a new addition
  to the existing AO-4 `WAITING_FOR_MODEL` state machine in
  `scripts/dev_workflow/state_machine.py`. On review this conflates two
  unrelated systems — that state machine governs the *development loop*
  (Claude/Codex/Antigravity coordination), not user-facing task
  execution. Repaired: §8 explicitly states ARN must define its own state
  names rather than overload that enum.
- Checked whether Qwen2.5-0.5B's B.4 rejection is being honored, per the
  User's explicit instruction not to assume it suitable: confirmed §2.11
  and §10 (Batch ARN.4) both state this rejection explicitly and require
  a dedicated qualification step before any reasoner fills the strategist
  role.

**What remains genuinely unverifiable at planning time, and whether it
affects this verdict:** whether Needle 3's `RESIDENT` reflex-routing scope
performs adequately on ARN-shaped candidate-ranking tasks specifically
(a different task shape than B.4's general corpus) cannot be verified
without running Batch ARN.4's own qualification step — this is disclosed
as a batch-level open question, not a planning defect, since qualifying it
is precisely what that batch exists to do. It does not block accepting
this plan, since the plan's own structure (§10) already requires that
qualification before any strategist role is filled.

**Verdict of this self-review:** plan is sound and internally consistent
with every standing constraint checked. Accepted as a planning artifact
only.

---

## 12. What this plan authorizes, and what it does not

**Authorizes:** nothing to be implemented yet. Recording this plan as
`ACCEPTED` planning-only artifact for a future session to pick up.

**Does not authorize:** any implementation this session; any change to
`uri_core/core/edge/` or `edge_lifecycle/`; any new model dependency;
resuming M33.2 Batch C (none exists or is opened by this plan); starting
M31 UI or the paused Hybrid UI Compact Chat Mode initiative.
