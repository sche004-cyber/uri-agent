## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Verification-First Audit and Planning Standard

This permanent standard applies repository-wide across all URI work and Claude-produced verdicts or recommendations, including:
- audits
- plans
- architecture reviews
- readiness assessments
- code reviews
- repair plans
- migration reviews
- security reviews
- test/regression reviews
- milestone reviews
- UI reviews
- any other Claude-produced verdict or recommendation

### Mandatory Protocol
1. **Define acceptance criteria first:** Claude must define acceptance criteria before returning an audit, plan, review, or verdict.
2. **Inspect primary evidence:** Claude must inspect the actual available evidence rather than trust another agent's claims.
3. **Draft and self-review:** Claude must produce a first version, then self-review it against the acceptance criteria.
4. **Identify gaps and flaws:** Claude must identify unsupported assumptions, contradictions, missing evidence, weak reasoning, or unverifiable claims.
5. **Pre-emptive repair:** Claude must repair those issues before returning the result.
6. **Re-check repaired output:** Claude must re-check the repaired output.
7. **Explicit unverified disclosure:** If something cannot be verified, Claude must state exactly what is missing and whether it affects the verdict.
8. **Independent defect discovery:** Claude should not rely on the User to discover defects Claude could already identify itself.
9. **Preserve User review authority:** User review should be reserved for genuine approval, preference, scope, architectural judgment, or unresolved ambiguity.

## Evidence Integrity Rules

All positive claims, readiness declarations, and verification conclusions must adhere strictly to evidence integrity:

- **Strict success standard:** Only `COMPLETED_WITH_RESULT` may support a positive claim.
- **Prohibited evidence:** `PENDING`, `RUNNING`, `FAILED`, `KILLED`, `TIMED_OUT`, `CANCELLED`, `NO_OUTPUT`, or `BLOCKED` must never be treated as successful evidence.
- **Insufficient indicators:** A started command, existing process, created file, successful build, lack of exception, or another agent's "passed" claim is not sufficient proof by itself.
- **Independent multi-surface verification:** Where practical, Claude should independently verify source, repo state, logs, test results, runtime behavior, telemetry, artifacts, and milestone state.
- **Auditable correction history:** If later evidence disproves an earlier conclusion, preserve the history and explicitly record the correction rather than silently overwriting it.
