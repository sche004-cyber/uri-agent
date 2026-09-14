# URI Four-Stage Development Lifecycle

**Status:** Canonical Permanent Development Governance Rule  
**Authority:** Non-Negotiable URI Engineering Policy  
**Effective Date:** 12 September 2026  
**Applies to:** Every new add-on, capability, connector, integration, memory feature, graph feature, model feature, automation, workflow, UI-to-backend feature, skill, and future extension.

---

## 1. Overview and Core Purpose

Every future extension, integration, capability, skill, and feature in the URI ecosystem must adhere to the **URI Four-Stage Development Lifecycle**. This governance model prevents speculative implementation, ungrounded architectural drift, partial wiring, mock-data illusions, and broken agent execution loops.

A feature is never merely "code that exists" or "passing unit tests." Every feature must be grounded in verified production evidence, formally architected into URI's canonical agent loop, migrated without regression, and live-verified end-to-end through real model reasoning and runtime execution.

---

## 2. Permanent Acceptance Rule

The following is a non-negotiable, permanent URI governance rule:

> [!IMPORTANT]
> **PERMANENT ACCEPTANCE RULE:**  
> **"A feature is not DONE merely because its code exists or its unit tests pass. It is complete only when the Brain can discover and use it through URI's canonical agent loop, execution results are fed back into reasoning, and the user-visible behavior has been live-verified end-to-end."**

---

## 3. The Four-Stage Development Lifecycle

Every new add-on must pass sequentially through four mandatory stages:

```
┌────────────────────────────────────────────────────────┐
│ STAGE 1: EVIDENCE & ROOT-CAUSE AUDIT                  │
│ Establish live reality, trace production path, gather  │
│ evidence before designing or fixing anything.         │
└───────────────────────────┬────────────────────────────┘
                            │ Frozen Audit Document
                            ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 2: CANONICAL ARCHITECTURE DESIGN                │
│ Define how the add-on SHOULD fit into URI's canonical │
│ agent loop based strictly on Stage 1 evidence.         │
└───────────────────────────┬────────────────────────────┘
                            │ Frozen Architecture Document
                            ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 3: MIGRATION & INTEGRATION PLAN                 │
│ Define bounded, reversible migration path from current │
│ state to canonical architecture without regressions.  │
└───────────────────────────┬────────────────────────────┘
                            │ Frozen Migration Plan
                            ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 4: IMPLEMENTATION & END-TO-END VALIDATION       │
│ Implement accepted plan; validate via canonical loop   │
│ from user request to grounded response + live UI.      │
└────────────────────────────────────────────────────────┘
```

---

### STAGE 1 — EVIDENCE & ROOT-CAUSE AUDIT

#### Purpose
Establish what is actually happening in the live system before designing, refactoring, or fixing anything.

#### Required Questions
1. What exact problem are we solving?
2. What already exists in the codebase and runtime?
3. What does the live system actually do today?
4. What concrete evidence proves the gap or defect?
5. Is the problem local or architectural?
6. Is there already an existing capability or module intended to solve it?
7. Is the issue model-related, orchestration-related, state-related, context-related, routing-related, or integration-related?
8. What user-visible failure or metric demonstrates the problem?

#### Mandatory Rules
- **No implementation.**
- **No speculative patches.**
- **No new regexes or routing hacks.**
- **No architecture changes.**
- Trace the actual production call path and gather empirical evidence first.

#### Stage Output
A frozen **Evidence / Root-Cause Audit** document:
`docs/research/<MILESTONE>_ROOT_CAUSE_AUDIT.md`

---

### STAGE 2 — CANONICAL ARCHITECTURE DESIGN

#### Purpose
Define how the add-on SHOULD fit into URI's canonical agent loop, derived strictly from Stage 1 evidence.

#### Required Questions
1. Where does this belong in URI's canonical agent loop?
2. How does the Brain discover it?
3. What state and context does it need?
4. What actions and schemas does it expose?
5. What does it return?
6. What permissions, capability grants, and approval gates apply?
7. What memory and context implications exist?
8. Does it interact with Graphify/graph, session state, durable memory, or runtime state?
9. Does it need progressive discovery?
10. Does it require model escalation?
11. What existing component owns this responsibility?
12. What old or duplicate logic should be reused, consolidated, deprecated, or retired?

#### Mandatory Rules
- Design strictly from Stage 1 evidence.
- Do not redesign or alter the diagnosis to justify a preferred architecture.
- **No implementation yet.**

#### Stage Output
A frozen **Canonical Architecture Design** document:
`docs/architecture/<MILESTONE>_CANONICAL_ARCHITECTURE.md`

---

### STAGE 3 — MIGRATION & INTEGRATION PLAN

#### Purpose
Define exactly how to move safely from the current state to the accepted canonical architecture without breaking existing URI behavior.

#### Required Content
- Modules to reuse.
- Modules to modify.
- Modules to deprecate or retire.
- Compatibility strategy and backward compatibility guarantees.
- Feature flags or shadow mode where appropriate.
- Concrete rollback point.
- Component, integration, and behavioral test plans.
- Live verification plan.
- Step-by-step migration sequence.
- Regression risks and mitigations.
- Approval and safety impact analysis.

#### Mandatory Rules
- **No broad implementation.**
- The plan must explicitly reference Stage 1 evidence and Stage 2 architecture.
- Prefer reversible, bounded migrations.
- Do not introduce parallel competing architectures.

#### Stage Output
A frozen **Migration & Integration Plan**:
`docs/plans/<MILESTONE>_MIGRATION_PLAN.md`

---

### STAGE 4 — IMPLEMENTATION & END-TO-END VALIDATION

#### Purpose
Implement only the accepted migration plan and prove empirically that the add-on functions through URI's real agent loop.

#### Required Canonical Validation Path
Every add-on must be validated through the complete production cycle:
```
User Request
   ↓
Latest / Relevant Context Assembly
   ↓
Brain Decision (Model Reasoning)
   ↓
Capability Discovery
   ↓
Action Selection
   ↓
Deterministic Runtime Validation & Authorization
   ↓
Execution (with Approval Gates if Mutating)
   ↓
Execution Evidence / Result
   ↓
Result Fed Back to Brain Reasoning
   ↓
Grounded Natural-Language User Response
```

#### Mandatory Rules
- Component and unit tests are necessary but **NOT sufficient**.
- A capability is not complete merely because code exists.
- A capability is not complete merely because registration exists.
- A capability is not complete merely because unit tests pass.
- A capability is not complete until it is live-verified through URI's canonical user path.

#### Required Verification Levels
1. **Component tests:** Isolated unit tests for classes, schemas, and helpers.
2. **Integration tests:** Endpoints, multi-action executor, registry, and capability dispatch.
3. **Agent-loop behavioral tests:** Automated validation that the Brain proposes, the runtime validates, and results feed back into reasoning.
4. **Live verification:** Real execution from actual URI UI/desktop/chat interface where applicable.

#### Stage Output
**Implementation Report + Live Verification Result** (recorded in milestone state and project memory).

---

## 4. Canonical Loop Completion Rule (The 10 Invariants)

Every future capability or add-on must be able to answer all 10 questions:

1. **How is it discovered?**
2. **How does the Brain know it is available?**
3. **How does the Brain know when to use it?**
4. **What action contract does it expose?**
5. **What runtime state does it need?**
6. **What permissions and approvals apply?**
7. **How does execution happen?**
8. **How does the result return to reasoning?**
9. **How are follow-up references grounded?**
10. **How is it tested end-to-end?**

> [!CAUTION]
> If any of these 10 answers is missing or unspecified, the feature is **NOT integration-complete** and cannot be accepted.

---

## 5. Evidence Integrity Rules

To preserve architectural truth across milestones:

1. **Stage 2 Architecture** must explicitly reference which Stage 1 findings each major decision addresses. Stage 1 evidence must not be rewritten, filtered, or selectively ignored to justify a preferred design.
2. **Stage 3 Migration** must explicitly map back to the accepted Stage 2 architecture.
3. **Stage 4 Implementation** must be validated directly against Stage 3 acceptance criteria.

---

## 6. Scope of Application and Exception Boundary

### Scope of Application
This lifecycle applies unconditionally to:
- Capabilities and capability adapters
- Skills and toolsets
- Connectors (e.g. Gmail, Drive, Calendar, Google Workspace, institutional portals)
- Graphify and graph intelligence features
- Memory systems (durable, episodic, profile, working memory)
- Automations and background scheduled jobs
- Job monitoring and task tracking
- File conversion and document processing pipelines
- Model providers, semantic interpreters, and provider fallbacks
- Model routing and escalation mechanisms
- New runtime tools and primitives
- UI-to-backend features and client bindings
- Workflow orchestration features
- Permissions, role-based controls, and approval features
- All future unknown extensions

### Sole Exception Boundary
No add-on may bypass this four-stage lifecycle unless it is a **clearly bounded local bug fix** satisfying all four criteria:
1. **Known root cause:** Identified directly from an existing stack trace or deterministic failure.
2. **Minimal local scope:** Confined to a single function or module with no broader side effects.
3. **No architectural impact:** Introduces no new abstractions, contracts, routes, or state shapes.
4. **Regression coverage:** Accompanied by an immediate regression test covering the defect.

---

## 7. Stage Artifacts and Lifecycle States

### Artifact Path Pattern
```
docs/research/<MILESTONE>_ROOT_CAUSE_AUDIT.md
        ↓
docs/architecture/<MILESTONE>_CANONICAL_ARCHITECTURE.md
        ↓
docs/plans/<MILESTONE>_MIGRATION_PLAN.md
        ↓
Implementation & Live Verification Report (e.g. docs/plans/<MILESTONE>_STATE.md)
```

### Governing Lifecycle States
Milestones progress strictly through the standard project lifecycle states:
- `DRAFT`: Initial drafting of audit or plan.
- `REVIEWED`: Reviewed by Claude (Architect/Auditor) and peers.
- `ACCEPTED`: Approved under standing auto-approval or explicit User acceptance.
- `IMPLEMENTING`: Routed by Antigravity to Codex/Gemma for implementation.
- `VERIFICATION_READY`: All code and test suites passing; ready for audit.
- `LIVE_VERIFIED`: Verified end-to-end via the canonical agent loop and live UI.
- `COMMITTED`: Independently audited, verified, and committed by Claude Code.
