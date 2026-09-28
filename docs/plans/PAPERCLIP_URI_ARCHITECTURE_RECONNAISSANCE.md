# Paperclip → URI Architecture Reconnaissance

- **Type:** External prior-art reconnaissance and comparison. Not a plan, not a design freeze, not an implementation authorization.
- **Date:** 2026-09-28
- **Author:** Claude Code (Architect / Pre-Auditor role)
- **URI worktree:** `C:\Users\cheta\Development\Uri\_V1`, branch `m35-uri-v1-parallel-architecture`, HEAD `1f3ec48` (M36 plan commit). M33.3 is `CLOSED_FROZEN` at `291c9daa48435200c4b56857d0e3bc630016e82a` and is not reopened by anything in this report.
- **Scope guard:** No Paperclip code was vendored, installed, integrated or executed. No URI source file was modified. Nothing was committed or pushed.

## Acceptance criteria (defined before drafting)

| ID | Criterion | Result |
|---|---|---|
| AC1 | Every Paperclip claim cites a path and a symbol at one pinned revision | Met; revision in §2 |
| AC2 | Every URI claim cites a path in this worktree and says when the source is untracked research | Met |
| AC3 | Evidence is labelled by how it was obtained; unread areas are listed with their effect on the verdict | Met; §2.3 and §2.4 |
| AC4 | All 23 required sections, plus explicit answers to the 16 questions | Met; §1–§23, answers in §0 |
| AC5 | No recommendation modifies a frozen M33.3 slice; comparison uses the three required buckets | Met; §15–§17 |
| AC6 | Genuine open decisions are stated as questions, not assumed | Met; §22 |

---

## 0. Answers to the 16 questions

**Q1. What exactly is Paperclip's harness adapter abstraction?**

It is one TypeScript module per harness type, of type `ServerAdapterModule` (`packages/adapter-utils/src/types.ts`).
- The core is one call: `execute(ctx: AdapterExecutionContext) → Promise<AdapterExecutionResult>`.
- Every adapter also has a `testEnvironment(ctx)` preflight probe.
- Optional parts: `sessionCodec`, skill listing and sync, model discovery, a config schema, quota windows and a login capability.
- The server resolves the module by `agent.adapterType` via `getServerAdapter` (`server/src/adapters/registry.ts`). An unknown type falls back to the generic `processAdapter`.
- The adapter owns everything harness-specific: CLI arguments, stdin prompt, output parsing, and session-id extraction. The server owns runs, logs, sessions, workspaces and status.

**Q2. How does it persist and resume harness sessions?**

- After a run, the adapter returns opaque `sessionParams`. The adapter's `sessionCodec` serializes them.
- The server upserts them into `agent_task_sessions`, keyed uniquely by `(company_id, agent_id, adapter_type, task_key)`. The task key is usually the issue id.
- On the next run the params are decoded again. The adapter resumes (`claude --resume <id>`, `codex exec … resume <id> -`) only if the stored `cwd`, prompt-bundle key, MCP identity and remote identity all match.
- An "unknown session" error from the harness triggers one fresh-session retry and `clearSession`.
- Sessions rotate after run-count, token or age thresholds, with a handoff markdown injected into the next run.
- No time-to-live (TTL) or expiry sweep was found.
- The harness's own transcript stays in the harness's store (for example `~/.claude/projects/...`). Paperclip keeps only the handle.

**Q3. How does it manage execution workspaces?**

- Each project has workspaces; each issue has an execution workspace.
- The strategy is one of `project_primary`, `git_worktree`, `adapter_managed` or `cloud_sandbox`.
- Worktrees live under `<repoRoot>/.paperclip/worktrees/<branch>`. Branch names come from a template (default `{{issue.identifier}}-{{slug}}`), and a path-escape guard applies.
- A shared workspace is serialized with `workspace_busy` deferral.
- Cleanup runs teardown commands and deletes the branch only if its head matches an expected SHA.

**Q4. How does it authenticate and use Claude Code and Codex?**

It spawns the user's installed CLIs. Since recent versions the default path goes through an ACP wrapper; plain CLI mode is opt-in.
- **Claude:** Paperclip reuses the user's `~/.claude` login. The billing type is `"api"` only if `ANTHROPIC_API_KEY` is present, otherwise `"subscription"`.
- **Codex:** Paperclip symlinks the user's `~/.codex/auth.json` into a Paperclip-managed `CODEX_HOME`. The billing type is `"subscription"` unless `OPENAI_API_KEY` is set.
- Paperclip also has optional "managed AI connection" and login-driving paths. On those paths its server does handle secrets.

**Q5. Can it use existing subscription-authenticated local harnesses?**

Yes, technically, and that is its default local mode. Paperclip proves the mechanism only. It does not establish whether a provider's terms permit automated or orchestrated use of a consumer subscription. That question is left to the user (see §7 and §22).

**Q6. How does it record task/run provenance?**

Across several stores:
- `heartbeat_runs`: status, exit code, signal, usage, result, session before/after, log reference with SHA-256, process ids, context snapshot.
- `heartbeat_run_events`: sequenced events.
- An NDJSON log file per run.
- `activity_log`, `cost_events`, `issue_comments` and `issue_work_products`.

It is reconstructable enough for operations. It is not append-only: deleting an agent deletes its runs, events and activity rows. It also does not hash the input sources a run consumed.

**Q7. How does it handle ownership and concurrency?**

- Issue checkout is a conditional SQL `UPDATE` that sets `checkout_run_id` and `execution_run_id`. A conflict returns HTTP 409.
- Locks held by a finished or missing run are adopted.
- Wakes for an issue that is already executing are deferred. Wakes for the same task scope are coalesced into one run.
- There is a per-agent `maxConcurrentRuns` limit (default 20) and an in-process per-agent start lock.
- After a restart, orphan runs are reaped by checking whether the process id is still alive.

**Q8. How does it inject task-specific context and instructions?**

- A rendered prompt template goes to stdin (or to argv for Gemini and Pi).
- About 30 `PAPERCLIP_*` environment variables carry run, task and workspace identity.
- Claude receives a content-addressed "prompt bundle" directory outside the repo, via `--append-system-prompt-file` and `--add-dir`. Skills are symlinked inside that bundle.
- Codex skills go into the managed `CODEX_HOME`.
- A per-run MCP config file is written with mode 0600.

The target repo is not written to. However, Codex still auto-loads the repo's own `AGENTS.md`, and several adapters (Gemini, Cursor, OpenCode, Pi) symlink skills into user-global home directories.

**Q9. Does it independently verify outcomes?**

No.
- In the default `legacy` runtime, run success means the process exited with code 0, no error message and no signal. The agent then sets the issue status itself through the API.
- The newer `native` runtime classifies agent claims against durable server records. It never treats a model's `passed` flag as proof. But it does not re-execute checks or inspect artifacts itself.
- For low-risk issues (the default review policy) the native runtime still accepts the agent's own completion claim.

**Q10. Which Paperclip mechanisms are immediately useful to URI?**

See §16. The main ones:
- An adapter module with a preflight probe.
- A versioned, opaque session codec, with resume gated on compatibility and a fresh fallback when the harness no longer knows the session.
- Error families plus `retryNotBefore`.
- A `billingType` / `auth_mode` field on each run.
- A prompt bundle placed outside the repo.
- A worktree path-escape guard, and branch cleanup guarded by the branch-head SHA.
- A conditional-update claim with a run-id lock, and adoption of stale locks.
- Orphan reaping by process-id liveness.
- The stance that a claim is never proof.

**Q11. Which overlap with mechanisms URI already has?**

See §15:
- Approval gate: `uri_core/core/approval_gate.py`.
- Result versioning: S11 `uri_v1/results/version_ledger.py`.
- Trace and events: S7 `uri_v1/evaluation/`.
- Operation store with an `outcome_unknown` status: `uri_core/external/operation_store.py`.
- Wrong-binding gate: S2.
- The M36 provenance and authority vocabulary. It is stronger than anything in Paperclip.

**Q12. Which Paperclip ideas should URI reject?**

See §17:
- The company/employee metaphor and timer-driven "heartbeat" agents.
- Permission and sandbox bypass as the default.
- Agents setting their own "done" status.
- The `agent_claim_policy`.
- A mutable activity log.
- Skill symlinks in user-global home directories.
- A central Postgres control-plane server.
- Budget as the main governance lever.

**Q13. What is the smallest useful external-harness contract for URI?**

See §20: a `HarnessAdapter` port with `describe`, `probe`, `start`, `events`, `cancel` and `result`, plus one `HarnessRunRecord` lineage record. The result reports only claims. Verification is a separate, URI-owned step.

**Q14. Does this change the proposed Memory minimum?**

No structural change. It suggests one optional, non-authoritative link field (`harness_run_ref`) on OUTCOME and DERIVATIVE records. It also confirms the M36 rule that `VERIFIED` requires `VERIFIER_RESULT`. See §18.

**Q15. Does it change the proposed Edge minimum?**

No. Paperclip has no counterpart to Edge. Also, no Edge-minimum plan file exists yet. See §19.

**Q16. What should URI implement before the Office demonstrator?**

In this order:
1. A user ruling on D-A.
2. The HarnessRun contract plus one adapter, behind a feature flag.
3. A bounded workspace (copy-in/copy-out, or a worktree of an authorised root).
4. A script-and-workbook outcome verifier.
5. A lineage record linking M36, S11 and S7.

See §21 and §23.

---

## 1. Executive summary

Paperclip (`paperclipai/paperclip`) is a mature, heavily engineered TypeScript control plane. It runs coding-agent CLIs (Claude Code, Codex, Gemini, Cursor, OpenCode, Pi, Grok, Kimi, Hermes) as "employees" of a simulated company, and a Postgres-backed server with a heartbeat scheduler drives them.

For URI, its value lies in its **adapter, session and workspace plumbing**, not its architecture. That plumbing has been hardened against many real harness failure modes:
- stale sessions and resume on the wrong cwd
- poisoned session transcripts
- Codex SIGTERM leaving orphan process groups
- auth-refresh token races
- output-stall watchdogs
- orphaned runs after a server restart

URI would otherwise rediscover each of these.

Paperclip does **not** meet URI's central requirement: independent outcome verification.
- Its default runtime treats a clean process exit as run success and lets the agent declare the task done.
- Its newer runtime correctly refuses to treat model claims as proof, but it only cross-checks claims against other server records. It never re-executes a check or inspects a produced artifact.
- URI's planned stance (M36 `VERIFIER_RESULT`; research doc 05 §8, "Done from a harness is a claim, never evidence") is stricter and should stay so.

On data ownership, Paperclip's model matches URI's intent: the harness keeps the conversation, and the orchestrator keeps only an opaque resumption handle. This matches the research position "URI owns memory; harness state is cache" (M36 plan line 93, citing untracked research doc 05 §10).

**Main finding for governance:** the user's target flow, `URI → local harness adapter → existing user subscription` with Claude Code or Codex, is technically proven by Paperclip. In URI it is still blocked by an open governance question. The M31 rule forbids the Brain from shelling out to these CLIs (`docs/plans/M31_MODEL_BRAIN_UX_PLAN.md:80-82`). Research decision D-A (`docs/research/URI_HARNESS_STRATEGY/00_INDEX.md:43`, untracked) says that using them as *execution harnesses* "requires a separate explicit user ruling". This report does not assume that ruling (§22, question OD-1).

## 2. Paperclip revision inspected

| Item | Value |
|---|---|
| Repository | https://github.com/paperclipai/paperclip |
| Default branch | `master` |
| Commit inspected | `0f14d261233c545aa6a8a38ec253c498a5130fff` (committer date 2026-09-27T11:42:19Z; repo pushed 2026-09-28T02:26Z) |
| Access method | Read-only `gh api repos/.../contents/<path>?ref=<sha>`, `git/trees/<sha>?recursive=1` (8,554 tree entries), and `raw.githubusercontent.com/.../<sha>/...`. Nothing cloned, installed or executed. |
| Docs vs implementation | Where compared, source and in-code comments agree. `adapter-plugin.md` and `packages/adapters/AUTHORING.md` describe the same `ServerAdapterModule` contract. Conclusions rest on source, not the README. |

### 2.1 Primary evidence read directly (fetched and read by the author of this report)

- `packages/adapter-utils/src/types.ts`: the full adapter contract.
- `packages/db/src/schema/{agent_task_sessions,heartbeat_runs,issues,completion_contracts,native_run_results}.ts`
- `server/src/services/native-runtime/{completion-contracts,evidence-classifier,status-arbiter,native-finalization-reconciler}.ts`: the relevant functions.
- `packages/shared/src/types/native-finalization.ts`
- Spot-checked lines:
  - `server/src/services/heartbeat.ts:24738` (success predicate), `:5607`, `:17157`, `:18841`, `:19244` (`process_lost`), `:20027`, `:26170`, `:28787`, `:28935` (Codex SIGINT)
  - `packages/adapters/claude-local/src/server/execute.ts:165-167, 901, 906`
  - `packages/adapters/claude-local/src/server/acp.ts:88`
  - `packages/adapters/codex-local/src/server/codex-home.ts:10`
  - `packages/adapters/codex-local/src/server/execute.ts:1106`
  - `packages/adapters/codex-local/src/server/codex-args.ts:64`
  - `server/src/services/workspace-runtime.ts:3268, 3280, 3287`
  - `server/src/services/issues.ts:11561, 11701`
  - `server/src/services/agents.ts:1074, 1082`
  - `packages/shared/src/constants.ts:77, 919`

### 2.2 Evidence gathered by read-only sub-explorers and not every line re-read

These are marked "(sub-read)" where cited:
- per-adapter argument, parse and error details for Gemini, Cursor, OpenCode, Pi, process and HTTP
- ACPX session codec keys
- session compaction thresholds
- `ai-connection-runtime.ts` and `local-ai-login.ts` credential handling
- execution-workspace policy parsing
- approvals, budgets and pause services
- activity-log writer

Spot checks of these (above) all matched.

### 2.3 Not inspected (UNVERIFIED)

| Item | Effect on verdict |
|---|---|
| `grok_local`, `kimi_local`, `hermes`, `openclaw_gateway`, `cursor_cloud` command construction | None; not needed for URI's Claude/Codex focus |
| Internal turn loop of `packages/adapter-utils/src/acpx-engine/execute.ts` (5,458 lines) | Low. ACP is the default engine, but its observable contract is the same `AdapterExecutionResult` |
| Full bodies of `server/src/services/issues.ts` (459 KB) and `routes/issues.ts` (650 KB) | Low for Q9. A hidden automated verifier in the legacy path cannot be fully excluded, but none was found by symbol search, and the native runtime's own design implies none exists |
| Origin of runner-reported `verification` signals (`normalizePrpResultSignals`) | Low. Whatever the origin, the classifier only accepts refs that resolve to server records; it does not run checks |
| `execution_workspace_runtime_leases`, `environment_leases`, `services/recovery/service.ts` internals | Low; supplementary lease detail |

## 3. Architecture map

```
Trigger (timer | assignment | comment | on_demand | automation)
  └─ heartbeatService().invoke / wakeup  → enqueueWakeup()                heartbeat.ts:26170
        ├─ budgets.getInvocationBlock()  → skip + 409 if blocked
        ├─ coalesce into active run of same agent+task scope, or
        └─ INSERT agent_wakeup_requests + heartbeat_runs(status=queued)
  └─ startNextQueuedRunForAgent()  (per-agent in-process start lock; slots = maxConcurrentRuns − running)
        └─ claimQueuedRun()                                                 heartbeat.ts:17157
              re-check budget/pause/daily cap; company-scoped issue lock;
              status=running; bind issues.execution_run_id
        └─ executeRun(runId)   (fire-and-forget, tracked in activeRunExecutionPromises)   :20027
              ├─ resolveWorkspaceForRun → realizeExecutionWorkspace (git worktree etc.)  workspace-runtime.ts:3198
              ├─ load agent_task_sessions row; shouldResetTaskSessionForWake; evaluateSessionCompaction
              ├─ runLogStore.begin → <instanceRoot>/data/run-logs/<co>/<agent>/<run>.ndjson
              ├─ adapter = getServerAdapter(agent.adapterType)             adapters/registry.ts:996
              ├─ adapter.execute({runId, agent, runtime{sessionParams,taskKey}, config, context,
              │        signal(AbortController), onLog, onMeta, onEvent, onSpawn, authToken, …})
              │     └─ (claude_local) buildClaudeArgs → runChildProcess(stdin=prompt)
              │          → parseClaudeStreamJson → {exitCode, sessionParams, usage, costUsd, errorCode…}
              ├─ outcome: cancelled | timed_out | succeeded (exit 0 && no error && no signal) | failed   :24738
              ├─ runLogStore.finalize → log_bytes, log_sha256
              ├─ setRunStatusIfRunning(... usage_json, result_json, session_id_after …)
              ├─ releaseIssueExecutionAndPromote (free execution_run_id, promote deferred wakes)
              ├─ updateRuntimeState → cost_events → budgets.evaluateCostEvent
              └─ upsertTaskSession | clearTaskSessions
Cancellation: cancelRun → cancelRunInternal (:28787): abort signal, then terminate process group
              (SIGTERM, or SIGINT for codex_local :28935) → force-kill after grace.
Restart:      server/src/index.ts startup → recoverNativeRunsAfterRestart → reconcileHotRestartAdoption
              → reapOrphanedRuns (:18841; pid alive ⇒ keep "detached", else failed/process_lost + 1 retry)
              → promoteDueScheduledRetries → resumeQueuedRuns → sweepStaleIssueLocks …
Task status:  legacy — agent calls REST API (checkout → in_progress → in_review/done/blocked)
              native — status-arbiter decides from completion contract + evidence classification
```

There are two runtimes. `heartbeat_runs.runtime_mode` defaults to `"legacy"` (a direct adapter). `"native"` routes through `paperclip_runner` and server-side arbitration. Which one applies is decided by `native-runtime/runtime-mode.ts` (sub-read).

## 4. Adapter contract analysis

**`ServerAdapterModule`** (`types.ts`):
- Required: `type`, `execute`, `testEnvironment`.
- Optional: `sessionCodec`, `sessionManagement`, `listSkills`/`syncSkills`, `runtimeToolDelivery` (`native_mcp|environment|invocation_context`), `models`/`listModels`/`refreshModels`/`detectModel`, `getQuotaWindows`, `getConfigSchema`, `supportsInstructionsBundle` + `instructionsPathKey`, `requiresMaterializedRuntimeSkills`, `getRuntimeCommandSpec`, `loginCapability`, `onHireApproved`, `acp`.

**`AdapterExecutionContext`** (inputs):
- `runId`, `agent{id,companyId,name,adapterType,adapterConfig}`, `runtime{sessionId(legacy), sessionParams, sessionDisplayId, taskKey}`, `config`, `context`.
- `signal` ("Run-scoped operator cancellation; adapters must settle before returning"), `executionTarget` (local/SSH/sandbox).
- `runtimeMcp` and `runtimeTools` (a bearer token plus an MCP endpoint).
- Callbacks: `onLog`, `onMeta` (the invocation command, args, env and prompt, recorded for audit), `onEvent`, `onSpawn` (`pid`, `processGroupId`), `onDispatch`.
- `authToken`.

**`AdapterExecutionResult`** (outputs):

| Group | Fields |
|---|---|
| Process outcome | `exitCode`, `signal`, `timedOut` |
| Error classification | `errorCode`, `errorFamily` (`transient_upstream \| provider_quota \| model_refusal \| refresh_token_reused \| refresh_token_expired \| refresh_token_invalidated`), `retryNotBefore`, `errorMeta` |
| Usage and billing | `usage`, `usageBasis` (`per_run \| session_cumulative`), `provider`, `biller`, `model`, `billingType`, `costUsd`, `cacheAdjustedCostUsd` |
| Session | `sessionParams`, `sessionDisplayId`, `clearSession` |
| Result | `resultJson`, `summary`, `question` |
| Recovery | `executionRecovery` ("Positive evidence for retrying bootstrap; absent evidence never authorizes replay") |
| Native mode | `nativeFinalization` |

**`AdapterSessionCodec`** = `{deserialize(raw), serialize(params), getDisplayId?}`.

**`AdapterEnvironmentTestResult`** = `{status: pass|warn|fail, checks[{code, level, message, hint}]}`.

**Assessment.** This is a clean port: one function in, one structured result out. The adapter owns all harness-specific parsing. The error-family and retry-not-before fields, and the explicit "positive evidence required to retry" recovery field, match URI's evidence-integrity rules closely. Weaknesses for URI:
- The result has no field for changed artifacts or input manifest. These are inferred from the workspace later, if at all.
- `resultJson` and `summary` are free-form.

### Per-harness comparison (CLI lane; ACP is the default engine for Claude, Codex and Gemini: `claude-local/src/server/acp.ts:88` `return { engine: "acp", explicit: false }`)

| Harness | Invocation | Prompt channel | Session id source | Unknown-session handling | Billing detection |
|---|---|---|---|---|---|
| Claude Code (`claude_local`) | `claude --print --output-format stream-json --verbose [--resume id] [--append-system-prompt-file f] --add-dir <bundle>` | stdin | stream-json `session_id` | fresh retry + `clearSession`; poisoned transcript `.jsonl` unlinked | `ANTHROPIC_API_KEY` ⇒ `api`, Bedrock ⇒ `metered_api`, else `subscription` (`execute.ts:165-167`) |
| Codex (`codex_local`) | `codex exec --json [-c sandbox…] [--dangerously-bypass-approvals-and-sandbox] [resume id] -` | stdin (instructions prepended) | `thread.started.thread_id` | fresh retry + `clearSession` | `OPENAI_API_KEY` ⇒ `api`, else `subscription` (biller `chatgpt`) (sub-read) |
| Gemini (sub-read) | `--output-format stream-json [--resume] --approval-mode yolo --prompt <p>` | argv | stream | fresh retry | `GEMINI_API_KEY`/`GOOGLE_API_KEY` ⇒ `api` |
| Cursor (sub-read) | `-p --output-format stream-json --workspace <cwd> [--resume] --yolo` | stdin | stream | fresh retry | `CURSOR_API_KEY`/`OPENAI_API_KEY` ⇒ `api` |
| OpenCode / Pi (sub-read) | `run --format json` / `--mode json -p …` | stdin / argv | CLI / session file | fresh retry | `unknown` |
| Generic process | `config.command config.args` in `config.cwd` | none | none | n/a | n/a; non-zero exit ⇒ "Process exited with code N" |
| HTTP | POST `{payloadTemplate, agentId, runId, context}` | body | none | n/a | fire-and-forget; `res.ok` ⇒ success |

Process handling is `runChildProcess` in `packages/adapter-utils/src/server-utils.ts` (sub-read):
- `shell: false`, and a detached process group on POSIX.
- It strips the Claude nesting-guard environment variables (`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, …).
- Timeout sends SIGTERM to the group, then SIGKILL after `graceSec`.
- `terminalResultCleanup` kills a child that is still alive 5 s after it has emitted a terminal result event.

## 5. Claude Code integration analysis

- **Launch:** the `claude` CLI in print mode with `stream-json` output, and the prompt on stdin. Permission skipping (`dangerouslySkipPermissions`) defaults to `true` (sub-read).
- **Instructions:** written to `agent-instructions.md` inside a content-addressed prompt bundle `<instanceRoot>/companies/<co>/claude-prompt-cache/<sha256>/`. They are passed with `--append-system-prompt-file` on fresh sessions only (`execute.ts:898-901` comment: re-injecting on resume "wastes 5-10K tokens"). The bundle directory is added with `--add-dir` (`:906`). Skills are symlinked into `<bundle>/.claude/skills/`.
- **MCP:** a per-run `mcp-config.json` (mode 0600) with `--strict-mcp-config` (sub-read).
- **Resume gating:** resume happens only if the session id is a UUID and `promptBundleKey`, MCP identity, cwd and remote identity all match. Otherwise the run starts fresh.
- **Failure taxonomy:** `claude_auth_required` (login URL surfaced), `model_not_found`, `max_turns_exhausted`, `provider_quota`, `claude_transient_upstream`, `claude_refusal`, `claude_poisoned_previous_message_id`, `claude_cli_version_incompatible`, `timeout` (sub-read).
- **ACP default:** the default engine is `claude-agent-acp` (an Agent Client Protocol wrapper). It needs Node ≥ 24.11. If it is unavailable the run fails with `adapter_engine_unavailable` and does not silently fall back (sub-read). This matters for URI: Paperclip is moving to protocol-level harness control rather than CLI output scraping.

**Relevance to URI:** the prompt-bundle-outside-repo technique is directly usable. `--append-system-prompt-file` plus `--add-dir` lets URI inject capability-specific instructions without writing into the user's folder.

## 6. Codex integration analysis

- **Launch:** `codex exec --json … -` with the prompt on stdin, and `resume <thread_id> -` to resume.
- **Sandbox bypass default:** `--dangerously-bypass-approvals-and-sandbox` is the default unless a sandbox or permission restriction is configured explicitly (`codex-args.ts:64`, `DEFAULT_CODEX_LOCAL_BYPASS_APPROVALS_AND_SANDBOX`). Otherwise it uses `-c sandbox_mode="workspace-write"`.
- **Managed home:** `<PAPERCLIP_HOME>/instances/<id>/companies/<co>/codex-home`. It symlinks `auth.json` from the user's `~/.codex` (`codex-home.ts:10`, `SYMLINKED_SHARED_FILES = ["auth.json"]`) and copies the config files. Skills are symlinked into `<managed CODEX_HOME>/skills`. The managed `config.toml` is restored in a `finally` block.
- **Repo `AGENTS.md`:** not suppressed (`codex-local/src/server/execute.ts:1106`: "Paperclip does not currently suppress that discovery").
- **Watchdog:** `output-inactivity-monitor.ts` catches stalled runs (`codex_output_inactivity_monitor`).
- **Cancellation:** uses SIGINT rather than SIGTERM, because "SIGTERM can leave commands in their separate process groups alive" (`heartbeat.ts:28935`).
- **Cost:** `costUsd: null`, since Codex reports tokens but not cost.

**Relevance to URI:** the managed-`CODEX_HOME` pattern isolates configuration and skills from the user's own Codex setup while still reusing the login. For URI, a per-run or per-task `CODEX_HOME` would keep capability instructions from leaking into the user's everyday Codex. The SIGINT lesson and the stall watchdog should be copied.

## 7. Authentication / subscription findings

1. **Default mechanism: delegation.** Paperclip does not require API keys. It runs the user's installed, logged-in CLI, and the CLI authenticates itself (`~/.claude`, `~/.codex/auth.json`). A `testEnvironment` probe (`claude --print - … "Respond with hello."`) confirms that the login works. It flags `claude_anthropic_api_key_overrides_subscription` when an API key would silently take precedence.
2. **Billing classification is inferred from key presence.** A key present means `api`; none means `subscription`. This is recorded on each run as `billingType`, and URI should record it too (`auth_mode`).
3. **Paperclip is not credential-blind.**
   - Codex's `auth.json` is symlinked (the file is not read, but its location is managed).
   - `ai-connection-runtime.ts` writes company secrets into temporary homes.
   - `local-ai-login.ts` drives `codex login --device-auth` and `claude auth login`.
   - `adapter-auth-read.cjs` reads the sandbox `auth.json`.
   - `routes/agents.ts` reads the managed Codex `auth.json` (sub-read).
   - Refresh-token families (`refresh_token_reused/expired/invalidated`) exist because concurrent Codex runs sharing one `auth.json` race on token refresh.
4. **Limitations for URI:**
   - (a) Sharing one subscription login across concurrent runs causes refresh-token races. Paperclip needed copy-back and merge logic for this (`codex-auth-copyback.ts`, `codex-auth-merge-decision.ts`).
   - (b) Provider terms. Paperclip's code proves the technical path only. Whether Anthropic's or OpenAI's consumer-subscription terms allow automated orchestration is not established by any evidence here and is not assumed.
   - (c) URI's standing rule (`docs/plans/M31_MODEL_BRAIN_UX_PLAN.md:80,110`) forbids *Brain* access through these CLIs. Harness use is the separate, unresolved D-A question.
5. **Recommended URI posture if D-A permits harness use:** URI never reads, copies or stores harness credentials. It passes through only the harness's own home location. It records `auth_mode` and never falls back to an API key silently. It runs one subscription-backed run at a time per harness, which avoids the refresh race without adopting Paperclip's merge machinery.

## 8. Session persistence findings

| Aspect | Paperclip mechanism | Evidence |
|---|---|---|
| Identity | Opaque `sessionParams` (Claude: `sessionId`, `cwd`, `workspaceId`, `repoUrl`, `repoRef`, `promptBundleKey`, `mcpServerIdentity`; ACPX adds `configFingerprint`, `agentSessionId`, …) plus a display id | `types.ts` `AdapterSessionCodec`; codecs in adapter `index.ts` (sub-read) |
| Mapping | One row per `(company, agent, adapter_type, task_key)`; `last_run_id`; runs store `session_id_before/after` | `agent_task_sessions.ts`, `heartbeat_runs.ts` |
| Resume gate | Resume only if cwd, fingerprint and identity match; otherwise log and start fresh | sub-read, consistent with `execute.ts` bundle-key logic |
| Stale handle | Harness "unknown session" error triggers a fresh retry and `clearSession` | sub-read |
| Reset rules | Fresh on new assignment, approval request, unscoped timer, or credential-identity change | `heartbeat.ts:5607` `shouldResetTaskSessionForWake` |
| Rotation | Run count, token and age thresholds; handoff markdown injected | `evaluateSessionCompaction` (sub-read) |
| After process death | The handle survives in the DB. The next run resumes, or falls back to fresh | as above |
| After server restart | Runs reaped (`process_lost`, one retry). Sessions untouched | `heartbeat.ts:18841`, `:19244` |
| Expiry / cleanup | Explicit reset only, on adapter change or agent delete. **No TTL sweep found** | sub-read `services/agents.ts:806` |

**Assessment against URI's requirement:** Paperclip treats the harness session purely as a **resumption handle**, which is correct. The URI equivalent should be a `session_ref` inside the task lineage record, with these properties:
- versioned by codec, with harness type and version
- tied to the workspace root and base SHA it was created against
- marked non-authoritative
- never read into Memory as content
- losable without harm: losing it means starting fresh, never losing knowledge

What URI must add that Paperclip lacks: a record of *which input sources, at which hashes*, the session saw. Without it, a resumed session may be working on stale assumptions after the user edits the spreadsheet. M36's `DERIVATIVE_STALE` freshness concept can detect this if the run record carries the input manifest (§20).

## 9. Workspace lifecycle findings

- **Model:**
  - `project_workspaces` hold the repo root, setup and cleanup commands, and a shared key.
  - `execution_workspaces` hold the per-issue strategy, mode, status, cwd, base ref, branch, `derived_from_execution_workspace_id`, `last_used_at` and `cleanup_eligible_at`.
  - Strategies: `project_primary | git_worktree | adapter_managed | cloud_sandbox`.
  - Modes: `shared_workspace | isolated_workspace | operator_branch | reuse_existing | …` (sub-read).
- **Worktrees** (`workspace-runtime.ts`):
  - Branch template default `{{issue.identifier}}-{{slug}}` (`:3268`), sanitized to `[A-Za-z0-9._/-]` and at most 120 characters (sub-read).
  - Parent dir `<repoRoot>/.paperclip/worktrees` (`:3280`).
  - A containment check throws `worktree_path_escapes_parent_dir` (`:3287`).
  - Base ref is resolved and fetched. Unstarted reused worktrees are fast-forwarded (sub-read).
- **Concurrency:** a shared workspace held by a running run causes `workspace_busy` deferral, with a 60 s + jitter retry. Isolated modes are exempt (sub-read).
- **Cleanup:** `cleanupExecutionWorkspaceArtifacts` runs teardown, takes a worktree-cleanup lock, removes the worktree, and deletes the branch only if its head equals `expectedBranchHeadSha` (sub-read).
- **Weakness:** the worktree lives *inside* the user's repo (`.paperclip/worktrees`). Non-git folders have no isolated mode: `project_primary` simply runs in the base cwd.

**For "make this script work with this spreadsheet":** the user's files are usually in a plain folder, not a git repo. A git worktree is not the natural isolation unit. The transferable ideas are:
- (a) an explicit per-task workspace record with strategy, base state and status
- (b) a containment guard on every path
- (c) cleanup that refuses to discard anything that changed unexpectedly (Paperclip's head-SHA guard, generalised to a file-hash manifest)
- (d) serializing work on a shared workspace

The recommended URI strategy for Office files is **copy-in / copy-out**, sketched below. Final choice is question OD-3 in §22.
1. Copy only the resolved files into a URI-owned scratch workspace under the user's storage root.
2. Record their SHA-256.
3. Let the harness work there.
4. Diff the result.
5. Verify.
6. Only then write back, under the approval gate and with the S11 version ledger.

## 10. Ownership / concurrency findings

| Paperclip mechanism | Evidence | URI equivalent | Classification |
|---|---|---|---|
| Atomic issue checkout via conditional `UPDATE`; 409 `"Issue checkout conflict"` | `issues.ts:11561` | None for tasks. S10 `LeaseOwnershipLedger` (`uri_core/core/edge/lease_ownership.py:34`) covers **model-runtime** leases only | Gap; supplementary idea |
| `execution_run_id` lock; mutation guard `"Issue run ownership conflict"` | `issues.ts:11701` | S1 `BindingService` is sole owner of rebind authority (a different domain) | Gap for harness runs |
| Adopt locks held by terminal or missing runs | sub-read `adoptStaleCheckoutRun` | S10 `classify` marks orphans EXTERNAL / "uri-orphan-unverified" and **never auto-releases** | URI is deliberately more conservative; keep it |
| Orphan reaping by process-id liveness after restart, one retry | `heartbeat.ts:18841-19253` | `uri_core/external/operation_store.py` `mark_outcome_unknown` | Partial overlap; URI's `outcome_unknown` is the honest state; adapt the pid-liveness check only |
| Wake coalescing and `deferred_issue_execution` | sub-read | None needed. URI is single-user and turn-driven | Reject (no timer-driven agents) |
| `maxConcurrentRuns` default 20; in-process start lock | `constants.ts:77` | None | Adapt as a much smaller cap (1 per harness per workspace) |
| `controller_lease_expires_at`, `controller_boot_id` on runs | `heartbeat_runs.ts` | None (S10 has no TTL or heartbeat by design: "WRAP provider-native controls") | Do not add to S10; if needed, belongs in the new harness-run record |

**Conclusion:** none of Paperclip's mechanisms is superior to a frozen M33.3 mechanism *in that mechanism's own domain*. Nothing in S10, S11 or S1 should change. Paperclip does cover a domain URI has not built yet: **ownership of an external-harness run over a task workspace**. That belongs in the new harness contract (§20), not in S10.

## 11. Provenance / history findings

**What Paperclip records per run:**
- actor: `agent_id`, `responsible_user_id`
- trigger: `invocation_source`, `trigger_detail`, `wakeup_request_id`
- timing
- outcome: status, `exit_code`, `signal`, `error`, `error_code`
- `usage_json`: provider, biller, model, cost, `sessionReused`, `sessionRotated`
- `result_json`
- session before/after
- log reference, bytes and SHA-256
- process ids
- `context_snapshot`
- native mode only: completion-contract id and SHA-256

**Alongside the run:**
- `heartbeat_run_events` (sequenced; `source_payload_sha256`)
- `onMeta` invocation metadata (command, args, prompt)
- `cost_events`
- `activity_log` (`actor_type/id`, `action`, `entity`, `run_id`, `details`)
- `issue_work_products` (`created_by_run_id`, `review_state`)
- `completion_contracts`, which are good design: revisioned, `canonical_sha256`, `supersedes_contract_id`, `created_by_actor_*`

The adapter type is not a run column; it is read from `agents.adapter_type` (sub-read).

**What is canonical?** Nothing single. History is split across tables and log files.
- The activity log is **mutable**: deleting an agent deletes its `activity_log`, `heartbeat_runs` and events (`services/agents.ts:1074, 1082`).
- It is also *used as a source of truth* in places (`issue-review-policy.ts` finds the reviewer by querying `activity_log`; sub-read).

**Can it reconstruct "what happened, who or what performed it, in which workspace and context, with what result"?**
- **What and who:** mostly yes.
- **Which workspace:** yes (execution workspace, branch).
- **Which context:** partly. There is a context snapshot and the prompt via `onMeta`, but there are **no content hashes of the input files** the harness read.
- **What result:** as claimed by the agent, plus the workspace diff if a work product was recorded.
- **Was it verified:** only in native mode, and only as claim-versus-record classification.

**Comparison with URI's M36 needs** (`docs/plans/M36_URI_MEMORY_MINIMUM_PLAN.md` §7.2):
- M36 already distinguishes `Provenance` (USER_PROVIDED, SOURCE_OBSERVED, EXECUTION_OUTCOME, VERIFIER_RESULT, MODEL_DERIVED, USER_CORRECTION).
- It derives `Authority` from provenance by a pure function that callers cannot override.
- It separates `VerificationStatus` (VERIFIED requires VERIFIER_RESULT and a `verifier_id`; harness claims are `CLAIMED_ONLY`, line 331).
- Records are append-only with `supersedes`, plus `TOMBSTONE`.

URI's planned model is **stronger** than Paperclip's on every axis the brief lists (authoritative source, user input, generated content, harness output, verification, correction, superseded data). Paperclip contributes three concrete additions:
- (a) a per-run log file with a stored SHA-256
- (b) a sequenced event stream per run
- (c) revisioned, hashed completion contracts. URI's equivalent is a hashed "task acceptance criteria" record that verification is checked against.

## 12. Context / skill injection findings

| Channel | Paperclip mechanism | Touches target repo? |
|---|---|---|
| Prompt | `renderTemplate` `{{agent.id}}`… template (`DEFAULT_PAPERCLIP_AGENT_PROMPT_TEMPLATE`); bootstrap only when no resumed session; delta-only prompt on resume | No |
| Env | `PAPERCLIP_RUN_ID/TASK_ID/WORKSPACE_*`, `PAPERCLIP_API_KEY` (runtime-set; config may not override: `isForbiddenConfigEnvKey`) | No |
| System instructions (Claude) | Content-addressed bundle dir + `--append-system-prompt-file` + `--add-dir` | No (bundle outside repo) |
| System instructions (Codex/Gemini/…) | Prepended to prompt | No |
| Skills (Claude) | Symlinks under the bundle's `.claude/skills` | No |
| Skills (Codex) | Symlinks under the managed `CODEX_HOME/skills`, with a manifest of managed links | No (user's own `~/.codex` untouched unless `CODEX_HOME` points there) |
| Skills (Gemini/Cursor/OpenCode/Pi) | Symlinks into **user-global** `~/.gemini/skills`, `~/.cursor/skills`, `~/.claude/skills`, `~/.pi/agent/skills` | No repo write, but **pollutes user-global config** |
| Repo-local config | Codex auto-applies repo `AGENTS.md`; Paperclip does not suppress it (`codex-local/src/server/execute.ts:1106`) | Read, not written; still an uncontrolled context input |
| Tools | Per-run MCP config (0600) with a bearer token; `runtimeToolDelivery` | No |

**Answer:** yes, runtime instructions can be injected without permanently contaminating the target repo. Claude's bundle-dir approach and Codex's managed home show how. Paperclip does not fully control *inbound* context: repo `AGENTS.md` / `CLAUDE.md` discovery stays active, and some adapters write to user-global homes.

For URI, the stricter rules are:
- (a) a per-run instructions bundle in URI-owned storage
- (b) a per-run harness home where the harness supports one (`CODEX_HOME`; for Claude, `--setting-sources` / settings isolation)
- (c) a copy-in workspace that contains only the resolved files, so there is no stray `AGENTS.md` to discover
- (d) the hash of the bundle recorded in the run record

## 13. Approval / governance findings

- **Approvals table:** types `hire_agent | approve_ceo_strategy | budget_override_required | request_board_approval`; statuses `pending | revision_requested | approved | rejected | cancelled`; decided by a user id (sub-read).
- **Budgets:** policies per company, agent or project. A hard stop creates a `budget_override_required` approval, pauses the scope and cancels its runs. The check happens at both enqueue and claim time (sub-read).
- **Pause:** agent, company, project and subtree holds; pausing cancels active runs with `agent_paused`.
- **Review stages:** `issues.execution_policy` stages of type review or approval (`DEFAULT_MAX_REVIEW_ROUNDS = 3`). Advancing needs a comment from the designated reviewer. `review_policy` ∈ `anyone | not_creator | human_only`.
- **Question/answer:** `AdapterExecutionResult.question` and `PaperclipQuestion*` types let a harness pause for a user choice.
- **Audit:** `activity_log` (mutable, see §11).

**Mechanisms worth extracting** (without the company metaphor):
- (a) Check the gate twice, at enqueue and again at claim. This is time-of-check/time-of-use safety.
- (b) A harness-initiated **question** as a first-class result, returned to URI → Brain → user. This fits the canonical interaction loop: the Brain phrases the question, never URI.
- (c) Cancellation that must be *verified settled* (`stopRemoteStartup` "resolves only after provider termination is verified").

URI already has `uri_core/core/approval_gate.py`, `approval_store.py` (`ProposedAction`), `approval_resumption.py`, the S2 wrong-binding gate and `decision_gates.py`. Those remain the authority. Paperclip adds nothing that should replace them.

## 14. Outcome-verification findings

**This is the critical distinction, and the answer is clear:** Paperclip does not independently verify outcomes.

1. **Legacy runtime (the default).** Run `succeeded` ⇔ `(adapterResult.exitCode ?? 0) === 0 && !errorMessage && !signal` (`heartbeat.ts:24738`). The agent then moves the issue to `done` itself through the REST API. The "after the fact" checks (`run-liveness.ts` `classifyRunLiveness`, the comment policy, `successful-run-handoff.ts`) are heuristics that decide *whether to wake the agent again*. They do not validate the work (sub-read).
2. **Native runtime.**
   - `classifyNativeEvidence` (`evidence-classifier.ts`) states: "A model's `satisfied` or `passed` value is retained as a claim but never becomes proof." Each claimed criterion must cite refs that resolve to server-owned records:
     - a control-plane-accepted run event
     - an approved or merged work product
     - an approved approval
     - a resolved interaction
     - any persisted attachment. This one is weak: the mere existence of an attachment counts as `accepted`.
   - A `run.result.proposed` event is `model_result_event_is_claim_only`.
   - `status-arbiter.ts` grants `done` only when `evidenceComplete`, **or** when `policyClaimComplete`. That second path accepts the agent's own "satisfied" claims whenever `completionAuthority === "agent_claim_policy"`. `resolveNativeCompletionPolicy` (`completion-contracts.ts`) chooses that policy for every issue whose `reviewPolicy` is not `human_only` or `not_creator`, which is the default.
3. **Nowhere does the server re-run a test, open an output file, diff an artifact against expectations, or execute a verifier.** Verification in Paperclip is either a human review or a cross-reference between records.

**Partial mechanisms still useful to URI:**
- (a) The claim/evidence split and the four-way outcome vocabulary (`accepted | missing | rejected | unverifiable`). This maps closely onto M36 `VerificationStatus`.
- (b) Revisioned, hashed completion contracts that the claim must cite by revision (`contract_revision_stale`).
- (c) The rule that a stale contract revision rejects the claim.
- (d) The native `TranscriptRunVerification {commandOrCheck, status: passed|failed|not_run, artifactRef}` shape. URI can reuse it as the format of the *harness's claimed checks*, which URI then re-executes itself.

**URI verdict:** URI's intended sequence (harness works → URI independently checks → only then record `VERIFIED`) has **no counterpart in Paperclip**. It remains URI's differentiator and is a hard requirement for the Office demonstrator.

## 15. URI comparison matrix

| Concern | Paperclip | URI evidence | Bucket |
|---|---|---|---|
| Harness adapter port | `ServerAdapterModule` | `uri_core/external/contract.py` (`ExternalCapabilityDescriptor`), adapters `cli.py`/`http.py`/`in_process.py`; proposal `HarnessProvider` in `docs/research/URI_HARNESS_STRATEGY/06_PROVIDER_BOUNDARY_PROPOSAL.md` (untracked, not frozen) | 2: adapt (refine proposal) |
| Preflight probe | `testEnvironment` → pass/warn/fail checks | `uri_core/external/qualification.py` (qualification exists for external capabilities) | 1 partial + 2 (add auth-mode probe) |
| Opaque session handle + codec | `sessionCodec`, `agent_task_sessions` | None | 2: adapt |
| Error families / retry-after | `errorFamily`, `retryNotBefore` | Standing quota invariant `WAITING_FOR_MODEL` (development workflow; `scripts/dev_workflow/state_machine.py`), not runtime | 2: adapt for runtime |
| Run lifecycle / outcome_unknown | `heartbeat_runs.status` (8 states) | `uri_core/external/operation_store.py` `OperationRecord` (`pending`/`outcome_unknown`/`completed`), `lifecycle.py` `LifecycleController` | 1: URI has honest unknown state; extend states |
| Orphan / restart handling | `reapOrphanedRuns` pid liveness | S10 `classify` orphan = EXTERNAL, never auto-release | 1 (stance) + 2 (pid check) |
| Model-runtime ownership | none comparable | S10 `LeaseOwnershipLedger`, `RuntimeLease` | 1: URI stronger in its domain |
| Task/run execution ownership | checkout + `execution_run_id` 409 | None | 2: adapt (minimal) |
| Result/artifact versions | `issue_work_products`, worktree branch | S11 `uri_v1/results/version_ledger.py` (append-only, SHA-256, GENERATED/USER_EDIT/REDO) | 1: URI stronger |
| Trace / events | `heartbeat_run_events` seq, NDJSON log + SHA | S7 `uri_v1/evaluation/events.py`, `trace_context.py` | 1 + 2 (per-run log hash) |
| Provenance / authority | activity log (mutable), actor columns | M36 plan `Provenance`/`Authority`/`VerificationStatus`, append-only, `supersedes`, `TOMBSTONE` | 1: URI stronger (plan stage) |
| Outcome verification | none independent (legacy); claim-vs-record (native) | M36 `VERIFIER_RESULT` rule (plan); research doc 05 §8; **no code verifier yet** | 1 in principle; implementation gap in both |
| Approval / consequence gating | approvals table, review stages, budgets | `approval_gate.py`, `approval_store.py`, `approval_resumption.py`, S2 `wrong_binding.py` | 1: URI stronger (consequence-aware) |
| Context resolution before execution | issue/comment context snapshot | RAR (`uri_v1/turn/rar_*`), S1 binding, ARN, Graphify pointer index, M36 retrieval | 1: URI far stronger |
| Instruction injection outside repo | prompt bundle, managed `CODEX_HOME` | None | 2: adapt |
| Workspace isolation | git worktree + path guard | `uri_v1/user_storage.py` (storage root); no execution workspace | 2: adapt (copy-in/copy-out) |
| Credentials | delegates to CLI; also manages secrets | `uri_core/external/credentials.py` `ExternalCredentialStore` (Fernet) | 2 (delegate, do not store harness creds) |
| Routing to harness | agent's fixed `adapterType` | S6 `routing_policy.py` `evaluate_intelligence_route` (Brain routing, not harness) | Gap; future router target, outside frozen S6 |

## 16. Patterns recommended for adaptation

Each item cites the Paperclip source and gives a proposed URI placement. None touches a frozen M33.3 slice.

1. **Single-call adapter port with a structured result.** Source: `ServerAdapterModule.execute`, `AdapterExecutionResult` (`types.ts`). Place it in the new harness contract (§20), building on `uri_core/external/` or a new `uri_v1/execution/` (currently a placeholder).
2. **Preflight probe with a check list.** Source: `testEnvironment` and `claude_anthropic_api_key_overrides_subscription`. For URI: `probe()` returns installed version, auth mode (subscription/api/none) and warnings. Never auto-install or log in.
3. **Versioned opaque session codec, with resume gated on cwd, bundle and identity compatibility, and a fresh fallback on "unknown session".** Source: `AdapterSessionCodec`; `shouldResetTaskSessionForWake` (`heartbeat.ts:5607`). URI adds: a mismatched input-manifest hash also forces fresh.
4. **Error taxonomy with `errorFamily` and `retryNotBefore`.** This maps harness quota or outage onto URI's standing "wait, don't fail" principle.
5. **`billingType` / `auth_mode` on every run.** Source: `resolveClaudeBillingType` (`execute.ts:165`).
6. **Instruction bundle outside the target, content-addressed, with its hash recorded.** Source: Claude prompt bundle (`--append-system-prompt-file`, `--add-dir`, `execute.ts:901,906`) and managed `CODEX_HOME` (`codex-home.ts`).
7. **Path containment guard, and cleanup guarded by the expected state.** Source: `worktree_path_escapes_parent_dir` (`workspace-runtime.ts:3287`), `expectedBranchHeadSha`. For URI, generalise both to a file-hash manifest.
8. **Conditional-update claim with a run-id lock for harness runs over a workspace.** Source: `issues.checkout` (`issues.ts:11561`). A minimal per-workspace single-writer lock is enough for URI.
9. **Process-group termination with a harness-specific signal, a grace period, and verified settlement.** Sources: `cancelRunInternal` (`:28787`), Codex SIGINT (`:28935`), `stopRemoteStartup` "resolves only after provider termination is verified", `terminalResultCleanup`.
10. **Output-inactivity watchdog.** Source: `codex-local/src/server/output-inactivity-monitor.ts`.
11. **Per-run log file with a stored SHA-256, plus a sequenced event stream.** Source: `run-log-store.ts`, `heartbeat_run_events`.
12. **Claim ≠ proof classifier vocabulary and revisioned, hashed acceptance contract.** Source: `evidence-classifier.ts` and `completion_contracts`. The difference in URI is that the verifier *executes* the checks.
13. **Harness question as a structured result.** Source: `AdapterExecutionResult.question`. It goes to the Brain for phrasing, per the canonical loop.
14. **Strip nesting-guard env vars when a harness is launched from inside another harness session.** Source: `runChildProcess` removing `CLAUDECODE` and related variables. This is practically relevant because URI development itself runs inside Claude Code.

## 17. Patterns explicitly rejected

| Pattern | Reason |
|---|---|
| Company / CEO / employee / board metaphor; `hire_agent` approvals | Not URI's product identity (personal/office harness) |
| Timer-driven heartbeat agents, wake coalescing, autonomous re-wakes | URI is user-turn driven; the Brain decides, not a scheduler |
| `dangerouslySkipPermissions=true` and `--dangerously-bypass-approvals-and-sandbox` as defaults (`codex-args.ts:64`) | Conflicts with URI's safety boundary. Default must be the most restrictive posture that can do the task; see OD-4 |
| Agent sets its own task status to `done` via API | URI alone records outcome after independent verification |
| `agent_claim_policy` (self-claim accepted for low-risk work) | Violates URI evidence integrity: claims are `CLAIMED_ONLY` |
| Attachment existence counted as accepted evidence | Existence is not correctness |
| Mutable activity log deleted with its actor; log used as source of truth | M36 append-only + tombstone is the URI rule |
| Skill symlinks into user-global harness homes | Contaminates the user's own tools outside URI's scope |
| Central Postgres control-plane server, multi-tenant company scoping | User constraint: no central URI server; per-user storage |
| Budget hard-stops as the primary governance lever | URI governs by consequence and approval; cost can be recorded, not used as authority |
| Server-managed secret injection into harness homes | URI should delegate auth to the harness and never hold its credentials |
| Letting the harness conversation become the durable record | M36/D-C research: URI owns memory; harness state is cache |

## 18. Implications for URI Memory

- **No structural change to the M36 minimum is justified.** M36's provenance, authority and verification model is already stricter than Paperclip's.
- **Confirmed rule:** harness completion is recorded as `OUTCOME` with provenance `EXECUTION_OUTCOME` and status `CLAIMED_ONLY`. Only a URI verifier writes `VERIFIER_RESULT` / `VERIFIED` (M36 line 331).
- **Suggested optional addition** for PG-M1 pre-audit to consider, not decided here: an optional `harness_run_ref` on OUTCOME and DERIVATIVE records. It is a link to the external harness-run record (§20), never copied content, like the existing S11 and S7 links in `uri_adapter/links.py`. If M36 is frozen before harness work, this can come later as an additive, schema-versioned field.
- **Harness session ids must never enter Memory as retrievable content.** They are operational handles in the run record.
- **Input-manifest hashes** (`source_id@sha`) in the run record let M36 mark derivatives `DERIVATIVE_STALE` when a source changes. This reuses M36 `SourceRef` and adds nothing new.

## 19. Implications for URI Edge

- No change. Paperclip has no local small-model tier, no routing between local and cloud intelligence, and no latency-first reflex path. Its "model" choice is a per-agent config field.
- No Edge-minimum plan exists in the repo. It appears only as a sequence step (`docs/governance/URI_STATE.yaml:176`; M36 plan line 11). There is nothing to amend.
- One adjacent observation, *not* an Edge change: the frozen S6 router (`uri_core/core/edge/routing_policy.py`) routes Brain work (EDGE_ONLY / HYBRID / MAIN_BRAIN_PREFERRED). Deciding "this needs an agentic harness" is a different decision. It should be a separate, later routing layer and must not be added to frozen S6.
- Paperclip's point that Claude and Codex harnesses cannot use URI's local Edge models also appears in research doc 07 (untracked). Harness escalation therefore uses cloud intelligence by definition, so it is a consequential routing choice that the user should be able to see.

## 20. Minimum URI external-harness contract (proposal, NOT frozen)

This refines the untracked research proposal `06_PROVIDER_BOUNDARY_PROPOSAL.md` (`HarnessProvider`: describe/health/start_run/events/decide/stop/resume/result; status in `completed_claimed | failed | stopped | outcome_unknown`) with Paperclip-evidenced deltas marked **[P]**.

```
HarnessAdapter (one per harness family)
  describe() -> {harness_type, supported_versions, capabilities{resume, structured_events,
                 instructions_file, per_run_home, sandbox_modes}, default_posture}
  probe()    -> {installed_version, auth_mode: subscription|api|none|unknown,          [P testEnvironment]
                 checks[{code, level, message}]}
  start(capsule, session_ref|None) -> run_handle                                      [P execute]
  events(run_handle) -> stream of {seq, kind, payload}                                [P heartbeat_run_events]
  cancel(run_handle) -> settles only after process-group termination is verified      [P cancelRunInternal]
  result(run_handle) -> HarnessRunResult

ExecutionCapsule (URI -> harness; everything the harness may see)
  task_id, capsule_id, workspace{root, strategy: copy_in|worktree, containment_root},
  input_manifest[{source_id, relpath, sha256}], instructions_bundle{path, sha256},     [P prompt bundle]
  acceptance_criteria{revision, sha256, items[]},                                     [P completion_contracts]
  posture{sandbox, network, approvals}, limits{timeout_s, inactivity_s}                [P inactivity monitor]

HarnessRunResult (claims only)
  exit{code, signal, timed_out}, error{code, family, retry_not_before},               [P errorFamily]
  session_ref{codec_version, harness_type, harness_version, opaque, bound_to{root, manifest_sha}},  [P sessionCodec]
  claimed_outcome: completed_claimed|failed|stopped|outcome_unknown|question,
  question{prompt, choices}|None,                                                      [P result.question]
  claimed_checks[{command_or_check, status: passed|failed|not_run}],                   [P TranscriptRunVerification]
  changed_artifacts[{relpath, before_sha, after_sha, op}],   <- computed by URI from workspace diff, not trusted from harness
  usage{tokens, auth_mode, model}, log{ref, sha256}                                    [P run-log-store]

HarnessRunRecord (URI-owned lineage; append-only)
  run_id, task_id, trace_id(S7), capsule_sha, adapter{type, version}, started/finished,
  result (above), verification{verifier_id, status: VERIFIED|PARTIALLY_VERIFIED|FAILED|UNVERIFIABLE,
  evidence_refs}, supersedes
```

**Invariants:**
- (i) `changed_artifacts` is computed by URI, never taken from the harness's report.
- (ii) Nothing writes outside `containment_root`.
- (iii) Write-back to the user's real files happens only after verification and approval, through the S11 ledger.
- (iv) The session handle is non-authoritative, and losing it is harmless.
- (v) URI never reads or stores harness credentials.
- (vi) One active run per workspace [P checkout lock].

## 21. Implications for the Office demonstrator ("URI, make this script work with this spreadsheet")

| Step | Existing URI mechanism | Paperclip-inspired addition | Minimum needed? |
|---|---|---|---|
| 1 Understand task | Brain + decode (`uri_v1/turn/`) | none | existing |
| 2 Resolve script and spreadsheet | RAR, S1 `BindingService`, M36 retrieval (planned) | none | M36 minimum |
| 3 Decide agentic execution is needed | Brain decision; S6 routes Brain only | none (Paperclip has fixed agent type) | new, small: explicit "harness" route decision surfaced to the user |
| 4 Choose harness | none | `probe()` + `auth_mode` | **yes** |
| 5 Bounded workspace | `uri_v1/user_storage.py` | containment guard, workspace record, cleanup guard | **yes** (copy-in/copy-out) |
| 6 Only required context | S1 bindings, M36 context package | instructions bundle outside target; per-run harness home; input manifest | **yes** |
| 7 Harness works | none | adapter `start`, events, watchdog, cancel-verified | **yes** (one adapter) |
| 8 Changed artifacts returned | S11 ledger (for URI results) | URI-computed diff by hash | **yes** |
| 9 Independent validation | none in code | none (Paperclip lacks this) | **yes; URI-original**: re-run the script in a URI-controlled process against the copied workbook, check exit and expected workbook properties (sheets/ranges/formula errors), compare against hashed acceptance criteria |
| 10 Record lineage/provenance/verification | S7 trace, S11 ledger, M36 recorder (planned) | `HarnessRunRecord`, log SHA | **yes** (thin record, links only) |
| 11 Resume/revisit | M36 task history (planned) | `session_ref` codec, compatibility-gated resume | minimal: store handle; resume optional for demo |

**Minimum set:** one adapter, the capsule, the copy-in workspace, the run record, one domain verifier, and approval-gated write-back. Session resume can be stored but left unused in the first demo.

## 22. Open decisions requiring user input

> **Update 2026-09-28 (additive):** OD-1 through OD-5 below were **resolved by the User** after this report was written. The User's rulings are recorded verbatim-in-substance in §24. The questions below are kept unchanged as the historical record of what was open when the reconnaissance was returned.

These are not assumed. Each needs a direct user ruling before the related implementation.

- **OD-1 (blocking for harness work): D-A / M31 boundary.**
  - The question: may Claude Code and/or Codex CLI serve as URI *execution harnesses* (spawned as a subprocess, using the user's existing subscription login, with the result independently verified by URI), as distinct from URI's *Brain* (which M31 permanently forbids from shelling out)?
  - Evidence: `docs/plans/M31_MODEL_BRAIN_UX_PLAN.md:80-82,110`; `docs/plans/M31_STATE.md:82`; `docs/research/URI_HARNESS_STRATEGY/00_INDEX.md:43` (untracked); risk R-A8 in `04_BRICK_WALL_RISK_REGISTER.md`.
  - The brief's target flow implies "yes", but no formal ruling exists in the repo.
- **OD-2: Subscription terms.** Paperclip proves the technical path only. Is the user satisfied that automated use of their consumer subscription through the CLI is permitted for their accounts, or should the first adapter default to API-key mode?
- **OD-3: Workspace strategy for non-git Office files.** Recommended: copy-in/copy-out into URI-owned scratch, with write-back only after verification and approval. The alternative is a git worktree, which only works for repos.
- **OD-4: Harness permission posture.** Paperclip defaults to full bypass. Recommended for URI: the harness's own sandbox in `workspace-write` mode, no network by default, inside the copy-in workspace. That may cost capability, for example when a script needs to `pip install`.
- **OD-5: Placement.** Should the harness contract live as an extension of `uri_core/external/` (what research doc 09 S3 suggests) or in `uri_v1/execution/` (the parallel architecture, which has an import ban on `uri_core`)?

## 23. Recommended next URI step

1. **Keep the sequence** already recorded: M33.3 CLOSED_FROZEN → M36 Memory minimum (PG-M1 pre-audit, then PG-M2) → Edge minimum → Office demonstrator. Nothing in this reconnaissance justifies reordering it or reopening M33.3.
2. **Get the OD-1 ruling** before any harness planning. It is the only hard blocker this report found.
3. **When M36 reaches PG-M1:** consider the optional `harness_run_ref` link field (§18). Nothing else in M36 needs changing.
4. **Draft, as a plan only, a "Harness Execution minimum" milestone** after the ruling. Scope: §20 contract; one adapter (whichever harness OD-1 permits); copy-in workspace with containment and hash manifest; per-run instructions bundle; `HarnessRunRecord`; one script-and-workbook verifier; approval-gated write-back via S11. It should be qualified first offline against research experiment E-P5 (`08_EXPERIMENT_ROADMAP.md:151`, untracked), with a pass bar of zero claimed-but-failed runs recorded as verified.
5. **Do not vendor or depend on Paperclip.** Cite it per pattern (§16) as prior art in that plan.

---

## Self-review log

**First-draft issues found and repaired before return:**
- (1) The draft stated "Paperclip never sees credentials". Sub-read evidence shows managed-connection and login paths that do handle secrets, so it was corrected in §7.3 and Q4.
- (2) The draft implied Claude and Codex run as plain CLIs. Source shows ACP is the default engine (`acp.ts:88`), so an ACP note was added in §4 and §5.
- (3) The draft called Paperclip's native mode "verification". It was reworded to "claim-vs-record classification, no re-execution", backed by `evidence-classifier.ts` and the `policyClaimComplete` branch of `status-arbiter.ts`.
- (4) The draft put a harness lease in S10. That was removed: S10 is frozen and covers model runtimes, so the recommendation moved to the new contract (§10).
- (5) The draft relied on sub-read claims without marking them. The labels "(sub-read)" and §2.2–§2.3 were added, and 12 sub-read claims were spot-checked against source; all matched.

**Re-check against AC1–AC6:** all met.

**Remaining unverifiable items:** listed in §2.3. None changes a verdict in this report.

---

## 24. Decision resolution addendum (2026-09-28, additive)

This section was added after the report was returned. Sections 0–23 and the self-review log above are the original reconnaissance and are **not** rewritten. Where a ruling below differs from a recommendation above, the ruling governs and the recommendation stays as history.

**Source of rulings:** Direct User instruction in a live session, 2026-09-28. They are registered in `docs/governance/URI_STATE.yaml` → `architecture_decisions` as `D-A`, `OD-2`, `OD-3`, `OD-4`, `OD-5`, `VG-1` and `LF-1`.

**Status of Paperclip:** prior art only. Nothing in these rulings adopts Paperclip code, dependencies, architecture, or its company/agent metaphor.

### 24.1 User rulings (authoritative)

| ID | Ruling (User) | Relationship to this report |
|---|---|---|
| **OD-1 / D-A** | **ACCEPTED.** Claude Code and Codex CLI may serve as URI **execution harnesses**. They are **not** URI's Brain. A *Brain* is a reasoning/intelligence provider used by URI, and the existing M31 rule stays unchanged: the Brain itself must not shell out to Claude Code or Codex CLI. An *Execution Harness* is a separately launched external worker used for bounded agentic execution (Claude Code, Codex CLI, future compatible harnesses). A harness receives a bounded URI Execution Capsule; works only within URI-defined task, workspace and permission boundaries; may use its own native reasoning and tools; returns claims and results to URI; does not decide that its own result is verified; and does not become URI's canonical Memory. URI independently verifies consequential outcomes. A harness result stays `CLAIMED_ONLY` until a URI verifier establishes otherwise. | Resolves §22 OD-1. Consistent with §14 and §20 (claims only; URI verifier). M31 (`docs/plans/M31_MODEL_BRAIN_UX_PLAN.md:80-82,110`) is **not modified**. |
| **OD-2** | URI's Brain access is **provider- and transport-neutral**. Where supported, users may choose subscription-backed provider channels, API-backed providers, local Ollama, local LM Studio, other compatible local runtimes, or future supported transports. Subscription and API access are equally valid architectural options where officially supported. The user chooses the provider and the access method. Do not couple `BrainProvider == billing/auth method`; keep a structure conceptually like `BrainProvider` + `ProviderTransport/AuthMode`. Brain access mode and harness access mode are separate concerns. Do not add unsupported scraping or browser automation of the ChatGPT, Claude.ai or Gemini web apps merely to reuse a consumer subscription. | Broader than §22 OD-2, which asked only about harness subscription terms. §7 finding stands: Paperclip proves a technical path, not provider permission; "officially supported" in the ruling is the governing test. |
| **OD-3** | Workspace policy is **user-selectable per task**. Default **`COPY_IN_COPY_OUT`**: (1) resolve the exact required files; (2) copy only those into a URI-owned scratch workspace; (3) record their hashes; (4) the harness works only inside that bounded workspace; (5) URI computes the changed-artifact differences; (6) URI verifies the result; (7) write-back to the originals happens only after the required approval. Alternative **`DIRECT_ORIGINAL`** only when the user explicitly selects it for that task; it must never silently become the default. | Matches the §9 / §22 OD-3 recommendation and adds the explicit per-task alternative. |
| **OD-4** | Harness permission profile is **user-selectable per run**. Default is restrictive: workspace-write only; no network; no approval bypass; no unrestricted filesystem; no permission or sandbox bypass flags. If a task needs more, URI may ask the user to elevate the profile for that task or run (for example: allow network, permit package installation, permit access to an additional authorized folder, enable another specific capability). Do not copy Paperclip's permissive bypass defaults. | Matches the §17 rejection of `dangerouslySkipPermissions` / `--dangerously-bypass-approvals-and-sandbox` defaults and the §22 OD-4 recommendation; adds explicit per-run elevation. |
| **OD-5** | The external harness contract belongs in **`uri_v1/execution/`** for the current architecture. Concepts from `uri_core/external/` may be studied and adapted by reference, but `uri_v1` must not import across the frozen `uri_core` boundary. Do not create a new shared abstraction layer yet; reconsider later only if implementation evidence shows the need. | Resolves §22 OD-5 in favour of the `uri_v1` option. §20's contract sketch is placed there when a future plan is authorized. |
| **VG-1** | New formal future qualification requirement: **`URI_EXTERNAL_HARNESS_VIABILITY_GATE`**. URI must prove a practical advantage over giving the same task directly to Claude Code, Codex, or another harness, not merely that it can invoke one. | New; not in the original report. Specified in `docs/plans/URI_EXTERNAL_HARNESS_VIABILITY_GATE.md`. |
| **LF-1** | Design principle: **local first, escalate minimally.** External-harness invocation is a cost URI must justify, not the default path. Resolve locally → complete locally if qualified → otherwise escalate only the unresolved work → verify independently and locally where possible → record outcome and provenance. Correctness outranks avoiding escalation; Edge or local execution is never forced beyond demonstrated capability. | New. Refines §21: the harness is not automatically responsible for every Office-demonstrator step. |

### 24.2 User decisions versus Paperclip-derived recommendations

- **User decisions** (binding): the seven rows of §24.1.
- **Paperclip-derived recommendations** (non-binding engineering input to future plans): §16 adaptation list, §17 rejection list, §20 contract sketch, §21 step table. They must be re-checked against the rulings when a Harness Execution minimum plan is drafted. Known consequences:
  - §20 `posture` defaults to the OD-4 restrictive profile, and elevation is an explicit, per-run, user-approved change.
  - §20 `workspace.strategy` gains `DIRECT_ORIGINAL` as an explicit, user-selected alternative to `COPY_IN_COPY_OUT` (OD-3). The `worktree` strategy stays an option only for git repositories.
  - §20 `usage.auth_mode` describes the harness's own access mode. It is separate from Brain `ProviderTransport/AuthMode` (OD-2).
  - §21 steps gain Arm C (URI local completion) as a first-class path before delegation (LF-1, VG-1).
- §23 item 2 ("Get the OD-1 ruling") is satisfied. The remaining §23 sequence is unchanged: M36 Memory minimum (PG-M1, PG-M2) → Edge minimum → Harness Execution minimum plan → Office demonstrator.

### 24.3 Viability principle in relation to Paperclip

Paperclip has no counterpart to VG-1. It measures cost and tokens per run (`cost_events`, `usage_json`) but never compares orchestrated execution against direct execution. The Paperclip patterns in §16 items 5 (`billingType`), 11 (per-run log with SHA-256) and 12 (hashed acceptance contract) are useful *instruments* for VG-1 metrics. They are not evidence of URI advantage.
