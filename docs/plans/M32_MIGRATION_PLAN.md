# M32 Stage 3 — migration draft

Status: DRAFT; not implementation authorization. Depends on frozen [Stage 1](../research/M32_ROOT_CAUSE_AUDIT.md) and reviewed [Stage 2](../architecture/M32_CANONICAL_ARCHITECTURE.md).

Canonical sequence, file scopes, rollback, compatibility and verification are maintained once in [M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md](M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md), sections 4–7. Contract details live only in [EXTERNAL_CAPABILITY_CONTRACT.md](../architecture/EXTERNAL_CAPABILITY_CONTRACT.md).

Migration order: baseline/manual source qualification → contract/lifecycle/disabled registration → generic gated dispatch/evidence → CLI/HTTP profiles and normal-prompt reachability → Tools & Skills UI → two real acceptance tasks + full regression → independent audit/User acceptance. No legacy registry auto-promotion, no full-registry grant expansion, no unreviewed package execution. Keep old skills metadata behavior intact; legacy skills appear labeled metadata-only until separately qualified. Rollback removes the external overlay/instances, never the prior working tree or existing evidence/history.
