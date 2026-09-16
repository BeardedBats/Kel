# 10 — Reliability Review (Kel V1.5)

Status: **G9 sweep — every charter case mapped to evidence** (this working tree). Where a case is
proven by simulation (fixture deadlines, recorded provider states) rather than wall-clock hardware
failure, the basis says so; nothing here is covered by prose alone.

## Results table

| # | Case | State | Evidence (file · test) |
|---|---|---|---|
| 1 | worker false completion | ✅ | `test_broker_recovery` · `test_partial_agent_message_is_not_a_complete_result`; G5 claim gate (`test_v15_completion.py`) — claims exist only on finalized contracts |
| 2 | partial completion | ✅ | `test_core` · `test_P08_missing_review_is_uncertain`; `test_broker_recovery` · `test_cancellation_does_not_publish_recovered_result` |
| 3 | process exits without artifact | ✅ | `test_failure_surfacing` · `test_unexpected_worker_exit_explains_preserved_work`; `test_coding_recovery` · `test_missing_test_receipt_stays_fenced` |
| 4 | process hangs | ✅ simulated | deadline fencing: `test_broker_recovery` · `test_process_handle_fences_identity_before_termination`; orphan runs surface as `runs.expired_unfenced` in the diagnostics snapshot. Basis: fixture deadlines, not a multi-minute sleep |
| 5 | provider hangs | ✅ simulated | `test_v14_providers` · `test_circuit_makes_provider_degraded`; `test_failure_surfacing` · `test_provider_failure_names_the_circuit_state`. Basis: recorded latency/circuit state |
| 6 | provider disappears | ✅ | same circuit family + `test_core` · `test_provider_health_survives_restart` |
| 7 | crash after partial artifact | ✅ | `test_apply_changes` · `test_crash_after_first_replace_resumes_without_repeating_it`, `test_crash_before_replace_recovers_staging_file` |
| 8 | database locked | ✅ **probed (G9)** | `test_v15_reliability.py` · `test_write_waits_for_a_competing_writer_then_succeeds`, `test_a_held_lock_surfaces_a_clean_bounded_error_then_recovers` — wait, bounded 10 s failure, clean error, recovery, integrity `ok` |
| 9 | app killed during job | ✅ | `test_startup` · `test_abrupt_exit_releases_kernel_lock_immediately`; G2 fencing sweep re-fences stale runs |
| 10 | app restarted | ✅ | `test_core` · `test_P11_restart_retains_work_and_rebuild`; G2 `RestartResumeTests` (fresh process re-evaluates durable state) |
| 11 | duplicate resume | ✅ | `test_isolated_recovery` · `test_quiescent_contained_work_can_retry_without_old_session`; G2 `resume_after_grant` wakes exactly the blocked job |
| 12 | duplicate worker event | ✅ | `test_core` · `test_P13_duplicate_event_consumed_once` |
| 13 | stale job state | ✅ | `test_broker_recovery` · `test_fenced_run_stops_monitor_even_if_broker_still_alive`; `test_isolated_recovery` · `test_unknown_process_quiescence_remains_fenced` |
| 14 | reviewer failure | ✅ | `test_review_recovery` · `test_actual_process_crash_resumes_review_without_worker_replay`, `test_missing_verdict_settles_uncertain_once`; `test_failure_surfacing` · `test_environment_limited_verification_names_the_missing_reviewer` |
| 15 | test failure | ✅ | `test_coding_recovery` · `test_pending_checks_reject_tamper_and_cancel`; `test_coding_boundaries` suite |
| 16 | partial parallel branch | ✅ | G2 `ParallelIsolationTests` — a denial/failure in one branch touches only that branch's lease and request list |
| 17 | cancellation race | ✅ | `test_core` · `test_cancel_racing_launch_finalizes_with_terminal_receipt`, `test_P16_cancel_needs_ack`; `test_acp_host` · `test_cancel_controls_job_without_shutting_down_service`; `test_isolated_recovery` · `test_cancel_acknowledged_only_after_confirmed_group_stop` |
| 18 | provider failover | ✅ | `test_v14_providers` · `test_preferred_provider_is_selected`, `test_fallback_is_explained` |
| 19 | missing binary | ✅ | `test_v14_providers` · `test_cli_missing_is_not_installed`; desktop `binaryResolver.test.ts` · bundled-path diagnostics; packaged-binary presence check runs at G11 (`verify-packaged-smoke.cjs`) |
| 20 | missing auth | ✅ | `test_v14_providers` · `test_cli_present_without_session_needs_sign_in`, `test_api_key_states`; `test_failure_surfacing` · `test_no_eligible_worker_names_install_and_auth_reasons` |
| 21 | stale engine package | ✅ **probed (G9)** | `test_v15_reliability.py` · `test_engine_version_identity_is_reported_everywhere` — the running version is reported in `/api/state` and the diagnostics snapshot, and the session descriptor carries it (`service.py` serve()); packaged smoke re-checks at G11 |
| 22 | shutdown handle retention | ✅ **probed (G9)** | `test_v15_reliability.py` · same test class — an in-flight telemetry provider call may hold `appserver.stderr` past `Service.shutdown()`; fixed by joining the telemetry thread (bounded 30 s) |

## Defects this sweep found and fixed

1. **Masked lock error** — `Store.transaction()` ran an unconditional `ROLLBACK` when
   `BEGIN IMMEDIATE` itself failed, replacing `database is locked` with
   `cannot rollback - no transaction is active`. Guarded by `db.in_transaction`
   (`runtime/kel/core.py`). Probe 8 proves the surfaced error is now the real one.
2. **Telemetry thread outliving shutdown** — `Service.shutdown()` never joined the telemetry
   thread, so a provider call in flight kept its stderr file handle open past shutdown (visible on
   Windows as an undeletable data root). `shutdown()` now joins it, bounded at 30 s
   (`runtime/kel/service.py`). Probe 22 demonstrates the fix (the probe failed before it).

## Basis and limits

- Cases 4–5 are simulated with fixture deadlines and recorded provider states — honest, bounded
  evidence; literal multi-minute wall-clock hangs are not exercised in the suite.
- Case 19's packaged-binary half and case 21's packaged-version half are re-verified against the
  assembled artifact at G11 (packaged smoke), not here.
