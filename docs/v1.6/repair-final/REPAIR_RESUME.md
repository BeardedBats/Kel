# REPAIR RESUME — Campaign C

**Fresh-context re-entry map.** Campaign C repairs the 12 Campaign B findings; nothing is released.

## Where the work lives
- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-final-repair`, branch `repair/v16-final` (base = audit head `a3490095889222862ea13b4b696166c0ddc5bf0f`).
- Repair record: `docs/v1.6/repair-final/` (this directory); findings ledger: `docs/v1.6/audit-final/MASTER_FINDINGS.md` (Campaign C fields appended, never rewriting audit history).
- Read-only references: `kel-v16-final-audit` (audit records + probes + evidence), `kel-ux-v15` (RC @ `08f5667`), `Kel-Repo` (`main` @ `5e76b21`).

## State now
- Integrity verified end-to-end (see `00_REPAIR_BINDING.md` §1): all checks YES.
- Dispositioned: **2/12** — `AUD-MAJOR-001` REPAIRED (`44aee9f`; focused 28/28, adjacent 129/129, probe §A replay refused). `AUD-MAJOR-002` REPAIRED (`eaf7bad`; desktop vitest 147/147, tsc exit 0, pre-fix replay fails; evidence `ma2-*`).
- In progress: `AUD-MINOR-002` (budget reservation aggregation).

## Next actions (ordered)
1. `AUD-MINOR-002` (budget aggregation) → `AUD-MINOR-003` (credential containment) → `AUD-MINOR-006` (path containment) — security-adjacent MINORs.
2. `AUD-MINOR-001` / `004` / `005` — commit ledger, package-evidence, corpus drift (documentation truth).
3. `AUD-MINOR-007` / `008` / `009` — donor runtime / desktop-pet / builder config.
4. `AUD-SUG-001` — directive docstring vs behavior.
5. Full regression, package build + installed battery, migrations/persistence, isolation checks; finalize `docs/v1.6/POST_REPAIR_RELEASE_CANDIDATE.md`.

## How to verify current state
- `git -C kel-v16-final-repair log --oneline -8`; `git status` clean except declared build artifacts.
- Engine suite: `cd runtime && python -m pytest tests -q`. Desktop: `cd desktop && npx vitest run` + `node_modules/.bin/tsc -p tsconfig.json --noEmit`.
- Campaign B probes: `docs/v1.6/audit-final/probes/`.

## Hard rules (still binding)
- No release, no freeze, no `main` movement, no final independent audit; `HUMAN_VISUAL_GATE` stays PENDING.
- Every repair needs: reproduction, discriminating test, attack replay, evidence, commit — then continue.
