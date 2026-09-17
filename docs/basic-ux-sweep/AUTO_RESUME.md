# Basic UX sweep — AUTO_RESUME

## Where this program stands (2026-09-17)

- Audit of the pre-fix packaged RC complete (`evidence/audit/…`); every checklist area classified in
  `01_EXPECTATION_MATRIX.md`.
- Implemented: default model + per-chat override (engine + UI, 11 unit tests), theme foundation
  colors, draft persistence, palette actions, global search, backup/restore + data folder.
- **Shipped artifact: `dist/package-final6/win-unpacked`** (`KelEngine.exe` sha256 `de973cf6…`,
  `app.asar` `edfd758f…`, installer `86290d9c…`). The as-built battery results, the defects found by
  that battery (F11–F16) and their fixes are in `15_FINAL_VERDICT.md` + `evidence/final/`.
- Engine suite: `runtime && python -m pytest tests -q` → 529 passed (10 subtests). Renderer: `desktop && bunx tsc --noEmit` → 0 errors.

## If work resumes here

1. Worktree `C:\Users\Nick\Desktop\Kel\kel-ux-v15` (`ux/v15-journeys`).
2. Build the engine (`scripts/build-runtime.ps1`), then `desktop && bun run package` and
   electron-builder with `--config.directories.output=<fresh dir>` (never rebuild while a
   packaged scenario is running; the host GUI can hold `dist/package/app.asar`).
3. Scenarios: `sweep-seed` → python seeder → `sweep2`/`sweep3`/`sweep4`, plus the standing battery
   (`transcription`, `hardening`, `voice-vetting`, `vetting`, `first-run`, `tour`, `settings`,
   `palette`, `keyboard`, `readability`, `sider`, `maintext`) and the a11y probes. Scratch runner:
   `C:\Users\Nick\Desktop\Kel\ux-audit\run-f3-battery.sh` (edit `APP` to the artifact under test).
4. Probes must walk shadow roots: assistant replies render through `MarkdownView`/`ShadowView`, so a
   light-DOM `innerText`/`querySelectorAll` probe reports empty text for content that is on screen (F15).
5. Remaining honest marks: artifacts browser, activity feed, notification live behaviour, retry/stop
   live behaviour — all provider-dependent or optional (see the matrix and 14_FINDINGS_AND_FIXES).
