# URI External-Harness Viability Gate (requirement specification)

- **Identity:** `URI_EXTERNAL_HARNESS_VIABILITY_GATE` (short form `VG-1` in `docs/governance/URI_STATE.yaml` → `architecture_decisions`).
- **Status:** `REQUIREMENT_RECORDED_NOT_IMPLEMENTED`. This file records a future qualification requirement. It is not a plan, does not authorize implementation, and defines no test code.
- **Date:** 2026-09-28.
- **Source:** Direct User instruction, 2026-09-28, the session that also resolved OD-1 through OD-5 of `docs/plans/PAPERCLIP_URI_ARCHITECTURE_RECONNAISSANCE.md` (see its §24).
- **Recorded by:** Claude Code (Opus 5.5), Architect role. The content below restates the User's requirement; wording marked *(recorder note)* is Claude's clarification, not a User ruling.
- **Applies to:** the future Harness Execution minimum, the future Edge minimum (avoidance share), and the Office demonstrator. It does not change M33.3 (frozen), M31 (Brain restriction unchanged), or the M36 Memory minimum.

---

## 1. Requirement

It is not enough for URI to show that it *can* invoke an external harness (Claude Code, Codex CLI, or a future compatible harness). URI must eventually show that **using URI is measurably worthwhile** compared with giving the same task directly to that harness.

If URI provides no meaningful advantage, the qualification must say so honestly and identify which URI layer adds unnecessary overhead. The benchmark must not be tuned or selected to make URI win.

## 2. Design principle: local first, escalate minimally (`LF-1`)

External-harness invocation is a cost that URI must justify. It is not the default execution path.

Preferred flow:

```
resolve locally
  -> complete locally if qualified
  -> otherwise escalate only the unresolved work
  -> independently verify locally where possible
  -> record outcome and provenance
```

URI should maximize qualified local completion and minimize external context, external tokens, external turns, external tool exploration, and unnecessary provider usage.

This does not mean forcing Edge or local execution when a task exceeds qualified local capability. **Correctness is more important than avoiding escalation.**

## 3. Execution arms

For suitable real tasks, compare up to three arms on the same task, the same source files, and the same acceptance criteria.

| Arm | Name | What happens |
|---|---|---|
| A | Direct external-harness baseline | The harness receives the raw user request, the same accessible source files, and its normal capabilities. It discovers context, inspects files, decides what matters, reasons, executes, and produces a result on its own. This represents "the user could simply use Claude Code or Codex directly". |
| B | URI-mediated harness | URI first does task decoding; RAR/ARN/context resolution as applicable; Memory retrieval; exact file binding; deterministic or local inspection; construction of the minimum Execution Capsule; acceptance criteria; and a bounded workspace. Only the unresolved agentic work is delegated. Afterwards URI computes changed artifacts itself, verifies the result independently, and records provenance and lineage. |
| C | URI local completion | Where the task is within qualified local capability, URI completes it without invoking an external harness. Mechanisms may include deterministic execution, existing URI tools, Edge, the local Brain, and local code/file/spreadsheet mechanisms, alone or combined. This is a first-class source of URI advantage. |

*(Recorder note)* Arm C applies only to tasks where local capability is actually qualified. A task outside that envelope is reported as "Arm C not applicable", never forced through Arm C.

*(Recorder note)* To keep the comparison fair, every arm's result is judged by the same independent verifier against the same hashed acceptance criteria. Arm A therefore also gets URI-side verification, but only for measurement: in Arm A the harness receives no URI context.

## 4. Two distinct advantages

**G1 — Avoidance advantage.** How often can URI finish the task correctly without invoking an external harness at all? Measure:
- external-harness avoidance rate
- percentage of the workload completed locally
- verified success
- latency
- local compute cost
- user interventions

**G2 — Delegation advantage.** When escalation is necessary, does URI reduce the work the external harness must do? Candidate mechanisms:
- resolve the exact files first
- remove filesystem exploration
- inspect spreadsheet or document structure locally
- provide compact task context, precise constraints, and hashed inputs
- provide acceptance criteria
- remove irrelevant files and context
- verify locally after execution

## 5. Metrics (record where measurable)

| Group | Metrics |
|---|---|
| Success | Verified functional success rate; verifier pass/fail; failed outcomes incorrectly claimed successful |
| Reproducibility | Reproducibility across repeated runs; recovery from failure |
| Cost and effort | Input tokens; output tokens; total reported token usage; billable cost where exposed; amount of context supplied to the harness; number of harness turns; number of tool calls; wall-clock latency; retries |
| User load | Clarification requests; user interventions |
| Correctness of inputs | Wrong-file binding errors; wrong-context errors |
| Safety | Unintended file modifications; write-back safety |
| Avoidance | External-harness avoidance rate; percentage of task completed locally |

Rules:
- Do not invent provider costs a harness does not report. Record unavailable metrics explicitly as `UNAVAILABLE` with the reason.
- *(Recorder note)* Token and cost figures are taken only from harness-reported usage or provider billing data. A missing figure is never estimated into a comparison.

## 6. Pass principle

URI does **not** need to win every individual metric.

URI must achieve **equal or better verified task success** than direct harness execution, **and** show a **material advantage in at least one important dimension** (efficiency, reliability, reproducibility, safety, context efficiency, or cost), **without an unacceptable regression** in the others.

Expected, but not presumed, advantages:
- **Reduced external-harness context and token usage**, when URI has already resolved the task and its inputs locally.
- **Reproducibility**, because URI binds context deterministically, defines acceptance criteria, verifies outcomes independently, and prevents unrelated changes.

*(Recorder note)* "Material advantage" and "unacceptable regression" must be given numeric thresholds in the future qualification plan, predeclared and frozen before the first measured run, in the same way as existing threshold gates (for example the M36 `threshold_gate.json`).

## 7. Office demonstrator application

Target task: **"URI, make this script work with this spreadsheet."**

The demonstrator should be designed so that URI may do locally:
- locate the correct `.py` file and the correct `.xlsx`
- inspect workbook structure and script metadata
- hash both inputs
- identify an obvious schema mismatch
- construct acceptance criteria
- create the bounded workspace (default `COPY_IN_COPY_OUT`, OD-3)
- decide whether the remaining work can be done locally
- if not, delegate only the code-repair portion (restrictive default permission profile, OD-4)
- run the resulting script
- inspect the resulting workbook and compare workbook properties and hashes
- verify success, or reject the harness claim

The external harness is not automatically responsible for every step. A future test compares the same task through direct Claude Code/Codex (Arm A), URI-mediated Claude Code/Codex (Arm B), and URI local completion where qualified (Arm C).

## 8. Boundaries

- Nothing here is implemented. Implementation requires its own plan, pre-audit, and User authorization.
- M31 is unchanged. The Brain never shells out to Claude Code or Codex. Harness use is governed by OD-1.
- Frozen S6 routing is unchanged. The decision to escalate to an external harness is a separate, later routing concern.
- Paperclip (`docs/plans/PAPERCLIP_URI_ARCHITECTURE_RECONNAISSANCE.md`) is prior art only; it has no counterpart to this gate.
