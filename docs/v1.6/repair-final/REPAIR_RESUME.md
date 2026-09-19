# REPAIR RESUME — Campaign C

**Fresh-context re-entry map.** Campaign C repairs the 12 Campaign B findings; nothing is released.

## Where the work lives
- Repair worktree: `C:\Users\Nick\Desktop\Kel\kel-v16-final-repair`, branch `repair/v16-final` (base = audit head `a3490095889222862ea13b4b696166c0ddc5bf0f`).
- Repair record: `docs/v1.6/repair-final/` (this directory); findings ledger: `docs/v1.6/audit-final/MASTER_FINDINGS.md` (Campaign C fields appended, never rewriting audit history).
- Read-only references: `kel-v16-final-audit` (audit records + probes + evidence), `kel-ux-v15` (RC @ `08f5667`), `Kel-Repo` (`main` @ `5e76b21`), `ux-audit` (RC probes + runs; R12 tools patched 2026-09-19).

## State now — **12/12 DISPOSITIONED (all REPAIRED)**
- `AUD-MAJOR-001` `44aee9f` · `AUD-MAJOR-002` `eaf7bad` · `AUD-MINOR-001` `960e023` · `AUD-MINOR-002` `7e293ba` · `AUD-MINOR-003` `91bd869` · `AUD-MINOR-004` `89ab6ad` · `AUD-MINOR-005` `8ca6231` · `AUD-MINOR-006` `c056a8a` · `AUD-MINOR-007/008/009` `197dbff` · `AUD-SUG-001` `6d665b2`.
- All gates green: ledger gate 1:1 · corpus lint PASS · donor tests 5/5 · desktop vitest 152/152 + tsc 0 · per-finding attacks replayed.

## Remaining work (the completion battery — §15→§21)
1. §15 engine suite: `cd runtime && python -m pytest tests -q` → `evidence/final-engine-suite.txt` (record exact counts).
2. §16 desktop battery: `cd desktop && npx vitest run` + `node_modules/.bin/tsc -p tsconfig.json --noEmit` → `evidence/final-desktop-battery.txt`.
3. §19 attacks: re-run `python ../docs/v1.6/audit-final/probes/auditor_probe_1.py` at the final head → `evidence/final-attack-replay.txt`; per-finding replays already retained (`ma1-* … ms1-*`).
4. §17 package build from the exact repair HEAD (engine build → vite → electron-builder with the Kel default config; retain command + full log); §18 install to `C:\Users\Nick\KelRepairInstall` (gated `r12-installed-probe.cjs`; uninstall log retained) — execute the `04_PACKAGE_EVIDENCE.md` checklist.
5. §20 finalize corpus; §21 create `docs/v1.6/POST_REPAIR_RELEASE_CANDIDATE.md` (`POST_REPAIR_V1_6_HEAD=<sha>`; Human Visual = PENDING; final re-audit = NOT STARTED; release/freeze = NOT STARTED; frozen refs UNCHANGED).

## How to verify current state
- `git -C kel-v16-final-repair log --oneline -30`; `git status` clean except declared build artifacts.
- Gates: `python docs/v1.6/audit-final/tools/reconcile-commit-ledger.py` + `python docs/v1.6/audit-final/tools/check-corpus-staleness.py` (both must PASS).

## Hard rules (still binding)
- No release, no freeze, no `main` movement, no final independent audit; `HUMAN_VISUAL_GATE` stays PENDING.
