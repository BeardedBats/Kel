# Release hardening — AUTO_RESUME

## Final state (2026-09-16)

- Phase A verdict: **CONTINUE** (transcription review round 2: all fixes verified; P3 cleanups done).
- Phase B: battery green on the as-built package; evidence archived under `docs/release-hardening/evidence/`.
- Branch: `ux/v15-journeys`; `dist/package/win-unpacked` + NSIS installer built after the last source change.
- Standing rule honored: no tag, no freeze; frozen V1.5 untouched.

## If work resumes here

1. Worktree `C:\Users\Nick\Desktop\Kel\kel-ux-v15`; build with
   `desktop && bun run package && electron-builder --config kel-builder.json --win --x64`.
2. Engine: `scripts/build-runtime.ps1` (its output is picked up by electron-builder extraResources).
3. E2E: `NODE_PATH=… node packaging/ux-audit.cjs <app> <root> <out> <scenario>`; run scenarios
   strictly sequentially — never rebuild while a packaged scenario is running (EBUSY).
4. Open limitations and next-step recommendations: `10_RELEASE_READINESS.md`.

## Artifact note (2026-09-16)

- The verified artifact of this program is `dist/package-final` (fresh full build after the last
  source edit); `09_PACKAGED_ACCEPTANCE.md` records the runs against it.
- `dist/package` is one renderer edit behind: its `app.asar` is held by a lingering handle from the
  host environment (identified with the Windows Restart Manager: the GUI host process), so
  electron-builder cannot replace it in place. Rebuilding in place will succeed after a host
  restart; until then build with an output override:
  `electron-builder --config kel-builder.json --config.directories.output=<fresh dir> ...`.
- Never rebuild while a packaged scenario is running — that produced a real EBUSY failure and a
  half-removed app during this program (lesson recorded in 09).

