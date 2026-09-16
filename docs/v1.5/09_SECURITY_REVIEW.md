# 09 — Security Review (Kel V1.5)

Status: **G2 closure matrix — all 25 cases evidenced** (implementation + tests); the G4
credential-leak suite has landed (`04_CREDENTIAL_RUNTIME.md`). The G9 gate re-runs this sweep on
the assembled release with runtime evidence from the packaged build, and adds the reliability
sweep (`10_RELIABILITY_REVIEW.md`).

"Evidence" names the test or the documented trust-boundary record; no case is marked covered by
prose alone.

| # | Case | State | Evidence |
|---|---|---|---|
| 1 | no lease | ✅ G2 | `test_no_lease_is_denied` (DENY `lease-required`) |
| 2 | expired lease | ✅ G2 | `test_expired_lease_is_reported_as_expired`; worker stop at the effect point (`RestartResumeTests`) |
| 3 | revoked lease | ✅ G2 | `test_revoked_lease_is_reported_as_revoked`; `AdapterEffectPointTests` |
| 4 | spoofed actor | ✅ G2 | payload `actor` rejected on every route (`ServiceIdentityTests`); unknown actor ⇒ `INVALID_CONTEXT` |
| 5 | spoofed worker | ✅ G2 | `worker-not-active`, `worker-mismatch`, `worker-milestone-mismatch` (`FailClosedTests`) |
| 6 | spoofed role | ✅ G2 | `role-unknown` denial (`FailClosedTests`); role edits apply immediately with no cached authority (`RestartResumeTests`) |
| 7 | outside repository | ✅ G2 | `test_worker_outside_the_repository_asks_once_then_grant_resumes` (expansion, never execution); `ParallelIsolationTests` |
| 8 | outside filesystem root | ✅ G2 | system-path denial, fail-closed (`test_frozen_and_system_paths_are_denied`) |
| 9 | unauthorized domain | ✅ G2 | `test_unauthorized_domain_asks_once` (request recorded, no execution) |
| 10 | unauthorized tool | ✅ G2 | `test_unauthorized_tool_asks_once`; role tool policy (`RolePolicyTests`) |
| 11 | locked capability | ✅ G2 | every `BLOCKED_KINDS` entry denied with its guardrail rule |
| 12 | frozen path | ✅ G2 | `frozen-immutable` denial + lease refusal for frozen roots + apply refusal (V1.4.1 suite retained) |
| 13 | system path | ✅ G2 | `system-path` denial |
| 14 | destructive without snapshot | ✅ G2 | `DENY destructive-snapshot` (`test_destructive_needs_snapshot_and_approval`) |
| 15 | approval missing | ✅ G2 | `REQUIRES_USER_APPROVAL`; a valid approval must match the action digest **and** the job (`test_approval_from_another_job_...`) |
| 16 | allow-once reused | ✅ G2 | consumed exactly once; reuse ⇒ `DENY grant-used` |
| 17 | project grant revoked | ✅ G2 | `test_revoked_project_grant_is_asked_again_not_silently_allowed` |
| 18 | restart with stale authorization | ✅ G2 | `RestartResumeTests` — a fresh process re-evaluates durable state; no decision is cached |
| 19 | resumed worker after lease expiry | ✅ G2 | adapter `BLOCKED` with zero workspaces created |
| 20 | parallel authorized + unauthorized workers | ✅ G2 | `ParallelIsolationTests` — B's denial touches only B's lease and request list |
| 21 | alternate legacy effect path | ✅ G2 | effects are gated even when the caller bypasses the engine chain: direct `CodingAdapter.execute`, direct `apply_checked` (`AdapterEffectPointTests`, `ApplicationGateTests`) |
| 22 | external-agent effect boundary | ✅ G2 | dispatch gate blocks the full agent (`AdapterEffectPointTests`); read-only agent argv pinned (`NativeTrustBoundaryTests`); internal worker cannot spawn (`InternalWorkerBoundaryTests`); inner-loop trust stated in `02A` §5 |
| 23 | malformed context | ✅ G2 | `FailClosedTests` — actor/kind/job/milestone/target/worker cases deny or return `INVALID_CONTEXT`; no default lease, no "unknown = allowed" |
| 24 | guardrail tamper | ✅ G2 | `test_guardrail_tampering_refuses_every_decision` + engine tick refusal (V1.4.1 suite) |
| 25 | emergency-stop then attempted effect | ✅ G2 | `test_emergency_stop_stops_the_worker_effect_point`; jobs pause; work resumes only through the recorded reissue decision |

Note on case 21: the alternate-path claim is proven the other way round — the boundary sits at the
effect points, so a caller that skips the engine still cannot skip the boundary.

## Still to come

- Credential-leak suite (G4, engine-side): complete for the env / child-inheritance / command-line
  / durable-text / request-scope vectors — `test_v15_credentials.py` (6 tests) + redaction in
  `kel/internal.py` / `kel/research.py`; the packaged end-to-end injection check runs at G11, and
  desktop-side (crash-report) vectors are re-checked at G9.
- Full re-run of this matrix against the assembled release at G9, with runtime (not only test)
  evidence from the packaged build.
