# Kel V1.4 — Baseline Screenshots (V1.3, frozen package)

Date: 2026-09-15 · Captured by: `packaging/capture-screens.cjs` (Playwright Electron)
Package: a **copy** of `Kel Releases\Kel-V1.3-Frozen` at `dev-tools/runs/v13/pkg` (the original is never launched or written).

## What is here

- `v13-empty-*.png` — 30 views on a fresh data root (empty states).
- `v13-fixture-*.png` — 30 views on a seeded data root (populated: conversations, a PAUSED job,
  an AWAITING_USER job with a PENDING approval, mixed-trust memory records).
- `v13-*-manifest.json` — per-view metadata: view name, requested size, actual inner size, route
  hash, byte size, text sample, renderer errors, engine pid/version, shutdown outcome.
- `v13-*-texts.jsonl` — full captured innerText per view (audit + regression text evidence).
- `v13-*-discovery.json` — interactive elements (buttons/labels) observed at boot.

## Isolation and safety (applies to every capture run)

- The frozen package is copied; only the copy is launched.
- `KEL_DATA_DIR`, `KEL_HOST_DATA_DIR`, `AIONUI_E2E_TEST=1`, `AIONUI_E2E_USER_DATA_DIR` all point
  inside the run data dir; live user data is never touched.
- Windows are parked offscreen and removed from the taskbar; no focus is taken; no desktop input.
- Bounded shutdown; task-owned leftovers are killed; the zero-orphan check is recorded in each manifest.

## Regenerate

    PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright \
    node packaging/capture-screens.cjs <appDir> <dataDir> <outDir> --tag v13-fixture \
      --widths 1440x900,1280x720,1920x1080,2560x1440,1024x768 --explore

For populated runs, seed first:
`python runtime/tools/seed_ui_fixture.py --data <dataDir> --project-root <fixture-project-dir>`
(refuses to run outside `dev-tools` run directories).
