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
| 23:03 | desktop baseline | `bunx vitest run` | 15 files / 156 PASS | pre-D0 tree |
| 23:05 | engine identity | `python -m unittest discover -s tests -p "test_v16_r8_identity.py"` | 3 OK | pins desktop version == engine `__version__` == `1.7.0-dev` |
| 23:05 | new job-label suite | `bunx vitest run tests/unit/job-labels.test.ts` | 5 PASS | HVRA-MINOR-001 |
| 23:06 | desktop after D0 edits | `bunx vitest run` | 16 files / 163 PASS | tsc had found TS7011 → fixed with explicit annotation |
| 23:08 | desktop typecheck (final D0 tree) | `bunx tsc --noEmit` | exit 0 | — |
| 23:08 | desktop full (final D0 tree) | `bunx vitest run` | 16 files / 163 PASS | — |
| 23:09 | focused D0 suites | `donor-policy + job-labels + needs-attention` | 3 files / 24 PASS | donor-policy 11 tests (2 new pins) |
| 23:07→23:19 | engine full suite #1 | `python -m unittest discover -s tests -v` | **1019 tests, 1 failure** | failure = `test_v141_claims` (pre-existing, see ENG-001) |
| 23:11 | claims single file (after re-pin) | `python -m unittest tests.test_v141_claims -v` | 2 OK | — |
| 23:14 | D1 typecheck | `bunx tsc --noEmit` | exit 0 | — |
| 23:14 | D1 focused | `provider-status + job-labels + donor-policy` | 3 files / 27 PASS | provider-status 11 tests |
| 23:15 | D1 full | `bunx vitest run` | 17 files / 174 PASS | — |
| 23:19 | engine full suite #2 (re-run) | `python -m unittest discover -s tests` | **1019 tests OK (275.5s)** | fully green |
| 23:18 | D2 typecheck | `bunx tsc --noEmit` | exit 0 | — |
| 23:18 | D2 full | `bunx vitest run` | 18 files / 177 PASS | includes `update-policy.test.ts` |
