# 04 — REGRESSION (Kel V1.6 human visual repair)

Batteries to run on the repair head (all results recorded here when executed):

## Desktop (`desktop/`)

- TypeScript: `bunx tsc --noEmit` (or `just typecheck`)
- Vitest: `bun run test` (full suite)
- Focused/new tests for this pass:
  - attention action targets the real conversation route (Work → Open the chat)
  - Desktop Pet toggle truthfulness (enable refused → toggle reverts + feedback)
  - any Model page / drawer changes with existing suites

## Engine (`runtime/`)

- Run affected engine suites; full suite if shared contracts/APIs/authorization/routing are touched.
- This pass is presentation/UX on the desktop shell + installer strings; expected engine impact: none.
  (Confirm no engine files touched by diff; record the check.)

## Routes / actions checklist

Open the chat · Permissions actions · Work & context · sidebar routes · settings routes ·
Model controls · Tools · Desktop Pet · Remote · Team route (post-disposition).

## Console

Zero unexplained renderer errors in the installed review build.
