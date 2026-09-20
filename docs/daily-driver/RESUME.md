# RESUME — how to continue this marathon (disk-first)

Read order: `MARATHON_STATE.md` → this file → `IMPLEMENTATION_STATUS.md` → `FEATURE_LEDGER.md`.

## Where

- Worktree: `C:\Users\Nick\Desktop\Kel\kel-daily-driver` · branch `dev/daily-driver`.
- Base `37b1f27…`; current HEAD is recorded in `MARATHON_STATE.md`.

## How to continue

1. `cd /c/Users/Nick/Desktop/Kel/kel-daily-driver` and `git status` + `git log --oneline -10`
   (confirm clean tree and latest checkpoint).
2. Open `MARATHON_STATE.md`; continue from **CURRENT ITEM** / **NEXT QUEUE**.
3. Work loop per feature: understand → narrow design → implement → self-review → focused tests →
   realistic journey → record (`TEST_EVIDENCE.md`, `FEATURE_LEDGER.md`) → commit → continue.
4. Update `MARATHON_STATE.md` at every checkpoint (disk is durable state).

## Commands

- Install deps (once per worktree): `cd desktop && bun install`
- Full unit suite: `cd desktop && bunx vitest run`
- Focused tests: `cd desktop && bunx vitest run tests/unit/donor-policy.test.ts tests/unit/needs-attention.test.ts`
- Typecheck: `cd desktop && bunx tsc --noEmit` (exact invocation used is recorded in `TEST_EVIDENCE.md`)
- Engine tests: `cd runtime && python -m unittest discover -s tests` (record actual command used)

## Package / install (final phases)

- Candidate install: `C:\Users\Nick\KelDailyDriverCandidate`
- Candidate data root: `C:\Users\Nick\KelDailyDriverRuns\prepared`
- Do **not** overwrite preserved audit/release-candidate installations.

## Never

- Touch protected refs (`main`, `repair/*`, `audit/*`, `ux/v15-journeys`, tags).
- Publish, tag a release, rewrite history, or start another audit campaign.
- Stop after one feature/suite/package — continue the queue.
