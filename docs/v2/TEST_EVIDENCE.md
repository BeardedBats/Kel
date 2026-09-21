# KEL V2.0 — TEST EVIDENCE

Cumulative verification. Every phase appends its own block; nothing here is copied from a plan. Each
row names the command and the result, so a resume run can re-run it instead of trusting prose.

## Baseline at V2-00 (inherited from `dev/daily-driver` @ `a471e17`)

| Suite | Command | Result |
| --- | --- | --- |
| Engine (full) | `cd runtime && python -m unittest discover -s tests` | **1060 tests OK** |
| Engine — transcription family | `python -m unittest tests.test_transcription` | **35 OK** (incl. shared-credential reuse, no-key refusal, explicit practice mode, credential scoping) |
| Engine — dogfood store | `python -m unittest tests.test_dogfood` | **27 OK** (incl. the practice-text guard in both directions) |
| Desktop types | `cd desktop && bunx tsc --noEmit` | **clean** |
| Desktop tests (full) | `cd desktop && bunx vitest run` | **38 files / 310 tests pass** |
| Desktop — Fix Capture | `bunx vitest run tests/unit/fix-capture.dom.test.ts tests/unit/fix-capture-layer.dom.test.tsx` | **41 pass** (retry reuses the same audio payload, honest failure copy, Record Again drops the failed take, cancel cleans up, bridge allowlist, preload wiring, capture contract) |

### Installed-app verification of the baseline (evidence committed in the predecessor line)

| Check | Evidence | Result |
| --- | --- | --- |
| Fix Capture journeys A–E (save → restart, Record Again, cancel + 0 temp files, Prepare Fix Prompt + BATCHED, screenshot + target outline) | `docs/daily-driver/evidence/fix-capture/installed-journeys.json` | **all PASS**, 0 console errors, 0 orphaned engines |
| Real Muse — normal Transcriptions | `docs/daily-driver/evidence/muse/transcriptions-*.json` | **PASS** — page reports *Muse*; transcript *"Regular transcription muse verification orange"* |
| Real Muse — Fix Capture | `docs/daily-driver/evidence/muse/fix-capture-*.json` | **PASS** — `FIX-0006` = *"Fix capture muse verification, blue baseball 83"*, visible in Dogfood Fixes |
| Muse failure path | `docs/daily-driver/evidence/muse/failure-*.json` | **PASS** — honest error, Retry reuses the recording, Save disabled, nothing saved, practice-text guard refused (400) |
| Real microphone path | `docs/daily-driver/evidence/muse/device-check-*.json` | **PASS** — 4 real inputs, device opened, peak ≈ 0.001 (room silent) |
| Dogfood page regression | `docs/daily-driver/evidence/muse/regression-dogfood.png` | **PASS** — list + outline render, 0 px overflow, no donor terms, no raw internal ids |

## V2 phases

| Phase | What was verified | Evidence |
| --- | --- | --- |
| V2-00 | developer line + durable state (this setup commit) | `docs/v2/`; `git worktree list`; remote `dev/v2` SHA = local |

## Standing rules for this file

- A phase is never "verified" by a plan, a screenshot alone, or a code change: name the command and the
  result, or the installed-app check and its evidence file.
- When a check cannot run here (no hardware, no credential, no network), say exactly that and record what
  *was* verified instead — never mark it green.
