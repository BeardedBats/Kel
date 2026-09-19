# 08 — WORKFORCE / ORCHESTRATION

Audit target `08f56673…`. Sources: probes 1 & 3, code reads (pods/assurance/parallel/delegation/contracts), suite re-run (998+10).

## Executed attacks (results)

| Attack | Method | Result |
|---|---|---|
| Child wider authority — class | probe-1 E1 / probe-3 | REFUSED ("Delegation may narrow authority but never create it: authority class external-effect exceeds leased-write") |
| Child wider authority — tools | probe-1 E2 | REFUSED (tool not in delegator grant / scope escape message) |
| Child scope escape | probe-1 E3 | REFUSED ("write_scope entry 'secrets/x' escapes the delegator scope ['src']") |
| Nested contract without delegator | probe-1 E4 | REFUSED ("A nested task contract must declare its delegator authority") |
| Budget envelope — single cost | probe-1 E5 | REFUSED ("Reserved cost … exceeds the remaining job budget 8.0") |
| Budget envelope — cumulative / tokens | probe-1 E6–E7 | **GAP → AUD-MINOR-002** (cumulative overcommit accepted; token/wallclock caps disclosed-absent) |
| Path-trick containment (`..`) | inline probe | **GAP → AUD-MINOR-006** (`src/../secrets` counts as within `src`; `.` root universal by design) |
| Commander spawnable | probe-3 A | INCONCLUSIVE at module level (control role also unresolved on a bare store; `resolve_role('commander')` refused but non-discriminating) — **suite coverage** (`test_workforce_assignment`, re-run green) is the standing evidence |
| Flag-off performs zero writes | probe-3 B | PASS — `delegate(enabled=False)` returns `{'delegated': False}` before touching the job/DB; table counts unchanged; control (enabled=True, unknown job) raises |
| Retry budget survives restart | probe-3 E | PASS — attempts 1→2 across a fresh `Store` instance; after the max-2 budget, third claim refused ("Milestone cannot run"); terminal milestone `NEEDS_REPAIR`, verdict UNCERTAIN |
| Never-gate waiver by Kel | probe-3 C + static | Static guard verified: "The user is the only authority that can accept never-gate findings"; `if result['never_gate_hits'] and authority != 'user': raise` (assurance.py); resolution path refuses non-user never-gate acceptance. Behavioral never-gate construction was left to the (green) suite |
| Evidence-bound close | static (`close_d1`) | Verified shape: contract lookup, packet schema validation, task-id match, ownership binding via `assignment_artifacts` for content-bound contracts, optional `artifact_root` on-disk binding — consistent with CHG-006/REQ-F4 records; `run_d1` still passes no root (disclosed) |
| Lease reclamation | static (`reclaim_stale_leases`) | Retires `ACTIVE` leases past expiry (heartbeat reclamation); never resurrected; EXPIRED note recorded — matches INV-RETRY/LEASE-EXPORTED behavior; no independent kill-mid-integration run performed |

## Not executed (recorded honestly)

- Live D2/D3 pod runs, verifier==builder attempt, family-diverse fallback unavailability, worktree isolation, Sentinel/Oracle live dispatch, learning shadow end-to-end — the suite re-run covers the recorded unit/integration behaviors; no additional independent live run was built this cycle.
- Adaptive staffing stays deferred (`5.7_DECISION_DEFERRED.md`); Advanced Worker View deferred (`phase8` decision) — decisions reviewed, not re-litigated.
