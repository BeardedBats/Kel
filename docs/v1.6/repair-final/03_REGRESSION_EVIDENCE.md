# 03 — REGRESSION EVIDENCE (Campaign C)

Raw outputs are retained under `docs/v1.6/repair-final/evidence/`. Every repaired finding records: focused test, adjacent regression, and the Campaign B attack replay.

How to re-run (from `runtime/`):
- Engine focused: `python -m pytest tests/<file> -q`
- Campaign B attacks (in-repo copy used by Campaign C): `cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_<n>.py`

## AUD-MAJOR-001 — chat-approval conversation scoping (REPAIRED, `44aee9f`)

- Pre-fix reproduction (Campaign B probe §A): `evidence/ma1-attack-prefix.txt` — A2/A6: a caller declaring no conversation settled convA-/main-owned approvals with NO ERROR.
- Discriminating tests: 4 new tests fail pre-fix (`evidence/ma1-newtests-prefix-fail.txt`: 4 failed, 6 passed, 18 deselected; the single teardown `PermissionError` is a Windows temp-file-lock artifact of the failing run — absent in every subsequent run), 10/10 pass post-fix (`evidence/ma1-newtests-postfix-pass.txt`).
- Focused suite: `cd runtime && python -m pytest tests/test_v16_approvals.py -q` → 28 passed.
- Adjacent suite: `python -m pytest tests/test_v16_approvals.py tests/test_v16_r4_approval_exact.py tests/test_v14_autonomy.py tests/test_v15_authorize.py tests/test_v16_r1_authority.py -q` → 129 passed (`evidence/ma1-adjacent-suite-rerun.txt`; original capture `ma1-adjacent-suite.txt`).
- Campaign B attack replay at fix: `cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_1.py` → A2 now `PolicyError: That request belongs to another conversation`; A6 remains allowed (omission = `main` read-path parity; the record it resolves is main-owned); A1/A5 refused; probe ran to `PROBE-END` (`evidence/ma1-attack-replay-at-fix.txt`).
- Sibling search (all resolution entry points): chat `resolve` (fixed; used by `/api/approvals`, which passes the declared conversation); legacy `/api/approval` singular route (now scoped); `store.resolve_approval` primitive callers — the chat path (guarded) and the coding-adapter expiry-deny, which acts on the run id it owns (reviewed); `Autonomy.resolve_expansion` callers — chat access kind (guarded) and `/api/autonomy` resolve (Work surface, by-id by design; Campaign B reviewed; retained re-audit item); UI callers declare the conversation (KelWorkPanel/KelApprovalCard).
- Residual risk: `/api/state` still returns an unscoped read-only pending-approvals list (display data, no resolution path) — explicit re-audit item, see `05_REMAINING_RISKS.md`.

## AUD-MAJOR-002 — privileged IPC sender validation (REPAIRED, `eaf7bad`)

- Guard truth table + per-channel refusals: `evidence/ma2-newtests-postfix-pass.txt` — focused run 2 files, 25 passed. Spoof shapes exercised per family: subframe, foreign origin, missing `senderFrame`, missing `sender.mainFrame`, frame without url, mismatched frame identity; plus the legit main-frame path.
- Pre-fix discrimination: stash replay (tracked sources reverted) → 4 failed / 14 passed on the in-place channels (`evidence/ma2-newtests-prefix-fail.txt`); extracted families' pre-fix inline handlers guard-free at HEAD (`evidence/ma2-prefix-anchors.txt`).
- TypeScript: `node_modules/.bin/tsc -p tsconfig.json --noEmit` → exit 0 (`evidence/ma2-tsc-postfix.txt`). (`npx tsc` on this machine resolves the deprecated `tsc` stub package — the local binary is the correct invocation; recorded for reproducibility.)
- Desktop regression: `cd desktop && npx vitest run` → 147 passed / 14 files, exit 0 (`evidence/ma2-desktop-vitest-full.txt`; Campaign B baseline at RC was 122/122 — +25 new tests).
- Sibling search: full `ipcMain.*` inventory across `desktop/packages` — the guarded set (KelService 11, feedback 3, `backendStartupIpc` 5, adapter dispatcher 1) plus pet channels (`petManager`, `petConfirmManager`; MINOR-008 scope, reviewed, unchanged). No other privileged registrations exist.

(Results appended per finding as repairs complete.)
