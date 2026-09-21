# KEL V2.0 — FEATURE LEDGER

Feature → state → evidence. "State" is what is actually true on disk right now; the baseline rows
describe what the V2 line inherits from `dev/daily-driver` at `a471e17` (evidence lives in that line's
`docs/daily-driver/` and `docs/transcription/`), and the V2 rows are added as phases land.

## Baseline inherited by V2 (verified on `dev/daily-driver` @ a471e17)

| Feature | State | Evidence |
| --- | --- | --- |
| Conversation surface, projects, memory, team/agents, providers, transcription library, recipes engine, autonomy/continuation, activity, diagnostics, remote/WebUI gateway | **BUILT** (V1.x + Daily Driver D3–D19) | `docs/daily-driver/FEATURE_LEDGER.md`, `ROADMAP.md`, `IMPLEMENTATION_STATUS.md`; engine suite 1060 OK |
| Transcription with Muse (real credential shared from the copied Transcriptions app; practice mode explicit-only) | **BUILT + live-verified** | `docs/transcription/11_MUSE_SHARED_CREDENTIAL.md`; `docs/daily-driver/evidence/muse/` |
| Fix Capture (Ctrl+Shift+F → click → record → Muse → review → Save Fix; retry on failure; Dogfood Fixes; Prepare Fix Prompt) | **BUILT + installed-verified** | `docs/daily-driver/FIX_CAPTURE.md`, `evidence/fix-capture/`, `evidence/muse/`; desktop 310 tests |
| Dogfood store (four statuses, screenshots under the data root, prompt generator, practice-text guard) | **BUILT** | `runtime/kel/dogfood.py` (migration 22) + 27 engine tests |

## V2 features (to be filled as phases land)

| Phase | Feature | State | Evidence |
| --- | --- | --- | --- |
| V2-00 | V2 developer line + durable program state | **DONE** | this `docs/v2/` directory; `dev/v2` @ setup commit |
| V2-01 | Connections model + central management | **BUILT** | `runtime/kel/connections.py` (migration 23) + 25 engine tests; `/connections` page, bridge routing and 11 jsdom page tests + 12 workspace tests |
| V2-02 | Generic REST Connection | **BUILT** | `runtime/kel/connections.py` `test()` + `perform_request` (migration 24) and 20 engine tests incl. a local service stub; `Test connection` on the page + 2 jsdom tests + sender-guard coverage |
| V2-03 | Personal Connections (Pitcher List, Stripe, Raptive, Google Drive, GitHub, ClickUp, Figma, Discord) | **BUILT** | `runtime/kel/connection_services.py` (the eight services as data) + `auth_prefix` (migration 25) and 9 engine tests; "Set up …" on the page + 2 jsdom tests. Live checks against the real services need Nick's credentials and are not claimed |
| V2-04 | Connection Framework + templates | queued | — |
| V2-05 | iPhone Kel PWA V1 | queued | — |
| V2-06 | Needs Your Attention 2.0 | queued | — |
| V2-07 | Recipes 2.0 | queued | — |
| V2-08 | Activity 2.0 | queued | — |
| V2-09 | Routing intelligence | queued | — |
| V2-10 | Learning 2.0 | queued | — |
| V2-11 | Long-running work 2.0 | queued | — |
| V2-12 | Adaptive staffing 2.0 | queued | — |
| V2-13 | Local execution isolation | queued | — |
| V2-14 | Network permissions | queued | — |
| V2-15 | Real dogfood integration pass | queued | — |
| V2-16 | Performance + UX polish | queued | — |
| V2-17 | Manual upgrade reliability | queued | — |
| V2-18 | Synthetic V2 acceptance journeys | queued | — |
| V2-19 | Full V2 regression | queued | — |
| V2-20 | V2 release candidate | queued | — |

Removed from the intended V2 connection list by the directive: **Gmail** and **Slack** (they are not
V2 scope; do not re-add them without a recorded decision).
