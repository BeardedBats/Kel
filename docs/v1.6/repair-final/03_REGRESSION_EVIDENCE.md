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

## AUD-MINOR-002 — budget reservation aggregation (REPAIRED, `7e293ba`)

- Reproduction: `evidence/mi2-prefix-attack.txt` (probe §E at the unfixed state): E5 refused; E6 cost-1 accepted (tokens/wallclock disclosed); E7 cost-8 accepted after cost-1 (cumulative 9 vs envelope 8).
- Discriminating tests: `ReservationAccountingTests` + delegation cumulative test — 9/9 post-fix (`mi2-newtests-postfix-pass.txt`), 5 fail pre-fix with the fix stashed (`mi2-newtests-prefix-fail.txt`).
- Focused suites: `tests/test_workforce_assignment.py` + `tests/test_v16_r1_authority.py` → 65/65 (`mi2-focused-suite.txt`).
- Cluster: workforce set (assignment/schemas/learning/parallel/assurance/d1/d2) + r1 → 299/299 in 95s (`mi2-adjacent-suite.txt`).
- Attack replay: `mi2-postfix-attack.txt` — E7 now refused: `Reserved cost 8.0 exceeds the remaining job budget 7.0`; E5 unchanged; E6 unchanged (disclosed policy).
- Promotion probe (claiming): `mi2-claiming-probe.txt` — planning reservation 4 on budget 4 accepted; execution spend caps at the envelope (m3 refused, "Execution and verification budget exhausted"); `spent + reserved <= budget` holds — no re-grade.

## AUD-MINOR-003 — native child credential containment (REPAIRED, `91bd869`)

- Reproduction: `evidence/mi3-prefix-attack.txt` (probe §G pre-fix): G4 — `DEEPSEEK_API_KEY` present in both native children; G1–G3 correct.
- Discriminating tests: `tests/test_v15_credentials.py` 9/9 post-fix (`mi3-newtests-postfix-pass.txt`); 3 new tests fail pre-fix with the fix stashed (`mi3-newtests-prefix-fail.txt`).
- Cluster: credentials + r7 credentials + providers → 34/34 (`mi3-adjacent-suite.txt`).
- Attack replay: `mi3-postfix-attack.txt` — G4 DeepSeek absent from both children; G1–G3 unchanged.
- Boundary evidence: spawned-process check (`test_a_spawned_native_child_process_sees_only_its_own_key`) observes only `ANTHROPIC_API_KEY` inside a real child process.

## AUD-MINOR-006 — delegation containment resolves `..` (REPAIRED, `c056a8a`)

- Reproduction: `evidence/mi6-prefix-attack.txt` — `src/../secrets` was contained under `src` pre-fix; post-fix `evidence/mi6-postfix-attack.txt` refuses it and behaves as documented for the whole traversal matrix.
- Discriminating tests: 4/4 post-fix (`mi6-newtests-postfix-pass.txt`); 3 fail pre-fix with the fix stashed (`mi6-newtests-prefix-fail.txt`).
- Focused file: `tests/test_v16_r1_authority.py` → 26/26 (`mi6-focused-file.txt`).
- Cluster: r1 + workforce set → 303/303 (`mi6-adjacent-suite.txt`).
- End-to-end consumer confirmation: issuance (`validate_task_contract`) refuses `src/../secrets` against the declared boundaries and against the delegator (test in `ContractParentAuthorityTests`).

## AUD-MINOR-001 — commit-ledger reconciliation (REPAIRED, `960e023`)

- Gate before: `evidence/mi1-ledger-check-prefix-fail.txt` — 12 unlisted commits + 2 malformed rows against `git rev-list 8a2b25d..08f5667` (73 commits).
- Gate after: `evidence/mi1-ledger-check-postfix-pass.txt` — `PASS - 73 commits ... every row well-formed, 1:1`.
- Gate script: `docs/v1.6/audit-final/tools/reconcile-commit-ledger.py` (exit 1 on unlisted/placeholder/wrong-parent rows; runnable at any RC head).

## AUD-MINOR-004 — R12 evidence tooling (REPAIRED, `89ab6ad`)

- Gate discrimination: `evidence/mi4-gate-discrimination.txt` — r12-fresh `GATE: FAIL` exit 1 (attentionVisible=false, aboutLogoLoaded=false); r12-fresh2 `GATE: PASS` exit 0; repo copy PASS.
- Integrity re-run at repair head: `evidence/mi4-integrity-repair-head.txt` — `INTEGRITY: PASS dirty=0 actionable_hits=0` (branch `repair/v16-final`, head `960e023`).
- Script hashes: `evidence/mi4-script-hashes.txt`.
- Remaining executions (build log, gated installed probe, uninstall log, final integrity re-run) tracked in `04_PACKAGE_EVIDENCE.md`.

## AUD-MINOR-005 — corpus reconciliation (REPAIRED, `8ca6231`)

- Pre-fix: `evidence/mi5-lint-prefix-fail.txt` — `CORPUS LINT: FAIL (source: HEAD)` with 25 stale/missing markers across the six corpus files.
- Post-fix: `evidence/mi5-lint-postfix-pass.txt` — `CORPUS LINT: PASS (6 files checked)`.
- Regression gates re-run: ledger gate `PASS — 73 commits … 1:1`; corpus gate `PASS`.
- Gate script: `docs/v1.6/audit-final/tools/check-corpus-staleness.py` (`--source <rev>` discriminator).

## AUD-MINOR-007/008/009 — donor cluster (REPAIRED, `197dbff`)

- Provenance: `evidence/mi7-aioncore-provenance.txt` — `provenance.json` recorded (v0.2.2, iOfficeAI/AionCore); staged vs packaged-final16 `aioncore.exe` sha256 identical (`67eb02774bab3855b759ec9756c2e540cd17b64b850407fa4b8bad07fd8a0892`).
- Pet policy: `evidence/md-donor-postfix-pass.txt` — donor tests 5/5 post-fix; `md-donor-prefix-fail.txt` — 3 fail pre-fix (stash replay).
- Build identity: pinned by the same suite (`kel-builder.json` is the default; identity assertion runs pre-build).
- Regression: `evidence/md-donor-full-vitest.txt` — desktop vitest 152/152 (15 files); `tsc --noEmit` exit 0.
- Decisions + reachability lists: `06_DONOR_DISPOSITIONS.md`.

(Results appended per finding as repairs complete.)
