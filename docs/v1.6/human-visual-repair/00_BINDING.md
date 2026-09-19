# 00 — BINDING (human-visual repair, Kel V1.6)

Status: ACTIVE
HUMAN_VISUAL_GATE = PENDING_REVIEW (Nick owns this gate; the agent cannot close it)

## Campaign identity

- Campaign: Kel V1.6 — HUMAN VISUAL REPAIR MARATHON (post-audit polish pass)
- Production target (immutable): `05a076b` (`05a076b3d723ab2c1f3666e6a42193dfc9e502e5`)
- Final pre-repair audit head: `eb4da52b40a2500daae12fe8740823d07a6ad1d8` (branch `audit/v16-postrepair-final`)
- Repair branch: `repair/v16-human-visual`, based at `eb4da52` — the audit corpus is retained and
  production changes begin from the exact audited production tree.
- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-human-visual-fix`
- Verified at start (2026-09-19): `git diff --name-only 05a076b eb4da52` contains only `docs/`
  paths — the production tree at the audit head is identical to the production target.

## Fixed history — do not rewrite

- Do not modify or branch from in-place: `audit/v16-postrepair-final`, `repair/v16-final`,
  `ux/v15-journeys`, `main`, or any protected tag.
- Do not touch the preserved final-audit install (`C:\Users\Nick\KelV16ReviewInstall`) or its
  prepared roots (`C:\Users\Nick\KelV16ReviewRuns\`); the repair review install is separate.
- This pass repairs visuals/UX only. It must not weaken or bypass authorization, approvals,
  capability enforcement, project/conversation isolation, memory, recovery, provider routing,
  Workforce execution, migrations, or package identity.

## Boundaries

- No release, no freeze, no merge to `main`, no tag, no publish.
- The agent may establish `AUTOMATED_VISUAL_REPAIR = PASS` only with recorded evidence.
- `HUMAN_VISUAL_GATE` stays `PENDING_REVIEW` until Nick personally inspects the installed
  repair build.

## Evidence locations

- Human findings: `01_HUMAN_FINDINGS.md`
- Implementation log: `02_IMPLEMENTATION_LOG.md`
- Visual evidence: `03_VISUAL_EVIDENCE.md`
- Regression evidence: `04_REGRESSION.md`
- Package evidence: `05_PACKAGE_EVIDENCE.md`
- Status / resume: `REPAIR_STATUS.md`, `REPAIR_RESUME.md`
