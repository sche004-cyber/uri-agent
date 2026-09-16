# M32 Stage 2 — canonical architecture draft

Status: DRAFT, planning only; depends on [Stage 1](../research/M32_ROOT_CAUSE_AUDIT.md) freeze and Claude review. The single detailed contract is [EXTERNAL_CAPABILITY_CONTRACT.md](EXTERNAL_CAPABILITY_CONTRACT.md); do not maintain a duplicate contract here.

| Evidence | Architecture decision |
|---|---|
| E1, E9, E10 | Qualification record + managed lifecycle + existing grants; metadata enable is not execution authority |
| E2, E4 | Compile external profiles into MultiActionCapabilityRegistry and generalize canonical multi-action dispatch once |
| E3 | Reuse deterministic affordance ranking, exact aliases and existing canonical Brain; no evaluator subsystem |
| E11–E16 | Existing canonical planning accepts registry-driven metadata; legacy CapabilityPlanner has hard-coded scoring. Extend existing metadata projection/eligibility/shared-term ranking/alias constraints only; no separate external skill router or planner |
| E5, E6 | Real external permission checker and per-action validation/approval at execution; bounded fallback inside gated action path |
| E7, E8 | Existing EvidenceRecord/envelope with scoped durable artifacts, provenance and normal Brain feedback |
| Upstream interfaces | CLI profile for Agent Reach's reviewed upstream tools; HTTP profile for Firecrawl; two transport engines, future MCP seam |

Brain discovers summaries, requests selected action schemas, proposes action inputs; runtime resolves identity/config/credentials, validates grants/approval/schema/scope, executes, records evidence, and returns grounded results to reasoning. Follow-up references resolve only within the same user/session result context. No new memory promotion, model escalation or capability authority. Progressive discovery stays in the existing Directory. Component, integration, agent-loop and live UI proof are defined in the M32 plan.

Alternatives rejected: product-specific planner branches; arbitrary shell/SKILL.md execution; all transports and marketplace in v1; model-based ranking service; importing unreviewed Python into URI; auto-enabling newly discovered actions. Benefits: small Core integration surface, two contrasting live integrations, add-next-profile extensibility. Tradeoff: unsupported sources still need a reviewed adapter and manual qualification; no adversarial sandbox is claimed.
