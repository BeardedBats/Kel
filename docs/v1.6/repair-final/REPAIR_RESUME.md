# REPAIR RESUME — Campaign C

**Fresh-context re-entry map.** Campaign C repairs the 12 Campaign B findings; nothing is released.

## Where the work lives
- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-final-repair`, branch `repair/v16-final` (base = audit head `a3490095889222862ea13b4b696166c0ddc5bf0f`).
- Repair record: `docs/v1.6/repair-final/` (this directory); findings ledger: `docs/v1.6/audit-final/MASTER_FINDINGS.md` (Campaign C fields appended, never rewriting audit history).
- Read-only references: `kel-v16-final-audit` (audit records + probes + evidence), `kel-ux-v15` (RC @ `08f5667`), `Kel-Repo` (`main` @ `5e76b21`), `ux-audit` (RC probes + runs; R12 tools patched 2026-09-19).

## State now
- Integrity verified end-to-end (see `00_REPAIR_BINDING.md` §1): all checks YES.
- Dispositioned: **8/12** — `AUD-MAJOR-001` (`44aee9f`), `AUD-MAJOR-002` (`eaf7bad`), `AUD-MINOR-001` (`960e023`), `AUD-MINOR-002` (`7e293ba`), `AUD-MINOR-003` (`91bd869`), `AUD-MINOR-004` (`89ab6ad`), `AUD-MINOR-005` (`8ca6231`), `AUD-MINOR-006` (`c056a8a`). Evidence `ma1-* … mi6-*`.
- In progress: `AUD-MINOR-007/008/009` (donor cluster) — read the final Campaign B evidence first; preserve legal attribution; inspect the built package after repairs.
- Then: `AUD-SUG-001` (directive docstring vs behavior) with a recorded final disposition.

## Next actions (ordered)
1. Donor cluster `007 → 008 → 009`.
2. `AUD-SUG-001`.
3. Full engine battery + desktop battery; package build (§17) + installed battery (§18) with the `04` checklist; replay all Campaign B attacks (§19); finalize `docs/v1.6/repair-final/` corpus (§20) and `docs/v1.6/POST_REPAIR_RELEASE_CANDIDATE.md` (§21).

## How to verify current state
- `git -C kel-v16-final-repair log --oneline -22`; `git status` clean except declared build artifacts.
- Engine: `cd runtime && python -m pytest tests -q`. Desktop: `cd desktop && npx vitest run` + `node_modules/.bin/tsc -p tsconfig.json --noEmit`.
- Gates: `python docs/v1.6/audit-final/tools/reconcile-commit-ledger.py` and `python docs/v1.6/audit-final/tools/check-corpus-staleness.py` (both must PASS).

## Hard rules (still binding)
- No release, no freeze, no `main` movement, no final independent audit; `HUMAN_VISUAL_GATE` stays PENDING.
- Every repair needs: reproduction, discriminating test, attack replay, evidence, commit — then continue.
