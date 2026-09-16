# 13 — Migrations (Kel V1.5)

Status: **measured on this working tree (G11)**. Every row below is a result, not an intent;
the raw probes live in the cited tests and in the G11 run log for the real-data check.

## What V1.5 adds

Migration **010 `v15-authorization`** (module-owned, `kel/authorize.py`): the additive
`guardrail_decisions` table plus its indexes. No existing table is altered. The web of prior
migrations (001–009: memory, project map, continuation, recipes, team, providers, autonomy,
diagnostics) is untouched.

## Matrix

| Path | What ran | Result |
|---|---|---|
| Fresh install | Packaged app, fresh data root (G10 probes + smoke): engine boots, migrations apply on first touch, store usable | ✅ `docs/v1.5/evidence/g10/` + smoke (`checks-done`, `quit-observed`, `errors: []`) |
| Real V1.3-origin data (upgraded through V1.4) | Copy of the machine's real `kel-desktop/work` root (migrations 1–4, 6–9; 2 jobs, 2 runs, 4 providers, 5 recipes). Opened by the V1.5 `Service` exactly like the shell does; then one boundary decision recorded | ✅ `RESULT: OK` — zero rows lost, `integrity_check ok`, decision recorded with `policy_version = kel-authz-1.5`; 010 applies lazily at the first authorization touch (documented behavior, not startup) |
| Pre-010 store → V1.5 (synthetic) | `test_v15_upgrade.py`: strip `guardrail_decisions` + bookkeeping row from a live store, then start the Service and use the boundary | ✅ 1/1 — additive, lazy, idempotent across reopens; prior job rows intact |
| V1.3 → V1.4 upgrade module | `test_v14_upgrade.py` (retained) | ✅ 5/5 (additive upgrade, data kept, idempotent reopen, backup + record, features work on upgraded data) |
| Closed-work migration bookkeeping | `test_migration.py` (retained) | ✅ 2/2 |

## Areas checked on the real-data run

Database (integrity + file open), jobs, runs, providers, recipes — counted before/after with zero
loss; memory/leases/grants/approvals were empty in the real root and are covered by the synthetic
test's intact-data assertion. Credentials metadata stays desktop-side (not in the engine DB) and is
carried by the shell profile, unchanged by 010. Frozen role snapshots and role policy rows are
untouched by 010 (it only adds the decisions table).

## Known limitations

- A **bare `Store` open does not apply 010**; the migration lands on the first authorization use
  (Service startup does not force it). Every application path authorizes before any effect, so the
  practical upgrade moment is the first work interaction — recorded here because a reader could
  otherwise expect startup-time migration.
- The real-data row is a single machine's root (V1.3-origin). The synthetic test keeps the general
  contract executable in CI.
