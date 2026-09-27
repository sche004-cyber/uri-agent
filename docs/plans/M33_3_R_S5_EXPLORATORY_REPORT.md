# M33.3-R S5 — Exploratory Wording Qualification Report

**Status:** exploratory evidence only (2026-09-27, implementer). No candidate threshold is set here. The User touchpoint (§6) decides tolerances; the threshold gate is frozen after that and a fresh final requalification follows. This report is not the independent audit.

## 1. What ran

| Item | Value |
|---|---|
| Battery | `fixtures/m33_3_s5/battery.json`, 60 L3 contracts (36 verbatim from S3 v2, 24 new office-realistic), LF SHA-256 `6e28cd3023a43ba8790d5999da6586fd4d81c56f704995106eec3bb62f5a7801` |
| Need classes (deterministic policy `m33.3-r.s5.need-class.v1`) | SIMPLE 31, EXPLAIN 26, REASONING 3 |
| Arms | template; Edge `qwen3.5-2b` (Q4_K_M); Capable `qwen3.5-9b` (Q4_K_M); both LM Studio llama.cpp, temperature 0, pre-closed think block |
| Factors | decoding: constrained (`response_format` json_schema, llama.cpp grammar) vs unconstrained; prompt: natural vs allowlist-aware; 2 repeats |
| Rows | 1,020 per round |
| Round 1 | prompt v1 — preserved as `M33_3_R_S5_EXPLORATORY_R1_*.json` |
| Round 2 | prompt v2 (bounded harness repair, §4) — `M33_3_R_S5_EXPLORATORY_{AGGREGATES,TELEMETRY,BLIND_SHEET,BLIND_KEY}.json` |
| Host | Windows 11, Ryzen 9 5900X, 24 GiB RAM, RX 7900 GRE 16 GiB; no other model loaded (preflight enforced); no concurrent S10 study |

## 2. Frozen-required properties (all hold, both rounds)

| Property | Evidence | Result |
|---|---|---|
| Template valid on every contract | 60/60 | PASS |
| Presented output always valid; model reject → template | selector re-validates what is shown | PASS |
| No invented slot or candidate ID **after** validation | 0 in 1,440 policy evaluations; 0 candidate-ID leaks in 1,920 raw model rows (both rounds) | PASS |
| Edge OFF never invokes Edge | 1,440 recording-renderer evaluations (3 modes × Edge ON/OFF × warm/cold × AUTO/explicit) | PASS |
| SIMPLE/EXPLAIN never cold-load | same grid, plus a **live** probe: 26 EXPLAIN contracts routed with `qwen3.5-2b` unloaded; LM Studio state `not-loaded` before and after, 0 Edge calls | PASS |
| EDGE_ONLY never calls the Capable Brain | same grid | PASS |

Pre-validation, **unconstrained** decoding invented or omitted slots (Edge up to 33 % of rows); **constrained** decoding produced 0 invented slots and 100 % schema-valid JSON for both models.

## 3. Candidate metrics (round 2, constrained decoding)

| Arm / prompt | Validator accept (all / SIMPLE / EXPLAIN / REASONING) | Rejected only for common words (shadow) | Warm latency p50 / p95 |
|---|---|---|---|
| Template | 100 % | — | ~0 ms |
| Edge 2B, natural | 2 % / 0 % / 4 % / 0 % | 12 % | 376 / 631 ms |
| Edge 2B, allowlist | 3 % / 0 % / 8 % / 0 % | 23 % | 386 / 566 ms |
| Capable 9B, natural | 33 % / 39 % / 31 % / 0 % | 23 % | 907 / 1,223 ms |
| Capable 9B, allowlist | 40 % / 55 % / 27 % / 0 % | 30 % | 882 / 1,218 ms |

Resources (round 2 / round 1): cold load 2B 3.2 s / 2.4 s, 9B 4.8 s / 8.9 s. GPU dedicated +1.8 GB (2B), +6.0 GB (9B). Host RAM available fell 11.6 → 5.6 GB with the 9B loaded in round 2, and 8.4 → 2.7 GB in round 1, when other applications were using more memory.

## 4. Findings

1. **The Edge wording role fails on this model.** `qwen3.5-2b` reaches at most 8 % validator acceptance on EXPLAIN. Its labels often lose the facts that tell options apart (identical labels such as "budget"). This matches the M33.2 B4 negative prior for small models. The fault is quality, not only the validator.
2. **The frozen S1 validator rejects ordinary English.** Its closed allowlist has no "or", "of", "is", "a", "please", "option". About 23–30 % of Capable outputs were rejected **only** for such words. This is a validator false-rejection rate, measured by a shadow analysis that is not a gate.
3. **"Valid" does not mean "better".** Some validator-accepted model labels drop the titles and keep only "recency 0 / recency 1" (blind item 13). The validator checks provenance, not usefulness. The blind rating is the only quality signal.
4. **The template is safe but stiff.** Labels carry noise such as "recency 0 · document". Several model wordings are visibly cleaner ("First.pdf / Second.pdf").
5. **Harness repair between rounds (bounded, disclosed).** In prompt v1, CHOOSE_ATTRIBUTE rounds asked "which value of the axis matches", and models copied the word "axis". Prompt v2 names the real axis and addresses the reader as "you". Round 1 is kept as history. The repair changed no gate, battery, frozen contract, or threshold.
6. **Frozen-S1 validator gap (disclosed, not repaired in S1).** `validate_render` accepts an empty question. The S5 selector adds a stricter check (`S5-EMPTY-TEXT`), so empty text is never shown. S1 is not modified.
7. **Evidence-integrity note.** Round 1 ran before a `lms` subprocess output-decoding fix (`encoding="utf-8"`). A reader thread raised a non-fatal decode error and no measurement was affected. Round 2 used the fixed script.

## 5. What the thresholds would decide

- A model tier counts as qualified for a need class only if its constrained, validated fallback rate and its p95 latency are within the User's tolerances **and** the blind rating shows a noticeable improvement over the template.
- On the round-2 numbers, **no model tier meets any fallback tolerance below 60 %**. The Edge tier fails at every tolerance. If the User keeps the frozen validator, the likely outcome is template-primary wording for all three classes, which Amendment G1 permits. REASONING-class wording would then be a template limitation or hand-off statement.
- A widened validator allowlist could raise Capable acceptance toward ~70 %. That would need a change to frozen S1, which is outside M33.3-R (stop condition 2) and needs an explicit User decision.

## 6. User touchpoint — questions

1. **Blind wording rating:** rate `docs/plans/M33_3_R_S5_BLIND_RATING_SHEET.md` (29 pairs).
2. **Latency tolerance** (warm p95) for model wording.
3. **Fallback tolerance** for a model tier to count as qualified.
4. **Validator decision:** keep the frozen S1 validator; authorize a bounded S1 allowlist amendment (this reopens frozen S1); or defer.
