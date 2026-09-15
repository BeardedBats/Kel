# KEL V1.3 — VERIFICATION REPORT

Gate 7 (adversarial acceptance) evidence. Method: every item in `KEL_V1.3_TEST_MATRIX.md` is
mapped to concrete evidence below — PASS with an exact pointer, or a limitation stated plainly.
Nothing is claimed without a run that produced it; no savings claims are made (C4 §measurements).

## 1. Suite totals

- Full engine suite on `v1.3-dev` (Gate 7 head): **267 passed + 10 subtests** (≈60 s).
- Baseline retention: the V1.2 suite is intact — 181 baseline tests still present, none deleted
  or weakened; the delta is +86 additive V1.3 tests:

| File | Tests | Gate |
|---|---|---|
| `tests/test_v13_memory.py` | 16 | G2 |
| `tests/test_v13_projectmap.py` | 7 | G3 |
| `tests/test_v13_composer.py` | 10 | G3 |
| `tests/test_v13_continuation.py` | 17 | G4 |
| `tests/test_v13_continuation_service.py` | 9 | G4 |
| `tests/test_v13_recipes.py` | 14 | G5 |
| `tests/test_v13_work_context.py` | 13 | G6/G7 |

## 2. Acceptance mapping (all 64 items)

### MEMORY (MEM-01..12) — all PASS

| Id | Evidence |
|---|---|
| MEM-01 | `test_mem01_decision_persists_across_restart` — reopened store, trust=2, confirmed |
| MEM-02 | `test_mem02_verified_fact_stores_provenance` — source_ref + digest + trust=3 |
| MEM-03 | `test_mem03_inference_remains_lower_trust` — trust=6, confidence, excluded, then promoted only by explicit confirm |
| MEM-04 | `test_mem04_explicit_correction_supersedes_with_history` + `test_mem_conflict_open_between_decisions` (equal-authority contradictions stay OPEN conflicts; explicit replacement chains history) |
| MEM-05 | `test_mem05_retract_excludes_from_selection` |
| MEM-06 | `test_mem06_forget_purges_content` — content purged, tombstone event content-free |
| MEM-07 | `test_mem07_project_isolation` |
| MEM-08 | `test_mem08_secret_values_are_refused` — 4 shapes refused, audits value-free |
| MEM-09 | `test_mem09_external_content_cannot_become_authoritative` + `test_fence_sanitizer_mirrors_donor_behaviour` (hermes-adapted fence scrubbing) |
| MEM-10 | `test_mem10_stale_command_after_config_change` — digest change → stale → excluded |
| MEM-11 | `test_mem11_search_fallback_matches_fts` — FTS and LIKE paths identical |
| MEM-12 | `test_mem12_migration_backup_receipt_and_idempotency` + `test_mem13_backup_failure_refuses_cleanly` + `test_mem14_partial_migration_recovers` |

### PROJECT MAP (MAP-01..07) — all PASS

| Id | Evidence |
|---|---|
| MAP-01 | `test_map01_commands_and_entry_points` |
| MAP-02 | `test_map02_sources_and_trust_labels` (verified; synthesis hook labels `inferred`) |
| MAP-03 | `test_map03_one_config_change_refreshes_only_affected_sections` (probe-first; architecture copied, call-count asserted) |
| MAP-04 | `test_map04_stale_sections_for_changed_paths` |
| MAP-05 | `test_map_actions_refresh_and_stale` (engine endpoint) + packaged UI Refresh click (engine refuses rootless project with a clear message) |
| MAP-06 | `test_map06_greenfield_project_map` |
| MAP-07 | `test_map07_no_rescan_when_nothing_changed` (zero inspector calls) |

### CONTEXT (CTX-01..09) — all PASS

| Id | Evidence |
|---|---|
| CTX-01 | `test_ctx01_relevant_decision_included` (+ live path `test_submit_packet_carries_context_sources`) |
| CTX-02 | `test_ctx02_irrelevant_memory_not_included` (omissions recorded) |
| CTX-03 | `test_ctx03_superseded_decision_excluded` |
| CTX-04 | `test_ctx04_conflicts_surfaced` (packet conflicts + per-record annotation) |
| CTX-05 | `test_ctx05_recent_window_is_bounded` (≤16 msgs / ≤8k chars; no transcript kinds) |
| CTX-06 | `test_ctx06_packet_structure_persisted` (digest+size structure per packet; full text only job-linked) |
| CTX-07 | `test_ctx07_project_isolation` + `test_context_packet_is_project_scoped` (live packet crosses nothing) |
| CTX-08 | `test_ctx08_deterministic_packet_digest` |
| CTX-09 | `test_ctx09_budget_drops_turns_records_omissions` (request/decisions never dropped; over-budget raises) |

### CONTINUATION (CONT-01..11) — all PASS

| Id | Evidence |
|---|---|
| CONT-01 | live probe `restart-survives` + `restart-re-resume-idempotent` (8/8 probe JSON in `docs/v1.3/evidence/gate4-continuation-probe.json`) |
| CONT-02 | probe `new-conversation-continues` (links grow to 2) |
| CONT-03 | `test_native_session_validation` (shape-validated session carried in the resume plan; V1.2 adapter reuse path unchanged) |
| CONT-04 | plan session invalid reasons (`no stored native session`, `malformed native session id`); never "most recent" |
| CONT-05 | `test_rec13_interrupted_recipe_resumes_with_accepted_frozen` + resume probes (accepted milestone untouched) |
| CONT-06 | `plan_resume` reopen list contains only non-accepted retryable milestones |
| CONT-07 | `test_revalidation_invalidates_source_changed_milestones` / `test_revalidation_preserves_matching_digest` |
| CONT-08 | probe `ambiguous-choice-listed` + `explicit-choice-resumes`; `test_resolve_choice_when_ambiguous` |
| CONT-09 | probe `wrong-project-refused`; `test_continue_wrong_project_refused` |
| CONT-10 | `test_verified_job_cannot_resume` + `test_verified_job_refused_explicitly` |
| CONT-11 | probe `approval-survives-restart`; packaged UI approval E2E (status APPROVED) + badge "1" |
### RECIPES (REC-01..08) — all PASS

| Id | Evidence |
|---|---|
| REC-01 | `test_rec01_builtins_install_and_validate` + `test_rec05_compile_to_contract` / `test_recipes_preview_and_run_with_rooted_project` (5 builtins × compile) |
| REC-02 | `test_rec13_interrupted_recipe_resumes_with_accepted_frozen` |
| REC-03 | `test_rec10_accepted_steps_are_frozen` (claim refused; attempts stay 1) |
| REC-04 | `test_rec11_failed_steps_receive_bounded_repair` (fail-first → attempts 2 → VERIFIED; bad → attempts 4 → FAILED) |
| REC-05 | `test_rec04_kind_minima_and_commands` + compile-time enforcement (undeclared `tests:run`/`project:write` → `PolicyError`); engine capability filters unchanged (V1.2 suite) |
| REC-06 | `test_rec12_terminal_verdict_remains_kel_controlled` (`terminal_states` never enters the contract; `assess()` untouched) |
| REC-07 | `test_rec07_shadowing_and_immutability` (shadow, version bump required, both scopes inspectable) |
| REC-08 | `test_rec06_project_save_requires_confirmation` + `test_rec08_from_job_propose_confirm_and_job_check` (`recipe.saved` event) |

### TRUST / COMPLETION (TRUST-01..07) — all PASS

| Id | Evidence |
|---|---|
| TRUST-01 | No worker write path exists for memory or verdicts: memory authority lives in the engine (`Memory` is not reachable from ACP); completion only via `assess()` (V1.2 boundary tests retained in the 267) |
| TRUST-02 | Reviewers receive the persisted contract (with `context` incl. the `context_packet`) + artifact digest via `record_review` subject checks (V1.2 tests retained) |
| TRUST-03 | Live packets carry source lists; `test_submit_packet_carries_context_sources` traces a decision id into the worker-visible contract context |
| TRUST-04 | Forced-failure evidence paths retained (`test_engine_bounded_retries`, malformed-result tests) |
| TRUST-05 | `explain_failure` UNCERTAIN branch (V1.2 suite retained) |
| TRUST-06 | `explain_failure` FAILED branch (V1.2 suite retained) |
| TRUST-07 | `test_v12_reviewer_diversity`, `test_v12_trust_summary`, `test_b3_provenance` all green in the 267; V1.3 fields are additive |

### PACKAGED (PKG-01..10) — all PASS

Run: `packaging/verify-packaged-acceptance.cjs` (Playwright on the real `Kel.exe`) and
`packaging/verify-v12-upgrade.py`; raw outputs retained (`/tmp/g7acc2.log`, `/tmp/upgrade4.log`
during the session; results below are copied verbatim).

| Id | Result | Evidence |
|---|---|---|
| PKG-01 | PASS | `pkg01_exe_opens: true` (Playwright launched `Kel.exe`) |
| PKG-02 | PASS | window title `Kel`; Work drawer + all 7 tabs render |
| PKG-03 | PASS | engine spawned by the shell; `/api/state` answered; `engine_version 0.5.0` |
| PKG-04 | PASS | upgrade verify: V1.2 store → migrations `[1,2,3,4]`, all four V1.3 tables created, `backup_created`, `receipt_integrity ok`, legacy approval + messages intact |
| PKG-05 | PASS | `records_before_restart 1 → records_after_restart 1` (`pkg05_memory_survived: true`) |
| PKG-06 | PASS | Continue button in the packaged drawer resumed the seeded paused job (`pkg06_continuation_resumed: true`), assistant message "Continuing…" (`pkg06_continuation_message: true`) |
| PKG-07 | PASS | zero renderer errors across both runs (`page_errors_run1/2: []`) |
| PKG-08 | PASS | graceful `app.close()` twice; `tasklist` shows no `Kel.exe` / `KelEngine.exe` survivors |
| PKG-09 | PASS | second launch in the same run (`pkg09_relaunch: true`) |
| PKG-10 | PASS | frozen hashes re-verified: `Kel.exe E048632E…`, `resources/app.asar B56816B6…`, `resources/kel-engine/KelEngine.exe 11D9DBC0…` — identical to the Gate-0 record |

## 3. Packaging parity (shell)

`asar-dedup-pack.js` repack of the extraction + overlay:

| Metric | V1.2 baseline | V1.3 candidate |
|---|---|---|
| files | 9,539 | 9,539 |
| dedup groups | 1,103 | 1,103 |
| dedup bytes saved | 10,220,315 | 10,220,315 |
| archive bytes | 68,062,079 | 68,069,000 (+6,921 content: renderer panel + IPC allowlist) |

## 4. Frozen V1.2 integrity

All three frozen artifact hashes re-verified unchanged at Gate 7 (`E048632E…`, `B56816B6…`,
`11D9DBC0…`). `Kel-V1.2-Frozen` has never been written to; only read.

## 5. C4 measurements (context)

Representative fixtures (`runtime/tools/measure_context.py`): legacy handoff 1,299–1,327 chars
vs composer packets 1,737–1,765 chars (~434–441 estimated tokens), with source mix and
omissions recorded per packet. Design choice recorded: the composer ADDS labeled provenance,
map sections and per-source reasons; the service keeps the handoff packet as the base and
attaches the composed packet (`context_packet`) additively — so live packets are
base + provenance, not smaller. **No savings claim is made**; quality claims are limited to
the properties proven by tests (relevance filtering, omission recording, isolation).

## 6. Migration verification

- 001 memory: backup + `migration-receipt.json` + integrity check + idempotency + partial
  recovery + blocked-backup refusal (MEM-12/13/14).
- 002/003/004: same ensure pattern; V1.2 → V1.3 upgrade verified end-to-end (PKG-04) with
  applied rows `[1,2,3,4]` in order (Service startup initializes all four modules).
- Downgrade posture unchanged: old engines ignore the new tables (no V1.2 table altered).

## 7. Known limitations / honest notes

1. `ENGINE_VERSION` remains the internal runtime string `0.5.0`; `v1.3.0` is the release tag.
2. The Work drawer's transient error alert (e.g. map refresh on a rootless project) clears
   within ~1.5 s because the state poll resets the error field — pre-existing V1.2 refresh-loop
   behavior, not introduced here; the engine message itself is clear and tested.
3. Settings surfaces were not deep-clicked under automation; they are unchanged V1.2 source and
   the app boots them without console errors (final freeze smoke includes a launch/shutdown).
4. Reviewer-relay checkpoints were used at every gate; the relay was intermittently
   unavailable and one CHALLENGE was resolved with artifact-level evidence before proceeding.
5. `bun` is absent on this host; the shell build ran via `node …/electron-vite.js build` against
   the donor worktree's existing `node_modules`. Byte-identical archive parity with the V1.2
   pipeline output structure was verified (entry count + dedup groups + savings).

## 8. Reproduction

```
python -m pytest tests/ -q                              # 267 + 10
python tools/measure_context.py                         # C4 measurements
python tools/probe_continuation.py                      # 8/8 live probes
NODE_PATH=<playwright> node packaging/verify-packaged-ui.cjs         <app> <data>
NODE_PATH=<playwright> node packaging/verify-packaged-acceptance.cjs <app> <data>
python packaging/verify-v12-upgrade.py <frozen> <v13-engine> <workdir>
```
