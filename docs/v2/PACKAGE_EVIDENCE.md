# KEL V2.0 — PACKAGE EVIDENCE

## Current canonical installation (2026-09-24)

`C:\Users\Nick\Desktop\Kel\App` is the only installed Kel app. It uses `C:\Users\Nick\Desktop\Kel\Data`. Its current package comes from source `8c67121` on `main`. SHA-256: `Kel.exe` `010beb34ceb12dc0495290428abd0c64e067003c1214efb143e8f756a3c051f1`; `resources/app.asar` `dd87843467840cf45a196b4c5c09a97eb5f14099c0d7cb06198a42befd1f9a78`; `resources/kel-engine/KelEngine.exe` `4d0604b4a797a84b07a4acac9dad7e4b35cc467ddfa904c72bd19593409417fe`. Each matches the verified unpacked package. The engine's 67 embedded modules match current source. The installed App retained its 15 installed-only files, including its uninstaller and hub resources. It launched with isolated data after the update. The rXX candidate and dogfood locations below are historical records, not active paths.

The verified `App` is installed, but temporary rollback folders under `Tools` and package/build folders under `Kel/dist` remain. Automatic approval review rejected recursive cleanup. No further delete was attempted.

## Current staged candidate (2026-09-23)

`C:\Users\Nick\KelV2Candidate.r29` is staged only, from pushed source `41b2bf6`. The verified `app.asar` SHA-256 is `6ae8b552e6cf167647957cf566bf7318e1449ddeb8bf51f40e50453f0152032b`; `Kel.exe` is `b42a19307508e52ea08f4a6a09aa5089441adc42e2a70949dfd58f5b9b10b594`. The frozen engine is unchanged. Its launcher now supplies separate host, store, and engine roots; launcher SHA-256 `09af1bb5ac96d11af8c8558a1d177532ec04162fc198853b16c1e5f170376476`. A packaged launcher smoke confirmed all three process paths. `CANDIDATE_R29.md` records the archive gate and isolated packaged checks. r20 runs from `C:\Users\Nick\KelV2Candidate`; the stable app remains protected. No candidate was renamed, promoted, or installed over either app.

Candidate, package and install evidence. Kel is a personal application: no updater infrastructure, no
channels, no release marketing — only safe manual upgrade and a developer rollback path (§17 of the
directive).

## The stable dogfood installation (PROTECTED — do not touch)

| | |
| --- | --- |
| Install | `C:\Users\Nick\KelDogfoodCandidate` |
| Installed app | `Kel.exe` `9a2ffbdf41c1c8c971306b586bc9551afbd0826314d9a459a52239e5bbfeaa09` |
| Installed engine | `resources\kel-engine\KelEngine.exe` `e64449916d66d8698fa794dfd6c75732866b568db7ce678abecf8781db8efb15` |
| Package it came from | `dist/package-r12/Kel-1.7.0-dev-win-x64.exe` `007eaaa5001fc56a554f6436c86176db207e336c586db03b6aa86ff51931eed5` (213,649,875 bytes) |
| Data root in daily use | `C:\Users\Nick\KelDogfoodRuns\prepared` (engine root `…\prepared\engine`) |
| Registration | `HKCU\Software\9280710d-02b9-55d6-ba7a-2b7d6f91d60a` → that install directory |
| Provenance | `docs/daily-driver/PACKAGE_EVIDENCE.md`, `FIX_CAPTURE.md`, `docs/transcription/11_MUSE_SHARED_CREDENTIAL.md` |

Nick uses this build while V2 is developed; its Fix Capture output is real dogfood input. **Never**
modify, uninstall, overwrite, reset, migrate, clean or point a V2 run at it.

## V2 packaging plan

| | |
| --- | --- |
| V2 test data root | `C:\Users\Nick\KelV2Runs\prepared` (create on first use) |
| V2 candidate | `C:\Users\Nick\KelV2Candidate` — **intentionally not created yet** |
| When to install | only when an implementation checkpoint genuinely needs installed-app verification (V2-05 iPhone reachability, V2-13/14 isolation and network rules, V2-17 upgrade/migration, V2-18/19/20 acceptance and regression) |
| Never | one install per phase; a V2 install that shares the dogfood data root; a second registry identity that would break the dogfood registration |

## Phase record (no candidate has been built yet)

| Phase | Candidate | Installed check |
| --- | --- | --- |
| V2-00 … V2-04 | none built | none performed. The Connections work is verified by engine tests, renderer type checking, jsdom tests through the shipped components and the real bridge contract, and source pins — recorded in `TEST_EVIDENCE.md`. Installing was not needed and `C:\Users\Nick\KelV2Candidate` still does not exist |

## V2 packaging: the manifest defect found on 2026-09-22 (and the fix)

A pack run produced `dist/package-r12/win-unpacked` whose `resources/app.asar` had a **corrupt root
`package.json`**: the entry held 4,402 bytes of `sw.js` text instead of the app manifest, so the
packaged `Kel.exe` showed Electron's *“Error launching app / Unable to parse package.json / Unexpected
token 'ACHE_NAME)' is not valid JSON”* dialog and never reached the app.

| | |
| --- | --- |
| Detected how | the dialog was reported verbatim; extracted the root manifest with `@electron/asar` 3.4.1 (`extract-file`) and parsed it — first bytes `ACHE_NAME);` |
| Root cause | **the build input was already corrupt**: a previous session ran `asar extract-file <archive> package.json` from `desktop/`, and that command writes into the current directory — it had overwritten the tracked `desktop/package.json` with a slice of `sw.js`. The packer faithfully packed the corrupted input. The same extractor against the protected dogfood install returns a valid manifest, so the tool and the packer are not at fault |
| Fix | `git checkout -- desktop/package.json` (restored: `name Kel`, `main ./out/main/index.js`, 10,586 bytes), then repack. **Never run `asar extract-file` from a source directory** — always from a scratch directory |
| Why it matters | the defect is invisible in a file listing (an `app.asar` of the right size still exists), so a candidate must always be **launched** before it is called verified |

Engine provenance for the same run: `scripts/build-runtime.ps1` freezes the Kel engine from this
worktree with PyInstaller; `packaging/verify_engine_pyz.py` read the archive back and agreed with the
source (67 `kel` modules, `MISMATCH: []`, `RESULT: OK`), and the pack config
(`desktop/kel-builder.json` `extraResources`) places it at `resources/kel-engine`. The desktop shell is
`resources/app.asar` (renderer + main); `resources/bundled-aioncore/win32-x64/aioncore.exe` is the
**donor** AionCore v0.2.2 binary that hosts the UI/back end process — provenance-checked against its
own `provenance.json`; it is not the Kel engine.

## Rules carried over from the predecessor program (learned the hard way)

- NSIS updates heal to the *registered* install directory: repoint the registration deliberately (and
  clear it first when installing to a new target) instead of assuming `/D=` wins.
- Build inputs must be current before packaging: rebuild the engine (`scripts/build-runtime.ps1`) and
  verify the packed module set (`packaging/verify_engine_pyz.py`) before the desktop package build.
- Record the package, app and engine hashes for every candidate that Nick is asked to use; without the
  hashes an install cannot be proven.
