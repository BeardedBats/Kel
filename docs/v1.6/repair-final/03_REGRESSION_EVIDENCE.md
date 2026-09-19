# 03 — REGRESSION EVIDENCE (Campaign C)

Raw outputs are retained under `docs/v1.6/repair-final/evidence/`. Every repaired finding records: focused test, adjacent regression, and the Campaign B attack replay.

How to re-run (from `runtime/`):
- Engine focused: `python -m pytest tests/<file> -q`
- Campaign B attacks: `python ../kel-v16-final-audit/docs/v1.6/audit-final/probes/auditor_probe_<n>.py`

## AUD-MAJOR-001 — chat-approval conversation scoping

- Pre-fix reproduction: `evidence/ma1-attack-prefix.txt` (probe §A) — in progress at initialization.
- Discriminating tests (must fail pre-fix, pass post-fix): `evidence/ma1-newtests-prefix-fail.txt`, `evidence/ma1-newtests-postfix-pass.txt`.
- Adjacent suites: recorded below once run.

(Results appended per finding as repairs complete.)
