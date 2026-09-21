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
| V2-04 | Connection Framework + templates | **BUILT** (the framework) | `connection_framework.py` (three templates + request policy), `connection_actions.py` (actions as data), `connections.run()`/`events()` (migration 26) + 16 engine tests; "What Kel can do" on the page + 5 desktop tests; the developer page `CONNECTION_FRAMEWORK.md`. Not part of the framework, and carried below: the assistant bridge and the OAuth sign-in flow |
| V2-04a | **Follow-up (not a roadmap phase): a tool the assistant can call for a connection action** | **BUILT** (2026-09-21) | The bridge (`kel.connection_tools` + the `kel.conn` helper), the `connections` capability, engine memory custody pushed by the shell (D-33), mutating confirmation through the existing approval rows (D-32), `source` provenance (migration 27). Engine journey test (16) + a live runtime journey recorded in `docs/v2/evidence/v2-04a/README.md` (`dev/v2` @ `d3bbf65`). Honest limits recorded: Claude Code quota-blocked that day (codex carried the work); the phone reaches it only once the Shell's Work route exists (Journey J held) |
| V2-04b | **Follow-up (not a roadmap phase): the OAuth account sign-in flow** | **BUILT** (2026-09-21) | `connection_oauth.py` (providers as data, flow in `oauth_flows`, migration 28) + the public `/oauth/callback` (D-35) + claim-once custody into the shell + refresh/revoke + plain-words `auth_state`; Google Drive first (`gdrive-files` action). 10 engine tests incl. a real-HTTP lifecycle and the security set (state/PKCE/replay/expiry/revoke/cross-connection/no-leak); desktop: main-process sign-in IPC + page Connect/Sign out, 5 new unit tests. Real Google not exercised — needs Nick's own client ID and a browser sign-in (`docs/v2/evidence/v2-04b/README.md`) |
| V2-05 | iPhone Kel PWA V1 | **PARTIAL** — voice (real Muse) and the send round trip (real model, continued) are proved in a real browser at phone width; conversation history / job attention / project routing remain | Journeys A–H in `desktop/tests/e2e/kel-mobile.e2e.ts` + `docs/v2/evidence/v2-05/`; the webui now seeds the Kel assistant (`packages/web-host/src/kel-integration.ts`, 4 unit tests); installability pinned by 5 desktop tests |
| V2-06 | Needs Your Attention 2.0 | queued | — |
| V2-07 | Recipes 2.0 | queued | — |
| V2-08 | Activity 2.0 | queued | — |
| V2-09 | Routing intelligence | **BUILT** (2026-09-21) | `kel/routing_evidence.py` (decayed, windowed, floored outcomes over the existing `routing_outcomes` table) + evidence-aware `router.select` (`why`/`chain`/`demoted`/`evidence`, policy `eligible-cost-v2`) + `action: 'why'` on `/api/model` + `needs_work()` so tool requests become real work turns. 204 tests green in bounded groups (13 new) and a live probe of the measured phone turn (job created, route readable, chat control stayed conversational). D-37/D-38; `docs/v2/evidence/v2-09/README.md` |
| V2-10 | Learning 2.0 | **BUILT** (2026-09-21) | Evidence-thresholded suggestions (`learning.suggest_learnings`: ≥3 decided runs / corrections / connection uses) through the existing proposal queue; off/on without deletion (`enabled` on a superseding equal-trust record; disabled never reaches `Memory.select`); `explain_learning` (source, evidence, chain, effect); the authority fence (no non-user source may assert permission/spending/file access/irreversible authority). 19 new tests; 112 tests green in bounded groups; live `/api/memory` loop proved (suggest → accept → explain → off → on). D-39; `docs/v2/evidence/v2-10/README.md` |
| V2-11 | Long-running work 2.0 | **BUILT** (2026-09-21) | Runtime recovery (`Store.recover_abandoned` + `Engine.tick`: fence only runs no broker can carry, never re-play), the Work brief (`Continuation.resume_brief` + `_work()['work']`: shipped/open/why/next + `needs_you`), all on the existing job/continuation paths. 11 new tests; 119 tests green in one bounded group; live: broker-backed runs survived startup untouched (orphaned total 0) and the Work brief rendered on the real service. D-40; `docs/v2/evidence/v2-11/README.md` |
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

## V2-05 — iPhone Kel PWA V1: PARTIAL (voice and send proved; history/attention/routing open)

Done and evidenced: the phone answers "what is happening with Kel?" (running context, "2 need you",
honest holds), the attention action it offers works from the phone (→ Providers, real provider state),
paste into the composer works, **voice reaches Muse** (real transcript in the composer), **the phone
chooses Kel and sends for real** (one `kel` pill → send → real reply → second turn → "still here"), the
PWA contract holds in the built app (Kel manifest, SW registered and controlling, 0 cached `/api/`, 0
horizontal overflow, clean console), and the gateway blocker that made all of it impossible is fixed.
Still open, in `RESUME.md` order: conversation history from the phone (deep link measured blank once),
job-driven attention actions, conversational project routing. V2-04a and V2-04b are built (2026-09-21)
and no longer unclaimed; **V2-09 routing intelligence is built** and the measured routing gap is
closed (a tool-shaped phone turn now becomes real work — `docs/v2/evidence/v2-09/README.md`).
