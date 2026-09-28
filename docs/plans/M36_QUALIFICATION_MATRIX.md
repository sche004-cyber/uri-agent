# M36 qualification matrix

Implementation self-qualification, 2026-09-28. This is not the independent closing audit. Exact pytest node names are in M36_TEST_RESULTS.xml; abbreviated function names below omit the test_ prefix. Positive real-flow content is produced through actual recorder calls and S1/S7/S11; adversarial rejection fixtures deliberately include tampered records.

91 M36 tests passed with no skips. Two predeclared runs each execute 45 reference cases (90 total); 0 wrong CONFIRMED, 0 invented IDs, 0 TENTATIVE-wrong, same-session skip 100%, maximum context 3,250 bytes or less (exact measurements in telemetry), deterministic decisions. All A2 gates below passed their implementation tests; independent disposition remains open.

| Gate | Concern | Evidence | Observed behavior |
|---|---|---|---|
| Q-A2-1 | Collision completeness | grounding: a3_d_collisions_and_incomplete_scan; a2_cross_root_and_stem_collisions_ignore_type_hint; sources: hash_replacement_race_and_hidden_incompleteness | Full live basename/stem collisions across folders/roots; narrowed subset and truncated/missing-root scopes withheld. |
| Q-A2-2 | Causal task authority | storage: task_chain_concurrency_terminal_and_month_rollover; adversarial: all_admitted_transition_edges, untrusted_transitions_and_same_head_concurrency, load_fork_never_picks_later_timestamp, illegal_serialized_heads_quarantined; verifier: verified_completion_requires_current_refs_and_event_capability | Every admitted status edge; terminal correction; concurrent expected-head mismatch; monthly rollover; fork/cross-kind/cycle/authority rejection. |
| Q-A2-3 | Live source versus historical content | sources: identity_changed_missing_cap_private_overlap; adversarial: real_64mib_and_offline_policy_no_hydration; retrieval: edited_live_rediscovery_stale_derivative_and_context_privacy; contracts: source_hash_degradation | Changed live identity rediscovered; old hashes stale; missing excluded; actual sparse >64 MiB and UNKNOWN hashes cannot prove current identity. |
| Q-A2-4 | Attachments and slot types | grounding: a2_attachment_whole_turn_and_per_slot, a2_conflicting_raw_slot_classes_and_extensionless_attachment; adversarial: attachment_membership_and_mime_cannot_be_model_flags | Whole-turn attachment membership, two-slot/distinct-source guard, mismatch/conflicting/unknown types and MIME mismatch suppress authority; model hint ignored for scope filtering. |
| Q-A2-5 | Structured temporal discovery | retrieval: temporal_task_recall_20_unrelated_tasks_and_subprocess_restart, calendar_timezone_boundaries_and_unsupported, used_timestamp_is_not_a_later_pause_timestamp, task_ambiguity_paused_discovery_budget_and_terminal | New process/no filename overlap with 21 unrelated tasks; calendar/IANA timezone; opened/updated/used distinctions; multiple matches and budget fail closed. |
| Q-A2-6 | Verifier admission | verifier: impersonation_and_actual_trusted_invocation, negative_verdict_not_superseded_by_harness, verified_completion_requires_current_refs_and_event_capability | Claim flags/copied verifier names cannot attest; protected receipt digest checked on reload; actual registered byte verifier; FAILED/PARTIAL/UNVERIFIABLE protected from later claims and context flooding. |
| Q-A2-7 | Containment | contracts: bad_paths; sources: real_junction_escape, symlink_escape, hash_replacement_race_and_hidden_incompleteness, identity_changed_missing_cap_private_overlap | Actual Windows junction and symlink tests executed; component/handle checks; ADS/device/trailing aliases, private overlap and replacement race rejected. |
| Q-A2-8 | Read-back persistence | storage: restart_torn_tail_idempotency_quarantine, fault_persistence_truthful_and_retry, durable_off_unknown_schema_and_authority; adversarial: real_process_writers_serialize_and_reset | Write/newline/flush/fsync/readback fault injection; corrupt bytes retained/deduped; later records survive; exact retry and true/false persistence; four actual writer processes serialize. |
| Q-A2-9 | Immutable round snapshots | retrieval: snapshot_stable_after_interleaved_recorder_write; grounding: a4_new_collision_and_changed_source_block; qualification F-B | Interleaved history writes and two references retain old snapshot; live source/scope change blocks stale use. Source edit invalidates captured binding. |
| Q-A2-10 | Unknown-task resume | retrieval: task_ambiguity_paused_discovery_budget_and_terminal, temporal_task_recall_20_unrelated_tasks_and_subprocess_restart; qualification F-B | Paused/no/multiple/terminal task handling; real force-terminated worker and new-process discovery without task_id; restored bindings explicitly historical. |
| Q-A2-11 | Correction pairs | storage: correction_pairs_full_history_interruption_and_retry; adversarial: correction_lineage_and_context_fail_closed_budget; qualification F-B | A→B→C causal history; partial pair cannot replace current head; same-operation retry; expected-head conflict; derivative lineage remains superseded. |

| Grounding gate | Evidence and outcome |
|---|---|
| A3 A/B | Model-normalized filename and context-copied source ID absent from raw span never CONFIRMED. |
| A3 C/E | Genuine typed title/ID controls remain CONFIRMED with live complete unique scope. |
| A3 D | Duplicate basename/stem remains ambiguous; incomplete receipts withhold projection. |
| A3 F | No invented extension, punctuation, identifier prefix or boundary match; comparison-only casefold; aliases empty; negation cannot be cropped into positive selection. |
| A3 G | Missing/echoed/forged intake withholds projection. Source IDs remain available in factual context. |
| A4 H1/H2 | Actual pending-round adapter → BindingService.respond → RAR → binding: descriptive answer rewriting to filename/copied ID yields no CONFIRMED. Observed respond arguments equal trusted raw answer. |
| A4 H3 | Actual raw typed budget.xlsx and typed permitted ID retain CONFIRMED eligibility. |
| A4 invalid answers | Missing/previous-turn/wrong-round/unchecked-offset/negated-span/current source or scope mutation cannot silently confirm. |

| Original gate | Evidence / result |
|---|---|
| Q-1 / T-FROZEN / T-BOUNDARY | 1,002 relevant tracked tests passed; 58 predeclared/environment skips; 178 subtests. 8 S4 + 24 LF anchors unchanged; complete frozen source/test scope checked, AST boundary test passed. |
| Q-2 / Q-3 | 90 real-format reference cases, zero invented IDs/wrong CONFIRMED; authorized containment/collision adversarial tests pass. |
| Q-4 | Five predeclared follow-ups per run operate without durable read even with durable Memory OFF: 100%. |
| Q-5 | Correct supported task/time current references discovered across fresh process; no filename overlap; 21 unrelated tasks. |
| Q-6 / Q-7 | Hash or degraded identity and authority labels; real S11 version links; claim versus protected verifier distinction and receipt reload tests pass. |
| Q-8 | Real S7 Change → correction pair, both records persisted; old lineage retained. |
| Q-9 | Force-terminated task worker → fresh reader discovers paused task without ID; exact two references, next step and last outcome restored; subsequent explicit resume succeeds. |
| Q-10 | Edited live document rediscovered; historical derivative DERIVATIVE_STALE; unsafe/missing sources excluded. |
| Q-11 / Q-12 | ≤8 KiB context cap, overflow returns empty degraded package; two users and unrelated task content isolation checks pass. |
| Q-E2E | F-A real docx read/S11 summary/Memory derivative; F-B S1 two refs/claim/trusted verifier/S7 Change/pair/pause/process kill/discovery/resume. |
| Q-DET | Identical normalized decisions across two full runs; fixed query snapshot determinism covered separately. Random identities in separate temp roots are intentionally distinct. |
| Q-LAT | Retrieval p50/p95 and machine metadata in telemetry. Separate load/fingerprint percentiles UNMEASURED; not a gate. |

Threshold SHA-256: `e5fdeff503bd520ad60a3e4c567e8da71254041f9b987018331f9015a7af24af`. Thresholds and battery were written before the first qualification attempt and never relaxed. The initial failed driver attempt exposed verifier-bootstrap restoration, repaired before requalification. Subsequent added adversarial tests extend rejection coverage without changing thresholds.
