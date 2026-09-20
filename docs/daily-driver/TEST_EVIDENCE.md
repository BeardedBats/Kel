# TEST EVIDENCE — `dev/daily-driver`

## Commands used

- Desktop unit (vitest): `cd desktop && bunx vitest run`
- Desktop focused: `cd desktop && bunx vitest run <files>`
- Desktop typecheck: `cd desktop && bunx tsc --noEmit`
- Engine: `cd runtime && python -m unittest discover -s tests` (add `-p "test_x.py"` for one file)

## Baseline (source: final V1.6 re-audit at `6d957ee9…`)

- Desktop tsc PASS; Vitest 15 files / 156 PASS; focused (donor-policy + needs-attention) 17 PASS;
  installed battery 25/25; engine probe healthy; 0 console/page errors.

## Runs (this lane)

| When (local) | Scope | Command | Result | Notes |
| --- | --- | --- | --- | --- |
| 2026-09-19 ~23:03 | desktop baseline | `bunx vitest run` | 15 files / 156 PASS | pre-D0 tree (version bump only) |
| 2026-09-19 ~23:05 | engine identity | `python -m unittest discover -s tests -p "test_v16_r8_identity.py"` | 3 tests OK | pins desktop version == engine `__version__` == `1.7.0-dev` |
| 2026-09-19 ~23:05 | new job-label suite | `bunx vitest run tests/unit/job-labels.test.ts` | 1 file / 5 PASS | HVRA-MINOR-001 |
| 2026-09-19 ~23:06 | desktop after D0 edits | `bunx vitest run` | 16 files / 163 PASS | tsc found TS7011 (fixed with explicit annotation) |
| 2026-09-19 ~23:08 | desktop typecheck (final D0 tree) | `bunx tsc --noEmit` | exit 0 | — |
| 2026-09-19 ~23:08 | desktop full (final D0 tree) | `bunx vitest run` | 16 files / 163 PASS | — |
| 2026-09-19 ~23:09 | focused D0 suites | `bunx vitest run tests/unit/donor-policy.test.ts tests/unit/job-labels.test.ts tests/unit/needs-attention.test.ts` | 3 files / 24 PASS | donor-policy now 11 tests (2 new pins) |
| 2026-09-19 ~23:07 | engine full suite (verbose) | `python -m unittest discover -s tests -v` | IN PROGRESS | result recorded here when complete; one `F` observed in an earlier, killed partial run — identify + resolve before D19 |
