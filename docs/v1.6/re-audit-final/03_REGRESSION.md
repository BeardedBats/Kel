# 03 — REGRESSION (final re-audit)

All runs executed by this audit in `kel-v16-postrepair-audit` (production tree == `05a076b`).
Full raw outputs under `evidence/`.

## Engine — complete suite

- `python -m pytest tests -q` from `runtime/`:
  **`1019 passed, 10 subtests passed in 287.07s`** — identical to the Campaign C claim
  (`evidence/ra-engine-suite.txt`). Collection count and subtest count match exactly.

## Engine — hostile/focused suites

- Targeted files re-run as part of the full suite (approvals, authority R1, workforce assignment,
  credentials, capabilities, autonomy, coding, continuation, memory, workforce, transcription,
  vetting, parallel, recovery — the repository's own hostile corpora collected in `runtime/tests`).
- First-party attack batteries (this audit) run green on the fixed tree:
  `probes/ra_attack_engine.py` (24/24) and `probes/ra_attack_engine2.py` (budget/credentials/
  path/wording; all green except the two recorded findings, below). Evidence:
  `evidence/ra-attack-major1.txt`, `evidence/ra-attack-major2.txt`.

## Negative controls (would the tests have failed before the repair?)

Pre-fix base worktree at `a349009` (Campaign B head), post-fix test files copied in, targeted run:

| Area | Pre-fix result |
|---|---|
| Approvals cross-scope (4 tests) + legacy-route test | **FAIL** (omission/cross-declared resolutions succeeded) |
| Credentials child-env (3 tests) | **FAIL** |
| Budget accounting (4 tests) | **FAIL** |
| Path containment (`..` lexical, normalization table, end-to-end escape) | **FAIL** |
| **Total** | **15 failed, 52 passed** — `evidence/ra-negctl-engine-prefix.txt` |

Desktop negative control: mutation replay (guards -> allow-all; pet policy -> enabled) produced
**19 failed / 11 passed** across `ipc-sender-channels`, `sender-guard`, `donor-policy` —
`evidence/ra-negctl-desktop-mutation.txt`. Verdict: discriminating (see `02_SECURITY_AUTHORITY.md`).

## Desktop — TypeScript + Vitest

- `npx vitest run`: **15 files, 152 passed (152)** — identical to the Campaign C claim.
  Evidence: `evidence/ra-desktop-tests.txt` (vitest section).
- TypeScript (`tsc --noEmit`): root `tsconfig.json` exit 0; `packages/web-host` exit 0;
  `packages/web-cli` exit 0 — `evidence/ra-desktop-tsc.txt` (root) + console transcript.

## Traceability / corpus checks (AUD-MINOR-001/004/005 replay)

- **Commit ledger** (`tools/reconcile-commit-ledger.py`): `LEDGER RECONCILIATION: PASS — 73
  commits in 8a2b25d..08f5667; every row well-formed, 1:1` (re-run by this audit).
- **Corpus staleness lint** (`tools/check-corpus-staleness.py`): `CORPUS LINT: PASS (6 files)`.
- **Migration max / next-free**: fresh store via `Service(tmp)` applies migrations with
  **max version 21** (next free 22), matching the corpus claim. Per-module `MIGRATION_VERSION`
  max is 21 (`assignment.py`).
- **R12 gate discrimination** (AUD-MINOR-004): re-gated the retained run JSONs with
  `ux-audit/r12-assert-gate.cjs` (hashes verified against `mi4-script-hashes.txt`):
  Campaign-era known-bad `runs/r12-fresh` -> **GATE FAIL exit 1** (`attentionVisible=false`,
  `aboutLogoLoaded=false`); `runs/r12-fresh2` -> **GATE PASS exit 0**; the repo evidence copies
  -> PASS. Additionally this audit ran a **mutation probe** on a pristine copy of the repaired
  fresh-run JSON: flipping `attentionVisible`, adding a `consoleErrors` entry, or lowering
  `engineVersion` each produced GATE FAIL exit 1. The gate observes real content and cannot
  produce a vacuous pass.
- Historical-claims hygiene: this re-audit did **not** re-label any historical evidence; all
  Campaign C records were treated as evidence to verify (and are cited as theirs where used).

## Build-toolchain findings that condition package identity

- PyInstaller 6.19.0 output is **not byte-reproducible**: two consecutive local builds of the same
  spec produced `KelEngine.exe` differing in **4 bytes** (PE build-stamp region offsets
  `0x101/0x151/0x3DAC5`), and this audit's build differs from Campaign C's in **6 bytes at the
  same offsets**. Consequence (recorded for `04_PACKAGE_IDENTITY.md`): identity must be bound
  *within one build chain* (built -> staged -> packaged -> installed), which is what this audit
  verifies; cross-build byte equality is not a valid gate.
