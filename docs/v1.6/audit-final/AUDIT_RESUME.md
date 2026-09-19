# AUDIT RESUME — Campaign B

## Where to work
- Audit worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-final-audit`, branch `audit/v16-final` (audit records only).
- RC source of truth (read-only for Campaign B): `C:\Users\Nick\Desktop\Kel\kel-ux-v15` at `08f56673…` on `ux/v15-journeys`.
- Durable audit output: `docs/v1.6/audit-final/` inside the audit worktree; raw evidence under `evidence/` (keep large logs on disk, not in chat).

## How to resume
1. `cd` to the audit worktree. Confirm `git status` shows only audit-doc changes and `git rev-parse --abbrev-ref HEAD` = `audit/v16-final`.
2. Re-verify the RC target has not moved: `git rev-parse ux/v15-journeys` == `08f56673ea93ed84568018937bb190e0a5acd71b`, and `git ls-remote origin refs/heads/ux/v15-journeys` matches (no force-push).
3. Read `AUDIT_STATUS.md` for the current pass and counters; continue from its "Next action".
4. Record every finding in `MASTER_FINDINGS.md` with the Campaign B schema (stable `AUD-*` IDs; severity BLOCK/MAJOR/MINOR/SUG; evidence; repro; acceptance criteria; regression-test requirement). Do NOT fix anything.
5. Keep per-area audit docs (`01…20`) and evidence up to date as passes complete; commit audit docs to `audit/v16-final` as milestones.

## Hard rules (do not violate)
- No production fixes anywhere; no edits outside `docs/v1.6/audit-final/` in the audit worktree (plus disposable fixtures for probes).
- The audit target does not move. Never amend/rewrite/merge the RC; never advance `ux/v15-journeys`, `main`, or frozen tags.
- One serious bug does not end the audit; continue to 100% declared scope.
- Human Visual gate stays PENDING unless Nick explicitly supplies that judgment.
- Campaign A claims are hypotheses until independently reproduced or inspected.

## Next concrete action
- See `AUDIT_STATUS.md` § Next action.
