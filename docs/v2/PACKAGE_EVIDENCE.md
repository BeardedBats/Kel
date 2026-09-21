# KEL V2.0 — PACKAGE EVIDENCE

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

## Rules carried over from the predecessor program (learned the hard way)

- NSIS updates heal to the *registered* install directory: repoint the registration deliberately (and
  clear it first when installing to a new target) instead of assuming `/D=` wins.
- Build inputs must be current before packaging: rebuild the engine (`scripts/build-runtime.ps1`) and
  verify the packed module set (`packaging/verify_engine_pyz.py`) before the desktop package build.
- Record the package, app and engine hashes for every candidate that Nick is asked to use; without the
  hashes an install cannot be proven.
