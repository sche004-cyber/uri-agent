# Autonomous Workflow Write Authority & Boundary Enforcement

Once a milestone has been accepted by the User and entered an active implementation or fixing cycle (`ACCEPTED`, `IMPLEMENTING`, `AUDITING`, `FIXING`, `READY_TO_RESUME`), Antigravity has automatic write authority over the repository workspace for the accepted milestone scope.

## Execution Directives
1. **Automatic In-Scope Writes:**
   - Do NOT prompt the User for interactive approval for file modifications, creations, or fixes that fall strictly within the accepted milestone scope or Claude's verified remediation scope.
   - Automatically apply Gemma implementation outputs, bounded Antigravity audit fixes, test additions/updates, and milestone state updates (`docs/plans/*_STATE.md`).

2. **Scope Enforcement:**
   - File writes are bounded strictly by the accepted milestone plan (`docs/plans/*_PLAN.md`) and Claude's independent verification / remediation scope.
   - Out-of-scope files and protected authority files (`AGENTS.md`, `ORCHESTRATION.md`, `URI_AI_OPERATING_POLICY.md`, etc.) remain immutable to automated modification.

3. **Separation of Authorities (WRITE != RELEASE):**
   - Automatic repository write authority does NOT grant commit authority, push authority, release authority, or architectural override authority.
   - Automated git commit and git push remain strictly disabled. Release is solely gated by Claude Code independent verification (`VERIFIED`) and User release authorization.

4. **Terminal & Execution Authority:**
   - Full terminal, development, and Python execution authority within the URI workspace and bounded external task-scoped operations are authorized per `terminal_and_file_permissions.md` and `python_execution_authority.md`.
