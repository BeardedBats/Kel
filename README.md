# Kel

Kel is Nick's personal AI assistant for Windows: **one capable assistant with hidden orchestration**.
You tell Kel what you want in a chat; Kel answers directly or hands real work to the background, staffs
it with the right models (a Builder, a Verifier, an independent Oracle review when it matters), checks the
result against evidence, and reports truthfully what happened. Work survives closing the window and can be
resumed. Kel acts with full access by default (D-64) and applies a verified change on its own with Undo
(D-65); anything it cannot verify waits for Nick.

What you see in V2:

- **Chat** with work cards across the top (D-68): each piece of work Kel's staff is doing, its progress
  and team, and "Needs you" questions answered right on the card (D-70).
- **Projects** (D-54) as the one context boundary, **Activity** for everything that happened,
  **Scheduled tasks** that run as engine Recipes (D-57), **Recipes**, **Knowledge**.
- **Connections** to services Nick uses (GitHub, Stripe, Figma, ClickUp, Discord, Google Drive, Pitcher
  List, Raptive), **Ramble** (voice transcription), **Kibble** (capture a fix while using Kel).
- **Settings** trimmed to what Kel has built (D-60), including **Staff & models** (which model each staff
  role runs on). English only (D-61). No updater and no Desktop Pet (D-56).

The product constitution is `KEL_CANONICAL_HANDOFF.md` (next to this repository, in
`C:\Users\Nick\Desktop\Kel`); decisions are in `docs/v2/DECISIONS.md`.

## Layout

    C:\Users\Nick\Desktop\Kel\
      Kel\     this repository (branch main, github.com/BeardedBats/Kel)
      App\     the one installed Kel (not in git)
      Data\    the one durable user-data root (not in git)
      Tools\   reusable tooling, rollback copies

Inside the repository:

    runtime/     the Kel engine (Python): kel/ package, tests/, PyInstaller spec (KelEngine.exe)
    desktop/     the Electron desktop shell (a fork of AionUI) and its tests (tests/unit, tests/e2e)
    packaging/   asar tools, packaged-app probes and audits (Playwright scripts)
    scripts/     PowerShell build/verify helpers
    docs/        v2/ is current; v1*/ and the other folders are history
    third_party/ donor licenses and provenance

## Development environment

- Windows 10/11 x64.
- Python 3.12+ (3.14 is in use) for the engine; `pip install pyinstaller` to build `KelEngine.exe`.
- `bun` and Node.js 20+ for the desktop shell (`desktop/bun.lock` is authoritative):
  `cd desktop && bun install`.
- Provider CLIs (Codex, Claude Code) and API keys are runtime dependencies of the installed app, not of
  this repository. Tests need none of them.

## Test

    cd desktop && bunx tsc --noEmit        # typecheck
    cd desktop && bun run test             # vitest: node + jsdom projects (about 120 files / 900 tests)
    cd runtime && python -m pytest tests -q   # the engine (about 1,650 tests, 10+ minutes)

Tests are hermetic: temporary data roots, fake providers, a local stand-in for web services. The engine
suite points `KEL_PROJECTS_ROOT` at a temporary folder and turns `KEL_GENERAL_ROOT` off
(`runtime/tests/conftest.py`), so no test creates folders in the real `Documents\Kel Projects`. On a
busy machine the first test of a heavy desktop file can time out; rerun that file alone before treating
it as a failure.

End-to-end and packaged checks are separate and need a running app:

- `desktop/tests/e2e/*.e2e.ts` (Playwright) run against an isolated, signed-in WebUI
  (`KEL_WEBUI_URL`, `KEL_DEV_PASSWORD`): `cd desktop && bunx playwright test`.
- `packaging/*.cjs` drive a packaged or installed Kel through Playwright/CDP (for example
  `verify-installed-battery.cjs`, `ux-audit.cjs`). A unit test keeps every route they name pointed at a
  route the app serves.

Never run checks against the real `App` or `Data` while Nick may be using Kel: copy `Data` to a scratch
folder and start `App\Kel.exe` with `KEL_DATA_DIR`, `AIONUI_DATA_DIR` and `KEL_HOST_DATA_DIR` pointing
at the copy, `KEL_PROJECTS_ROOT` pointing at a scratch folder so new projects are not created in the real
`Documents\Kel Projects` (General's default folder follows it; `KEL_GENERAL_ROOT` sets General's folder
separately, or `none` turns it off),
`AIONUI_MULTI_INSTANCE=1` and `KEL_BACKGROUND_WINDOW=1` (the window renders off-screen and raises no
notifications). Delete the copy afterwards: it holds credentials.

## Build

    cd desktop && bun run package          # electron-vite build -> desktop/out (main, preload, renderer)
    powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1   # -> dist/runtime/KelEngine

A Windows directory package (Kel.exe, `resources/app.asar`, `resources/kel-engine`):

    cd desktop && npx electron-builder --config kel-builder.json --x64 --dir   # -> dist/package

Run only one packer at a time. The bundled AionCore binary
(`desktop/resources/bundled-aioncore/win32-x64/aioncore.exe`) is a stock donor artifact that is not stored
in git; see `desktop/KEL-FORK-NOTES.md` and `THIRD_PARTY_NOTICES.md`.

## Install (manual upgrade)

Kel has no updater (D-56); an upgrade is a deliberate manual step at a meaningful milestone:

1. Stop Kel. Back up `Data` (the app's own backup, or a copy under `Data\backups`).
2. Keep a rollback copy of the current `App` pieces you are replacing under `Tools`.
3. From the `--dir` package, replace `App\resources\app.asar`, `app.asar.unpacked` and `kel-engine`.
   Keep `Kel.exe`, the bundled AionCore, `hub` and `fonts` unless they changed.
4. Record what was installed in `App\kel-install-provenance.json` (source commit, hashes, checks).
5. Start Kel; engine migrations run on first launch and keep existing data.

The current install, its checks and its rollback are described in `docs/v2/MARATHON_STATE.md`.

## Documentation

Start with `docs/v2/MARATHON_STATE.md` ("Current state" at the top), then:

- `docs/v2/DECISIONS.md` — every product decision for V2 (the V2-xx phase notes, then D-29 onward),
  newest last.
- `docs/v2/RESUME.md` — how to pick the work up again.
- `docs/v2/FEATURE_LEDGER.md`, `IMPLEMENTATION_STATUS.md` — what is built, with evidence.
- `docs/v2/KNOWN_LIMITATIONS.md` — what is not true yet, stated plainly.
- `docs/v2/TEST_EVIDENCE.md` — test and package evidence.
- `docs/v2/design/` — implementation designs (Projects, scheduled Recipes, the live workforce,
  Routing 2); `docs/v2/CONNECTION_FRAMEWORK.md` — adding a service or an action.
- `docs/product/USER_JOURNEY_STANDARD.md` — the journey rules (JR-*) the UI is held to.
- Figma file `BlpVvZGuc9j9HhxUojIiJI` is the exact visual specification.

Older lines (V1.x, the daily-driver line) keep their documents under `docs/v1*`, `docs/daily-driver`
and the other folders; they are history, not current state.

## Licensing

- Kel original code is **Apache-2.0** (see `LICENSE`).
- `desktop/` is an Apache-2.0 fork of AionUI; attribution and modification notes are in `NOTICE`,
  `THIRD_PARTY_NOTICES.md`, `desktop/KEL-FORK-NOTES.md` and `third_party/`.
- Evaluated reference donors, including AGPL projects evaluated as ideas only, are listed in
  `THIRD_PARTY_NOTICES.md`.

Packaged binaries (`Kel.exe`, `app.asar`, `KelEngine.exe`), personal data, transcripts, screenshots and
credentials are never stored in git.
