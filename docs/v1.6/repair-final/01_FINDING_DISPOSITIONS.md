# 01 — FINDING DISPOSITIONS (Campaign C)

Status vocabulary: `PENDING` · `IN_PROGRESS` · `REPAIRED` · `NOT_REPRODUCIBLE` · `INVALID_FINDING` · `ACCEPTED_DEFERRED`.

## Summary

- Total Campaign B findings: **12** (AUD-BLOCK 0 · AUD-MAJOR 2 · AUD-MINOR 9 · AUD-SUG 1)
- Repaired: 1 · Not reproducible: 0 · Invalid: 0 · Deferred: 0 · Remaining: 11

## Ledger

| ID | Sev | Title (short) | Status | Repair commit | Regression test | Attack replay | Residual risk |
|---|---|---|---|---|---|---|---|
| AUD-MAJOR-001 | MAJOR | Chat-approval conversation scoping opt-in | REPAIRED | `44aee9f` | `test_v16_approvals.py` 28/28 (4 fail pre-fix) + adjacent 129/129 | probe-1 §A: omission on a foreign approval refused (was approved); A6 `main`-parity kept | `/api/state` read-only pending list + `/api/autonomy` by-id resolve (unchanged; re-audit) |
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

### AUD-MAJOR-001 — detail (REPAIRED, `44aee9f`)

- **Reproduction (pre-fix):** probe-1 §A (`evidence/ma1-attack-prefix.txt`): A2 — a caller declaring no conversation resolved a convA-owned approval (`state: approved`, no error); A6 — same for a main-owned approval. Declared-foreign callers were refused (A1/A5).
- **Root cause:** the APR-02 repair made ownership an optional parameter (`resolve` ran `_require_owned` only `if conversation:`), and the legacy singular `/api/approval` route had no scope at all.
- **Repair:** `chat_approvals.require_owned` is public and unconditional; omission acts as the `main` conversation (read-path parity). Both the `/api/approvals` action and the legacy `/api/approval` route run it. No UI change (UI callers already declare the conversation).
- **Tests:** 4 new discriminating tests fail pre-fix (`ma1-newtests-prefix-fail.txt`: 4F), pass post-fix (`ma1-newtests-postfix-pass.txt`: 10/10); focused file 28/28; adjacent 129/129 (`ma1-adjacent-suite-rerun.txt`).
- **Attack replay:** `ma1-attack-replay-at-fix.txt` — A2 now `PolicyError: That request belongs to another conversation`; A6 allowed by design (omission = `main`, the record is main-owned); probe reached `PROBE-END`.
- **Sibling search:** every approval-resolution entry point was enumerated and reviewed (chat `resolve`; `/api/approvals`; `/api/approval` singular; `store.resolve_approval` callers incl. the coding-adapter expiry-deny on its own run id; `Autonomy.resolve_expansion` callers incl. `/api/autonomy` resolve). Details in `03_REGRESSION_EVIDENCE.md`.
- **Residual risk (re-audit items, unchanged):** `/api/state` unscoped read-only pending-approvals list; `/api/autonomy` by-id resolve surface. See `05_REMAINING_RISKS.md`.
