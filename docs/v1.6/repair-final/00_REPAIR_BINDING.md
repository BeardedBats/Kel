# 00 — REPAIR BINDING (Campaign C)

**Campaign:** Kel V1.6 — Campaign C, 100% repair of the Campaign B master findings
**Mode:** REPAIR + PROVE — reproduce, root-cause, narrow repair, discriminating test, replay, evidence, commit.
**Not in scope:** release, freeze, `main` movement, final independent re-audit, human visual judgment.

## 1. Authoritative inputs (verified, not trusted)

| Item | Declared | Independently observed (2026-09-19) | Verdict |
|---|---|---|---|
| Campaign A PRE-AUDIT RC | `08f56673ea93ed84568018937bb190e0a5acd71b` | commit exists; subject `docs(v1.6): PRE_AUDIT_V1_6_HEAD — Campaign A complete; pre-audit release candidate ready` | YES |
| Audit branch / head | `audit/v16-final` / `a349009` | `a3490095889222862ea13b4b696166c0ddc5bf0f`; audited worktree tree == HEAD (tracked-clean) | YES |
| Audit diff scope | audit records only | `git diff --name-only 08f56673…a349009` → 135 files, 100% under `docs/v1.6/audit-final/`; files outside the audit corpus = 0 | YES |
| RC descends into audit head | required | `git merge-base --is-ancestor 08f56673… a349009` → true | YES |
| No Campaign B production repair | required | zero production paths in the RC→audit diff; every entry is an add under the audit corpus | YES |
| `MASTER_FINDINGS.md` ledger | 12 findings (0/2/9/1) | 12 findings present; every one carries Campaign C `NOT_STARTED` | YES |
| RC worktree | immutable target | `kel-ux-v15` @ `08f5667`, `git status` clean | YES |
| `main` | unchanged | `Kel-Repo` @ `5e76b21`; local == `origin/main` (`git ls-remote`) | YES |
| Frozen refs | unchanged | `v1.5.0` obj `068cd26…`→`5e76b21`; `v1.6.0-pre1` obj `ceac727…`→`f24d9c2`; all heads/tags byte-match `evidence/git-refs-full.txt` + `ls-remote` | YES |
| Remote identity | `BeardedBats/Kel` | `origin` = `https://github.com/BeardedBats/Kel.git`; `ls-remote` matches local (no force-push) | YES |

Recorded notes (not blockers):
- The audit worktree carries one declared untracked build area: `build-output/` (1.2 GB of auditor PyInstaller/package/negative-control outputs; declared in `AUDIT_STATUS.md` §Environment; partially gitignored). Preserved untouched.
- The `main` worktree carries pre-existing untracked workspace files (`.agents/`, `Agents.md`); not produced by this campaign; refs verified unchanged.

## 2. Campaign C worktree

- Path: `C:\Users\Nick\Desktop\Kel\kel-v16-final-repair`
- Branch: `repair/v16-final`, created from audit head `a349009…` (intentional: the audit records and finding ledger travel forward; the production baseline is the RC).
- Hard rules: do not modify `kel-v16-final-audit`, `kel-ux-v15` (`ux/v15-journeys`), `main`, or any frozen tag; no release; no final audit.

## 3. Per-finding protocol (binding)

REPRODUCE → CONFIRM ROOT CAUSE → DESIGN NARROW REPAIR → ADD DISCRIMINATING TEST → IMPLEMENT → FOCUSED TEST → ADJACENT REGRESSION → RE-RUN ORIGINAL CAMPAIGN B ATTACK → RECORD EVIDENCE → COMMIT → CONTINUE.

Dispositions: `REPAIRED` · `NOT_REPRODUCIBLE` · `INVALID_FINDING` · `ACCEPTED_DEFERRED` (exceptional; never for BLOCK/MAJOR without proof).
