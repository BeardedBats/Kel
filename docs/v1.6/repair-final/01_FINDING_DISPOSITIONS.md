# 01 — FINDING DISPOSITIONS (Campaign C)

Status vocabulary: `PENDING` · `IN_PROGRESS` · `REPAIRED` · `NOT_REPRODUCIBLE` · `INVALID_FINDING` · `ACCEPTED_DEFERRED`.

## Summary

- Total Campaign B findings: **12** (AUD-BLOCK 0 · AUD-MAJOR 2 · AUD-MINOR 9 · AUD-SUG 1)
- Repaired: 0 · Not reproducible: 0 · Invalid: 0 · Deferred: 0 · Remaining: 12

## Ledger

| ID | Sev | Title (short) | Status | Repair commit | Regression test | Attack replay | Residual risk |
|---|---|---|---|---|---|---|---|
| AUD-MAJOR-001 | MAJOR | Chat-approval conversation scoping opt-in | PENDING | — | — | — | — |
| AUD-MAJOR-002 | MAJOR | Privileged IPC sender validation not uniform | PENDING | — | — | — | — |
| AUD-MINOR-001 | MINOR | COMMIT_LEDGER completeness failures | PENDING | — | — | — | — |
| AUD-MINOR-002 | MINOR | Budget reservations not aggregated (overcommit) | PENDING | — | — | — | — |
| AUD-MINOR-003 | MINOR | `native.child_env` strip weaker than claimed | PENDING | — | — | — | — |
| AUD-MINOR-004 | MINOR | R12 packaged-evidence integrity gaps | PENDING | — | — | — | — |
| AUD-MINOR-005 | MINOR | Corpus state drift not reconciled at RC | PENDING | — | — | — | — |
| AUD-MINOR-006 | MINOR | Delegation containment does not resolve `..` | PENDING | — | — | — | — |
| AUD-MINOR-007 | MINOR | Donor `aioncore` runtime live/shipped; no disposition | PENDING | — | — | — | — |
| AUD-MINOR-008 | MINOR | Donor desktop-pet subsystem wired | PENDING | — | — | — | — |
| AUD-MINOR-009 | MINOR | Donor builder config is the default build path | PENDING | — | — | — | — |
| AUD-SUG-001 | SUG | Capability directive docstring vs behavior | PENDING | — | — | — | — |

Per-finding detail (reproduction, root cause, repair, tests, replay, residual risk) is appended below as each finding is dispositioned.
