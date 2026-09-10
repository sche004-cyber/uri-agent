# URI Architecture

URI is model-centric: the model performs general reasoning, interpretation,
planning, drafting, review, and recovery; the local runtime is the small,
deterministic authority and execution layer.

The model may propose actions. The runtime alone validates, authorizes,
requires approval, executes, persists, audits, and reports them. Model output
is untrusted input to those controls.

This page is a map, not a substitute for governing architecture.

## Governing sources

- [ADR-018: Model-Centric Intelligence / Lightweight URI Runtime](URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md)
- [URI AI Operating Policy](URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md)
- [URI Model ↔ Runtime Contract](URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md)
- [URI M22 Architecture](URI_M22_ARCHITECTURE.md)
- [Multi-Agent Orchestration Architecture](ORCHESTRATION.md)

## Document Precedence

When interpreting requirements or resolving ambiguities, follow this order:
1. User Explicit Decisions
2. Security & Authority Invariants
3. Governing Architecture Decisions (ADR-018)
4. Runtime ↔ Model Contract
5. AI Operating Policy
6. Current Milestone Architecture Specification (e.g. URI_M22_ARCHITECTURE.md)
7. Project Memory & Delivery Tracker
8. Worker Task Instructions
9. Model Reasoning & Worker Proposals

## Repository map

| Area | Responsibility |
|---|---|
| `uri_core/` | Python runtime: API edge, identity/session state, orchestration, deterministic controls, capability execution, persistence, and audit. |
| `uri_core/core/` | Core runtime orchestration, approval, policy, capability, context, memory, and model-facing adapters. |
| `uri_core/app/server.py` | FastAPI HTTP edge. Route authorization/classification is the next M22.3 milestone. |
| `uri_ui/` | Flutter client. It is a thin HTTP client and must not gain Core authority or execution logic. |
| `URI_Model_Centric_Architecture_Docs/` | Governing model-centric architecture, operating policy, and runtime contract. |
| Root milestone documents | Delivery state and M22 execution plan; see [URI_MILESTONE_TRACKER.md](URI_MILESTONE_TRACKER.md) and [PROJECT_MEMORY.md](PROJECT_MEMORY.md). |
| `ORCHESTRATION.md` | Development multi-agent team roles, delegation, and workflow rules. |

## Current delivery boundary

M22.2 is complete at `34839ce`. M22.3 is next; M22.4 capability authority and
M22.5 provider/secrets remain deferred. See [PROJECT_MEMORY.md](PROJECT_MEMORY.md)
for the operational handoff state.

## Development Operating Architecture (AO-2)

Development orchestration mirrors runtime principles: reasoning proposes, deterministic control authorizes and executes.

- **User:** Final authority.
- **Qwen 3 14B (Local Ollama):** Day-to-day coordinator / reasoning layer (task triage, planning, worker delegation proposals, return-report reviews).
- **Antigravity (Gemini 3.8 Flash):** Control surface + implementer (exclusive authority over workspace edits, shell execution, worker dispatch, gates, tests, commits, and Flutter/UI implementation).
- **Codex (CLI):** Implementation specialist (substantial code generation and test suites).
- **Claude Code (CLI):** Architecture & security specialist (security boundaries, cross-module contracts, deep audit).
- **Gemma 3:** Excluded from active development team.
- **Specification:** [ORCHESTRATION.md](ORCHESTRATION.md).


