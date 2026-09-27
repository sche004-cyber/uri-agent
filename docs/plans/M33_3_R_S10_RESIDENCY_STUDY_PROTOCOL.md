# M33.3-R S10 — Residency Study Protocol

**Status:** protocol frozen before the study (2026-09-27, implementer). The study runs only in a hardware window with no concurrent S5 measurement and no other local-model benchmarking.
**Runner:** `scripts/m33_3_r_s10_residency_study.py`. **Outputs:** `docs/plans/M33_3_R_S10_RESIDENCY_TELEMETRY.json`, `docs/plans/M33_3_R_S10_RESIDENCY_AGGREGATES.json`.

## 1. Question

Plan B stage 3: on this host and the provider actually in use (LM Studio, llama.cpp GGUF backend), what do resident, idle-unloaded (TTL), on-demand (cold) and co-resident placements cost in latency and memory for the M33.3 Edge wording role (`qwen3.5-2b`) and the Capable Brain (`qwen3.5-9b`), and does URI's lease-ownership layer keep external leases untouched?

## 2. Mechanisms used (provider-native first)

- Loading: `lms load <model> --identifier uri-lease-<id> --ttl <s> -y`. The `uri-lease-` identifier is the provider-visible provenance of a URI-owned lease; the `LeaseOwnershipLedger` records it.
- Idle unload: LM Studio TTL (provider-native; URI adds no timer).
- Observation: `lms ps --json`, `/api/v0/models` load `state`.
- Unload: `lms unload <identifier>` only after `LeaseOwnershipLedger.require_may_unload` passes.
- JIT auto-evict is not exercised: a JIT request would let LM Studio evict another model, which could disrupt an external lease.

## 3. Configurations

| ID | Configuration | Measured |
|---|---|---|
| R1 | Edge resident (2B loaded by URI) | cold load time; 20 warm wording requests (p50/p95 latency, tokens); RAM/GPU delta |
| R2 | Capable resident (9B loaded by URI) | same |
| R3 | Co-resident (2B + 9B) | 20 alternating warm requests each; RAM/GPU; any latency change versus R1/R2 |
| R4 | On-demand | unload, then load-and-first-request for each model (demand-load cost) |
| R5 | Idle TTL | load 2B with `--ttl 20`; stay idle; poll `state` every 5 s up to 60 s; record unload time |
| R6 | External lease respect | a model loaded without a URI identifier (external) plus a URI-owned model; the ledger classifies both; URI cleanup unloads only its own and the external model stays loaded |

Workload: the EXPLAIN-class contracts of the frozen S5 L3 battery (`fixtures/m33_3_s5/battery.json`), constrained decoding, natural prompt (the same adapter as S5).

## 4. Measurement conditions recorded

Host OS/platform; CPU percent; RAM total/available; GPU dedicated memory (Windows `GPU Adapter Memory` counter; `UNAVAILABLE` if the counter fails); `lms ps` loaded instances and sizes before and after every configuration; wall-clock timestamps.

## 5. Safety limits and stop conditions

- **Preflight:** abort if any model is already loaded that the study did not load, unless it is the R6 external model the study created itself (no disruption of real external leases).
- **Limits:** abort a configuration and unload URI-owned leases if RAM available falls below 1.5 GiB or GPU dedicated usage exceeds 15.0 GiB (the RX 7900 GRE has 16 GiB).
- **Never** unload an instance the ledger does not own. R6's "external" model is loaded by the runner under a non-URI identifier to simulate a user load; the runner releases it only in its final cleanup step, recorded separately, after the ownership assertion.
- On any error the runner unloads only ledger-owned instances and records the partial result.

## 6. Pass criteria (FROZEN_REQUIRED for S10)

- Every URI-owned load carries a `uri-lease-` identifier and a ledger record.
- URI never unloads or evicts a non-owned instance (R6: the external instance is still loaded after URI cleanup).
- No configured limit is exceeded without the runner stopping.

Latency and memory numbers are evidence for later routing/residency policy; no residency threshold is frozen by this study (Plan B: "No always-resident 9B policy is ready to freeze").
