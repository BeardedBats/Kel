# REPAIR RESUME — Campaign C

**Fresh-context re-entry map.** Campaign C repairs the 12 Campaign B findings; nothing is released.

## Where the work lives
- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-final-repair`, branch `repair/v16-final` (base = audit head `a3490095889222862ea13b4b696166c0ddc5bf0f`).
- Repair record: `docs/v1.6/repair-final/` (this directory); findings ledger: `docs/v1.6/audit-final/MASTER_FINDINGS.md` (Campaign C fields appended, never rewriting audit history).
- Read-only references: `kel-v16-final-audit` (audit records + probes + evidence), `kel-ux-v15` (RC @ `08f5667`), `Kel-Repo` (`main` @ `5e76b21`).

## State now
- Integrity verified end-to-end (see `00_REPAIR_BINDING.md` §1): all checks YES.
- Dispositioned: **5/12** — `AUD-MAJOR-001` (`44aee9f`), `AUD-MAJOR-002` (`eaf7bad`), `AUD-MINOR-002` (`7e293ba`), `AUD-MINOR-003` (`91bd869`), `AUD-MINOR-006` (`c056a8a`; 4/4 tests, 26/26 focused, 303/303 cluster, replay refused). Evidence `ma1-*`, `ma2-*`, `mi2-*`, `mi3-*`, `mi6-*`.
- In progress: `AUD-MINOR-001` (commit ledger completeness; documentation-truth cluster).

## Next actions (ordered)
1. `AUD-MINOR-001` → `AUD-MINOR-004` → `AUD-MINOR-005` — commit ledger, package-evidence, corpus drift (documentation truth; never fabricate historical evidence).
2. `AUD-MINOR-007` / `008` / `009` — donor runtime / desktop-pet / builder config (read final Campaign B evidence first; preserve legal attribution).
3. `AUD-SUG-001` — directive docstring vs behavior (record final disposition).
4. Full regression, package build + installed battery, migrations/persistence, isolation checks; finalize `docs/v1.6/POST_REPAIR_RELEASE_CANDIDATE.md`.

## How to verify current state
- `git -C kel-v16-final-repair log --oneline -16`; `git status` clean except declared build artifacts.
- Engine suite: `cd runtime && python -m pytest tests -q`. Desktop: `cd desktop && npx vitest run` + `node_modules/.bin/tsc -p tsconfig.json --noEmit`.
- Campaign B probes: `docs/v1.6/audit-final/probes/`.

## Hard rules (still binding)
- No release, no freeze, no `main` movement, no final independent audit; `HUMAN_VISUAL_GATE` stays PENDING.
- Every repair needs: reproduction, discriminating test, attack replay, evidence, commit — then continue.
