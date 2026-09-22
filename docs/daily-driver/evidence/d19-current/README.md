# Installed battery — re-verification of the app installed today (2026-09-21)

The recorded D19 battery (`evidence/d19/`) verified the Daily Driver candidate installed at
`C:\Users\Nick\KelDailyDriverCandidate`. That directory no longer exists: the later Fix Capture lane ran
an NSIS update that heals to the registered directory, so that path came to hold that build, and the lane
has since moved its own target. The data root `C:\Users\Nick\KelDailyDriverRuns` went with it.

This directory holds a fresh run of the same battery against **the app this machine actually has
installed now**:

| | |
|---|---|
| Install dir | `C:\Users\Nick\KelDogfoodCandidate` (registered in HKCU) |
| Data root | `C:\Users\Nick\KelDogfoodRuns\prepared\engine` |
| App | `Kel.exe`, `FileDescription` Kel / `FileVersion` 1.7.0-dev |
| Bundled engine | `e6444991…` — byte-identical to `dist/runtime/KelEngine/KelEngine.exe` at HEAD |

Command:

```
KEL_INSTALL_DIR="C:\Users\Nick\KelDogfoodCandidate" \
KEL_BATTERY_DATA="C:\Users\Nick\KelDogfoodRuns\prepared\engine" \
KEL_BATTERY_OUT="C:\Users\Nick\Desktop\Kel\kel-daily-driver\docs\daily-driver\evidence\d19-current" \
node packaging/verify-installed-battery.cjs
```

Result: **`allPassed: true`** — 0 failing checks, 0 console errors, 0 donor terms in the console.

- Nine surfaces (Landing, Work, Projects, Recipes, Activity, Transcription, Team, Settings, Tools): no
  raw error patterns, no horizontal overflow, no donor terms.
- D0-001 — this data root holds no lease, so the Permissions page must show its honest empty state; the
  probe accepts that and keeps the strong Work-column check whenever a lease does exist.
- D0-004 — exactly one refusal message; the toggle settles off.
- D1 — human provider statuses; Set up → Save; no false health; no raw provider ids in user copy.
- D2 — `Update metadata request failed (404)`, no release card, honest fail-closed answer.
- `update_identity` — `v1.7.0-dev`, no donor term.

`installed-battery.json` is the machine-readable verdict; the `surface-*.png` and `probe-*.png` files are
the screenshots the run captured.

The run also drove two fixes into the battery itself (see `PACKAGE_EVIDENCE.md` and `TEST_EVIDENCE.md`):
the landing-brief invariant and the Permissions probe are now data-driven instead of encoding one data
root's content, and the evidence path is overridable so a re-run never overwrites recorded evidence.
