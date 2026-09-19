# REPAIR RESUME — Campaign C

**Fresh-context re-entry map.** Campaign C repairs the 12 Campaign B findings; nothing is released.

## Where the work lives
- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-final-repair`, branch `repair/v16-final` (base = audit head `a3490095889222862ea13b4b696166c0ddc5bf0f`).
- Repair record: `docs/v1.6/repair-final/` (this directory); findings ledger: `docs/v1.6/audit-final/MASTER_FINDINGS.md` (Campaign C fields appended, never rewriting audit history).
- Read-only references: `kel-v16-final-audit` (audit records + probes + evidence), `kel-ux-v15` (RC @ `08f5667`), `Kel-Repo` (`main` @ `5e76b21`), `ux-audit` (RC probes + runs; R12 tools patched 2026-09-19).

## State now
- Integrity verified end-to-end (see `00_REPAIR_BINDING.md` §1): all checks YES.
- Dispositioned: **11/12** — all MAJORs + `AUD-MINOR-001…009` except none; remaining: `AUD-SUG-001`. Key commits: `44aee9f`, `eaf7bad`, `7e293ba`, `91bd869`, `c056a8a`, `960e023`, `89ab6ad`, `8ca6231`, `197dbff`.
- In progress: `AUD-SUG-001` (directive docstring vs behavior) — then the completion battery.

## Next actions (ordered)
1. `AUD-SUG-001` — narrow correction + final disposition row.
2. Full engine battery (§15) + desktop battery (§16), replay all Campaign B attacks (§19).
3. Package build (§17) + installed battery (§18) executing the `04_PACKAGE_EVIDENCE.md` checklist; then finalize `05`, corpus (§20), `POST_REPAIR_RELEASE_CANDIDATE.md` (§21).

## How to verify current state
- `git -C kel-v16-final-repair log --oneline -26`; `git status` clean except declared build artifacts.
- Engine: `cd runtime && python -m pytest tests -q`. Desktop: `cd desktop && npx vitest run` + `node_modules/.bin/tsc -p tsconfig.json --noEmit`.
- Gates: `python docs/v1.6/audit-final/tools/reconcile-commit-ledger.py` and `python docs/v1.6/audit-final/tools/check-corpus-staleness.py` (both must PASS).

## Hard rules (still binding)
- No release, no freeze, no `main` movement, no final independent audit; `HUMAN_VISUAL_GATE` stays PENDING.
- Every repair needs: reproduction, discriminating test, attack replay, evidence, commit — then continue.
