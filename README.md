# Kel

Kel is a local, durable AI work engine for Windows with a desktop shell. It takes a request,
plans it into milestones, runs each milestone with real worker tools (native Codex/Claude CLIs,
or its own bounded internal worker), and then verifies the result against evidence before it
reports success. Kel keeps active work alive when the window closes and can resume unfinished
work across conversations and restarts.

- **Current stable version: V1.2** - the verified V1.2 source baseline (tag `v1.2.0`).
  Released binaries are built from it and distributed separately; they are not stored in git.
- **V1.3 (Context & Continuity): implemented and in release** - structured project memory,
  durable project map + provenance-labeled context composer, first-class continuation,
  reusable workflow recipes, and the Work-context UI. Source on `v1.3-dev`; design, status,
  and verification evidence under `docs/v1.3/` (suite: 267 passed + 10 subtests; packaged
  acceptance and V1.2-data upgrade verified).
- Platform: Windows 10/11 (V1.x line).

## Terminology

- **Kel Runtime** (`runtime/`) - the Python durable work engine (packaged as `KelEngine.exe`).
- **Aion Donor Shell** (`desktop/`) - the Electron desktop shell, a fork of AionUI.
- **KellShell** - the bundled AionCore process that hosts conversations and ACP agents
  (binary not in git; see `THIRD_PARTY_NOTICES.md`).

## Repository layout

    runtime/     Kel Runtime source (kel/), entry point, PyInstaller spec, tests
    desktop/     Aion Donor Shell source (AionUI fork) + Kel builder configs
    packaging/   asar dedup packer/inspector, engine PYZ verifier, packaged smoke test
    scripts/     build-runtime / build-desktop / verify-release / freeze-release (PowerShell)
    docs/v1/     V1-V1.2 status, drift, skeleton, verification documents
    docs/v1.2/   V1.2 release manifest + SHA-256 sums (reference)
    docs/v1.3/   V1.3 design, status, and verification documents
    third_party/ Donor license texts and provenance records

## Supported development environment

- Windows 10/11 x64.
- Python 3.12+ (V1.2 was built with 3.14.3) with `pip install pyinstaller` (V1.2 used
  PyInstaller 6.19.0) for runtime packaging.
- Node.js 20+ and `bun` for the desktop shell (`desktop/bun.lock` is authoritative).
- Optional: UPX (PyInstaller warns and skips if it is missing).
- Provider CLIs (Codex / Claude) are runtime dependencies of the installed application, not of
  this repository.

## Running the runtime tests

    cd runtime
    python -m pytest tests/ -q

Expected on the V1.2 baseline: `181 passed, 10 subtests passed`. Tests are hermetic (temp dirs
and fake providers); no network or API keys are required.

## Building Kel Runtime

    powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1

Runs PyInstaller with `runtime/KelEngine.spec` (repository-relative) and writes
`dist/runtime/KelEngine/`. The spec bundles `kel/web` and the native helper files as data.

Quick boot check from the repository root:

    dist\runtime\KelEngine\KelEngine.exe --data %TEMP%\kel-boot-check

The service prints its loopback port; `GET /api/state` on that port reports the engine version
and provider list. Idle engines stop with `POST /api/shutdown-idle`; otherwise close the window
or press Ctrl+C.

## Building the desktop shell

    powershell -ExecutionPolicy Bypass -File scripts/build-desktop.ps1 -Install

Runs `bun install` (first run) and `bun run build` in `desktop/`, producing
`desktop/out/{main,preload,renderer}` via electron-vite. Installer/dist packaging uses the donor
electron-builder flow (`bun run dist:win`) with the Kel builder configs
(`desktop/kel-builder.json`, `desktop/kel-runtime-builder.json`); see `desktop/KEL-FORK-NOTES.md`.

A full packaged release additionally requires (not stored in git):

- the AionCore binary at `desktop/resources/bundled-aioncore/win32-x64/aioncore.exe`
  (stock AionCore v0.2.2 build),
- the built runtime from `scripts/build-runtime.ps1`,
- an Electron runtime for the frame (installed by the desktop build).

## Packaging app.asar (dedup/integrity pipeline)

The shipped shell uses a content-addressed dedup layout with per-file SHA-256 integrity records.
To repack:

    node packaging/extract-asar.js <previous.asar> shell-stage        # once, to prepare the base
    node packaging/asar-dedup-pack.js shell-stage dist/app.asar
    node packaging/asar-inspect.js dist/app.asar

Overlay the freshly built `desktop/out` into `shell-stage` before packing. `asar-dedup-pack.js`
needs `@electron/asar` (found in `desktop/node_modules` after install, or set `ASAR_MODULE`).
Verification: `asar-inspect.js` entry counts and dedup savings must match the previous release's
numbers, and the data-size delta must be explainable by the actual content changes.

## Verifying a release

    powershell -ExecutionPolicy Bypass -File scripts/verify-release.ps1 -ReleaseDir <unzipped release>

Checks `Kel.exe`, `resources/app.asar` and `resources/kel-engine/KelEngine.exe` against the
reference sums in `docs/v1.2/SHA256Sums.txt.txt` (three hashes, in that order). Engine-level
provenance: `python packaging/verify_engine_pyz.py <KelEngine.exe>`. Packaged UI smoke:
`node packaging/verify-packaged-smoke.cjs <Kel.exe> <fresh-data-dir>` (requires Playwright).

## Licensing

- Kel original code is **Apache-2.0** (see `LICENSE`).
- `desktop/` is an Apache-2.0 fork of AionUI; attribution and modification notes are in
  `NOTICE`, `THIRD_PARTY_NOTICES.md` and `third_party/`.
- Evaluated reference donors - including AGPL projects evaluated as ideas only - are listed in
  `THIRD_PARTY_NOTICES.md`.

## Why packaged binaries are not stored in git

`Kel.exe` (Electron frame + Chromium), `app.asar` and `KelEngine.exe` are build outputs: large,
regenerable, and unsuitable for review. Releases are distributed as separate artifacts with a
manifest and SHA-256 sums (see `docs/v1.2/`). Git history keeps the source, tests, scripts and
licenses that produce them.

## Reproducibility limits (honest notes)

- Byte-identical binaries are **not** promised: timestamps, archive ordering, Vite content
  hashing and toolchain versions legitimately change bytes between builds.
- What is verified instead: runtime module-level structural equality
  (`packaging/verify_engine_pyz.py`), asar entry-count and dedup parity (`asar-inspect.js`), and
  behavior-level checks (runtime tests + packaged smoke harness).
- The bundled AionCore binary is a stock donor artifact and is not rebuilt here.
