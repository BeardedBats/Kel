# Campaign A baseline — reconciliation notes (2026-09-18)

Recorded by the Program Director at Campaign A entry. Sources: git commands in `kel-ux-v15`,
worktree inspection, `ls-remote origin`, process inspection (tasklist), file mtimes.

## Ownership confirmation

- Single writer confirmed for the Main worktree: no commits beyond the known chain (reflog
  verified), no stash entries, last repo mtime ~13:15Z (the previous director's final state
  update), no live watcher processes (the code-audit `.watch` files are stale since
  2026-09-17T18:09Z; no `.watch` in other worktrees).
- Visual worktree (`kel-v16-visual-fix`) and audit worktree (`kel-v16-code-audit`) are dormant;
  this director line inherits them per the sprint directive ("sole Program Director").

## Worktrees

```
C:/Users/Nick/Desktop/Kel/Kel-Repo              5e76b21 [main]
C:/Users/Nick/Desktop/Kel/kel-rust-audit        9c1e7d0 [audit/rust-runtime]
C:/Users/Nick/Desktop/Kel/kel-ux-v15            fd98cc4 [ux/v15-journeys]      <- THIS
C:/Users/Nick/Desktop/Kel/kel-v16-code-audit    fd04c00 (detached)
C:/Users/Nick/Desktop/Kel/kel-v16-visual-audit  ffeef73 [audit/v16-visual-ux]
C:/Users/Nick/Desktop/Kel/kel-v16-visual-fix    ac85eb3 [ux/v16-visual-fix]
```

## Remote refs (ls-remote origin, 2026-09-18T16:05Z)

- `refs/heads/main` = `5e76b21` (v1.5.0); `refs/heads/ux/v15-journeys` = `fd98cc4`.
- Tags verify: `v1.5.0` peeled `5e76b21`; `v1.6.0-pre1` peeled `f24d9c2` (unchanged).
- `v1.3-dev`/`v1.4-dev` unchanged. Full capture: `remote-refs.txt`.

## Program state at entry

- Phase 5 CLOSED; Phase 5.6 accepted via audit increment 24 (CONTINUE) through `8a2b25d`.
- Docs-only commits above the audited point: `c4ae724`, `5127bac`, `fd98cc4` (per-commit
  `git show --stat` verified).
- Visual: `ux/v16-visual-fix` @ `ac85eb3` (batch 5); not audited; not integrated.
- Rust: NO_MIGRATION_NEEDED_NOW (`kel-rust-audit` @ `9c1e7d0`).
- Open docket: P2 ×10, P3 ×16 (see MAIN_STATUS lists + P2_P3_DISPOSITION.md).

## Baseline test evidence

- `cd runtime && python -m pytest tests -q` (Python 3.14.3, Windows) →
  **878 passed, 10 subtests passed in 251.55s**. Captured in `engine-suite-20260918.txt`.

## Notes for future readers

- `docs/v1.6/AUTO_RESUME.md` top sections are historical; the authoritative state is
  `MAIN_STATUS.md` + the newest AUTO_RESUME sections (Campaign A appended 2026-09-18).
- Publication is never verification (GITHUB_SYNC_POLICY.md).
