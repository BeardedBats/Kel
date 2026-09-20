# 03 — REGRESSION (desktop + engine + installer + routes)

All runs executed by this re-audit in the dedicated worktree `kel-v16-human-visual-reaudit`
(production tree = `6d957ee9…`). No repairs performed.

## Desktop — TypeScript

`cd desktop && bunx tsc --noEmit` → **exit 0 (PASS)**. Log: `evidence/tsc.log`.

## Desktop — Vitest (full)

`bun run test` (vitest run) → **15 files / 156 tests passed** (exit 0) — matches the repair
record's expected `156 full`. Log: `evidence/vitest.log`.

## Focused repair tests

`bunx vitest run tests/unit/donor-policy.test.ts tests/unit/needs-attention.test.ts` →
**2 files / 17 tests passed** (donor-policy 9 — includes the RA-MINOR-003 pet-truth pins and the
installer-branding gate; needs-attention 8 — includes the `/conversation/<donor-id>` expectation).
Matches the repair record's expected `17`. Log: `evidence/focused-tests.log`.

## Engine (`runtime/`)

- No engine file changed in `05a076b..6d957ee9` — `git diff --name-only … -- runtime/` is empty and
  all production changes are confined to `desktop/` (proof: `evidence/delta-scope-proof.txt`).
- The packaged engine remains the audited binary `f525b15b…`; engine tree manifest identical to the
  campaign package (`evidence/pkg-chain-source.txt`). No shared contract/API changed, so a full
  engine-suite rerun was not required by the re-audit instruction; the untouched-tree proof stands.

## Installer smoke replays (re-run independently by this audit)

| Smoke | Mode | Result | Log |
| --- | --- | --- | --- |
| failure messagebox (all 12 scenarios) | compile-only | **PASS** (exit 0; 12/12 codes E1001–E1090 incl. extract-failed missing=Kel.exe) | `evidence/smoke-messagebox.log` |
| self-lock | full | **PASS** (exit 0) | `evidence/smoke-self-lock.log` |
| rstrtmgr UI | compile-only | **PASS** (exit 0) | `evidence/smoke-rtrtmgr.log` → `smoke-rstrtmgr.log` |
| report script | full script | **PASS** (`status=skipped code=E1003 wrapperCode=E1002 copyTextLength=613`) | `evidence/smoke-report.log` |

Summary: `evidence/smokes-reaudit.log`.

## Routes / actions battery

- Source phase (fresh package, dedicated root): campaign harness **25/25 gates PASS, 0 console
  errors** (`evidence/probes-source/kelvis/kelvis-verify.json`); the audit's independent probe
  results are recorded in `evidence/probes-source/own/` and interpreted per finding in
  `02_FINDING_REPLAY.md`.
- Installed phase: see `05_INSTALLED_REVIEW.md`.

## Console

- Renderer console: 0 errors in the campaign-harness source run; 0 page errors in the audit probe
  runs (HTTP status capture included). Any probe-incident artifacts from the audit's own tooling are
  documented in `02_FINDING_REPLAY.md` (none correspond to product behavior).
