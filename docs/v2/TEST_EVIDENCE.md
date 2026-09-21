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
| V2-01 | Connections model + central management | engine `1085 tests OK`; `tests.test_v2_connections` **25 OK**; desktop `40 files / 334 tests pass`; `tsc --noEmit` clean; `tests/unit/connections-page.dom.test.tsx` **11 pass**; `tests/unit/connections-surface.test.ts` **12 pass** (details below) |
| V2-02 | Generic REST Connection + Test Connection | engine `1101 tests OK`; `tests.test_v2_connections` **41 OK**; desktop `40 files / 338 tests pass`; `tsc --noEmit` clean; `connections-page.dom.test.tsx` **13 pass** (details below) |

### V2-01 — what each command actually proves

| Suite | Command | Result |
| --- | --- | --- |
| Engine (full, regression) | `cd runtime && python -m unittest discover -s tests` | **1085 tests OK** (baseline 1060 + 25 new; no existing test changed behaviour beyond the migration inventory below) |
| Engine — Connections model | `python -m unittest tests.test_v2_connections` | **25 OK** — exact schema (and no column that could hold a value), idempotent migration, slug ids that survive a rename, duplicate names, validation refusals (no name, unknown kind, non-http address, `javascript:` address, header defaulting, bearer/oauth defaults), list order and counts, remove, credential metadata set/clear with the pointer guard, service-agnostic pin, and the service-level dispatch incl. PolicyError sentences |
| Engine — migration inventory | `python -m unittest tests.test_v16_r8_migrations` | **4 OK** — the inventory now covers every module (`dogfood` 22, `connections` 23) and expects 23 as the maximum |
| Desktop types | `cd desktop && bunx tsc --noEmit` | **clean** |
| Desktop tests (full) | `cd desktop && bunx vitest run` | **40 files / 334 tests pass** (baseline 38 / 310) |
| Desktop — Connections page (jsdom) | `bunx vitest run --project dom tests/unit/connections-page.dom.test.tsx` | **11 pass** — the real page: state said in words, empty state, the shell/engine disagreement sentence, add a service through the form, the engine's own refusal sentence repeated verbatim, no request for an unnamed service, a credential stored under `connection:<id>` and gone from the DOM and from every request afterwards, remove credential, confirm-then-remove, and never a request to `/api/providers` |
| Desktop — Connections wiring | `bunx vitest run tests/unit/connections-surface.test.ts tests/unit/ipc-sender-channels.test.ts` | **12 + 19 pass** — the credential IPC routes connection metadata to `/api/connections` and provider metadata to `/api/providers`, the new status channel refuses spoofed senders, a failed sync never fails the custody action, and no credential value is ever placed in a sync body |

**Not verified for V2-01:** no installed-app check was run (no candidate was installed by this phase), and nothing in this phase called a service over the network — `test_endpoint` is stored only. That is the V2-02/V2-15 work.

### V2-02 — what each command actually proves

| Suite | Command | Result |
| --- | --- | --- |
| Engine (full, regression) | `cd runtime && python -m unittest discover -s tests` | **1101 tests OK** (V2-01 left it at 1085; +16 new, no existing behaviour changed) |
| Engine — Connections incl. checks | `python -m unittest tests.test_v2_connections` | **41 OK** — the V2-01 pins plus: exactly one `urlopen` in the module (the choke point), a 200 recorded with its status and duration, the credential reaching the service and being written nowhere (the whole row is searched for the value), bearer vs plain `Authorization` vs custom header, the query method in the address, basic needing both halves before anything is sent, 401/404/429/500/418 named honestly, a closed port as `unreachable` (not a failed credential), a slow service timing out, a connection with no address refused before any request, a connection with no credential still asking the service, `scrub` redacting, and the service-level `test` action returning the record without the value |
| Engine — migration inventory | `python -m unittest tests.test_v16_r8_migrations` | **4 OK** — `connections` now owns 23 and 24; 24 is the maximum, and the existing-database test proves the newest step is safe to re-apply |
| Desktop types | `cd desktop && bunx tsc --noEmit` | **clean** |
| Desktop tests (full) | `cd desktop && bunx vitest run` | **40 files / 338 tests pass** (V2-01 left it at 334) |
| Desktop — Connections page (jsdom) | `bunx vitest run --project dom tests/unit/connections-page.dom.test.tsx` | **13 pass** — the V2-01 journeys plus: Test connection uses the stored value for the check and reports what came back, the value appears in no part of the rendered page afterwards, and a connection with no address offers no check at all |
| Desktop — Connections wiring | `bunx vitest run tests/unit/connections-surface.test.ts tests/unit/ipc-sender-channels.test.ts` | **13 + 20 pass** — `kel:connection-test` refuses spoofed senders before reading anything, hands the engine exactly the fields the shell holds, and returns the record; the custody key format is pinned on both sides of the bridge |

**Not verified for V2-02:** no installed-app check, and no real service was contacted by any test — the engine tests run against a local stand-in service on the loopback interface, so "works against the real Pitcher List / Stripe" remains V2-03's and V2-15's evidence, not this phase's.

## Standing rules for this file

- A phase is never "verified" by a plan, a screenshot alone, or a code change: name the command and the
  result, or the installed-app check and its evidence file.
- When a check cannot run here (no hardware, no credential, no network), say exactly that and record what
  *was* verified instead — never mark it green.
