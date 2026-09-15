# KEL V1.4 — BASELINE (Gate 0 verification)

Date: 2026-09-15 (America/New_York) · Session: V1.4 autonomous session #1
Status: **VERIFIED** — repo refs, tag, frozen hashes, and test baseline confirmed this session.

## 1. Repository refs (verified this session)

| Ref | Commit | Note |
|---|---|---|
| `main` / `origin/main` | `b6974cf` | Current tip; 4 commits ahead of the v1.3.0 tag |
| `v1.3.0` (annotated) | `b3c7c24` | PR #1 merge (v1.3-dev → main); matches the brief's "current main commit" |
| `v1.3-dev` / `origin/v1.3-dev` | `dd67ef4` | Matches the brief |
| `v1.4-dev` (new) | branched from `b6974cf`, pushed to origin | V1.4 work branch |
| remote | `https://github.com/BeardedBats/Kel` | push verified this session (`v1.4-dev`) |

**Documented delta vs the brief:** the brief lists `main = b3c7c24`; actual `main` is `b6974cf`,
four commits later (`ab4aef0`, `c2d0c92`, `507220f`, `b6974cf` — Söhne / SF Pro Text font work,
PRs #2/#3, recorded in the frozen manifest as "owner's decision"). Benign, non-destructive,
expected. `v1.4-dev` therefore branches from `b6974cf`.

## 2. Frozen release integrity (3/3 PASS)

`C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.3-Frozen` — read-only check (`sha256sum`):

| File | SHA-256 (prefix) | Result |
|---|---|---|
| `Kel.exe` | `e048632e03fabc96…` | PASS |
| `resources/app.asar` | `cd0d51cb3f4a69af…` | PASS (font amendment hash) |
| `resources/kel-engine/KelEngine.exe` | `8ed30d3d09fb8bbe…` | PASS |

V1, V1.1, V1.2 frozen archives present; nothing under `Kel Releases/` was written.

## 3. Test baseline (green)

- Command: `cd runtime && python -m pytest tests/ -q` (with `PYTHONDONTWRITEBYTECODE=1`, `KEL_SKIP_TELEMETRY=1`)
- Result: **267 passed, 10 subtests passed in 55.58s**, exit 0 — exactly the V1.3 manifest claim.
- Suite is hermetic (temp dirs + fake providers; no network or API keys) per README.
- Environment: Windows 10/11 x64 · Python 3.14.3 · pytest 9.0.3 · Node 24.18.0 · npm 11.16.0 · git 2.53.0 · `gh` present (push verified).

## 4. Dogfood isolation evidence

Session 1 (verification):
- No `Kel.exe` / `KelEngine.exe` / Electron process was running at session start; none was started.
- No user data directories were read or written; no window was launched, so no focus was taken.
- Tests ran hermetic (temp dirs); frozen releases were only hashed (read-only).

Session 2 (packaged captures):
- The frozen package was **copied** to `dev-tools/runs/v13/pkg`; only the copy was launched. Nothing under `Kel Releases/` was written.
- Data, host state, and shell user-data were redirected into per-run directories: `KEL_DATA_DIR`, `KEL_HOST_DATA_DIR`, `AIONUI_E2E_TEST=1`, `AIONUI_E2E_USER_DATA_DIR`.
- Windows were parked offscreen (`setPosition(-32000,-32000)`, `setSkipTaskbar(true)`); no focus was taken; no synthetic input reached the desktop.
- Both packaged runs ended cleanly (`engineStopped: true`, `appExitCode: 0`); no orphan processes remained (process list re-checked).

## 5. Toolchain (installed 2026-09-15, session 2 — portable, no registry/PATH changes)

| Tool | Version | Location |
|---|---|---|
| Bun (portable binary) | 1.4.2 | `C:\Users\Nick\Desktop\Kel\dev-tools\bun\bun.exe` |
| Playwright (browser downloads skipped) | 1.63.0 | `C:\Users\Nick\Desktop\Kel\dev-tools\playwright\node_modules` |

Still open before build gates: `bun install` for `desktop/` (run when the first UI change lands) and
PyInstaller availability for runtime packaging (checked at the build gate).

## 6. UI baseline captures (session 2 — COMPLETE)

- Harness: `packaging/capture-screens.cjs` (see §7). Two runs, **30 captures each** (`v13-empty`,
  `v13-fixture`) across five widths (1280×720, 1440×900, 1920×1080, 2560×1440, 1024×768-class),
  zero console/page errors, zero blank captures, clean shutdown recorded in the manifests.
- Evidence set: `docs/v1.4/screenshots/baseline/` — PNGs + per-run `manifest.json` (view, size, route
  hash, text sample, errors) + `texts.jsonl` (full text per view) + `discovery.json` (interactive elements).
- Screen inventory (updated with captured routes): `KEL_V1.4_SCREEN_INVENTORY.md`.
- Audit notes + limitations: `KEL_V1.4_UI_AUDIT.md`.

## 7. Screenshot harness + fixtures (session 2)

- **Harness**: `packaging/capture-screens.cjs` — launches a package copy via Playwright Electron with
  full isolation (env redirected into the run data dir), parks windows offscreen, captures views +
  metadata, and records engine-shutdown outcomes (bounded close; task-owned leftovers killed; watchdog).
- **Fixture generator**: `runtime/tools/seed_ui_fixture.py` — seeds conversations, messages, a PAUSED
  job, an AWAITING_USER job with a PENDING approval, and mixed-trust memory records through production
  Store/Context/Memory paths. Refuses to run outside `dev-tools` run directories.
- **Reproduce**:

      node packaging/capture-screens.cjs <appDir> <dataDir> <outDir> --tag v13-fixture \
          --widths 1440x900,1280x720,1920x1080,2560x1440,1024x768 --explore

  with `PLAYWRIGHT_MODULE` pointing at the dev-tools Playwright install.

## 8. V1.3 source ↔ frozen-package provenance (resolved)

- `v1.3.0` (annotated) → `b3c7c24` (PR #1 merge). The tag is **not rewritten** and no replacement
  historical tag exists.
- After the tag, `main` gained four font-related commits (owner's decision): `ab4aef0`, `c2d0c92`
  (PR #2 merge), `507220f`, `b6974cf` (PR #3 merge).
- The frozen package records the change as an amendment: `resources/app.asar` rebuilt with the fonts
  (hash `cd0d51cb…`, verified 3/3 in §2); `Kel.exe` + `KelEngine.exe` unchanged.
- **Closest source correspondence: `main` @ `b6974cf`** (the post-font tree). Byte reproducibility is
  not claimed (README "Reproducibility limits"); correspondence is tree/behavior-level. `v1.4-dev`
  branches from the same commit, so before/after comparisons share one source lineage.
- The frozen package itself remains the **visual baseline** because it is the actual shipped artifact
  (its asar embeds the runtime font registration).

---
*Method note: every claim in this file was produced by commands run in this session; nothing is
copied from the brief without verification.*
