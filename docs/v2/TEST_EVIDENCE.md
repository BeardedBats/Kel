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
| V2-03 | Personal Connections | engine `1110 tests OK`; `tests.test_v2_connections` **50 OK**; desktop `40 files / 340 tests pass`; `tsc --noEmit` clean; `connections-page.dom.test.tsx` **15 pass** (details below) |
| V2-04 | Connection Framework (standard parts, then actions) | engine `1126 tests OK`; `tests.test_v2_connections` **66 OK**; desktop `40 files / 344 tests pass`; `tsc --noEmit` clean; `connections-page.dom.test.tsx` **18 pass**, `ipc-sender-channels.test.ts` **21 pass** (both increments below) |
| V2-05 | iPhone Kel PWA V1 (installability) | desktop `41 files / 349 tests pass`; `tsc --noEmit` clean; `tests/unit/pwa-install.test.ts` **5 pass** (below). No engine change |

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

**Not verified for V2-02:** no installed-app check, and no real service was contacted by any test — the engine tests run against a local stand-in service on the loopback interface, so "works against the real Pitcher List / Stripe" is not this phase's evidence.

### V2-03 — what each command actually proves

| Suite | Command | Result |
| --- | --- | --- |
| Engine (full, regression) | `cd runtime && python -m unittest discover -s tests` | **1110 tests OK** |
| Engine — Connections + known services | `python -m unittest tests.test_v2_connections` | **50 OK** — everything above plus: the catalogue is data (two functions, no imports, no branching on a service name), every entry is a usable connection row with a valid kind, method and http(s) address, a known service added by name lands on the id the catalogue uses, the declared prefix is exactly what the service receives (`Bearer `, `Bot `, raw), a value that already carries its prefix is not doubled, a connection with no declared prefix keeps the old "work it out" behaviour, an absurd prefix is refused, and the separator after a prefix survives being saved |
| Engine — migration inventory | `python -m unittest tests.test_v16_r8_migrations` | **4 OK** — `connections` now owns 23, 24 and 25; 25 is the maximum |
| Desktop types | `cd desktop && bunx tsc --noEmit` | **clean** |
| Desktop tests (full) | `cd desktop && bunx vitest run` | **40 files / 340 tests pass** |
| Desktop — Connections page (jsdom) | `bunx vitest run --project dom tests/unit/connections-page.dom.test.tsx` | **15 pass** — everything above plus: "Set up GitHub" fills the form in (name, address, header, and "Kel adds a word in front" with `Bearer `) and saving posts exactly those fields, and the page states what Nick has to fetch and how sure Kel is about the address (including that Raptive's address is not known) |

**Not verified for V2-03:** no real service was contacted — Kel knows the eight services' addresses and shapes, but testing them needs Nick's credentials, so nothing here says a service works. No installed-app check either.

### V2-04 — the framework's standard parts

| Suite | Command | Result |
| --- | --- | --- |
| Engine (full, regression) | `cd runtime && python -m unittest discover -s tests` | **1117 tests OK** |
| Engine — framework policy | `python -m unittest tests.test_v2_connections` | **57 OK** — everything above plus: a busy service (503 then 200) is asked again and the record says Kel tried twice; a 401, 403 or 404 is never retried (each service saw exactly one request, and the pauses list stayed empty); Kel stops after the policy's three attempts and never collects the fourth answer; a dropped connection is retried and then reported; the policy's numbers are the ones the engine uses; the three templates cover the three kinds with real words and a check sentence; and the framework module cannot learn a service name |
| Engine — migration inventory | `python -m unittest tests.test_v16_r8_migrations` | **4 OK** |
| Desktop types | `cd desktop && bunx tsc --noEmit` | **clean** |
| Desktop tests (full) | `cd desktop && bunx vitest run` | **40 files / 341 tests pass** |
| Desktop — Connections page (jsdom) | `bunx vitest run --project dom tests/unit/connections-page.dom.test.tsx` | **16 pass** — everything above plus: the kind list a person picks from is the engine's templates, word for word (label — hint), so the renderer has no vocabulary of its own |
| Desktop — surface pins | `bunx vitest run tests/unit/connections-surface.test.ts` | **13 pass** — including the pin that the renderer's API module no longer carries a kind vocabulary, and that the credential field name comes from the framework's template |

**Not verified for V2-04, and not claimed:** what Kel can *do* with a service (actions/tools) is not built, the OAuth sign-in step is not built, and no real service has been contacted. The framework's retries are proven against a local stand-in service only.

### V2-04 continued — actions

| Suite | Command | Result |
| --- | --- | --- |
| Engine (full, regression) | `cd runtime && python -m unittest discover -s tests` | **1126 tests OK** |
| Engine — actions | `python -m unittest tests.test_v2_connections` | **66 OK** — everything above plus: the action catalogue is rows belonging to known services (unique ids, GET only, a leading-slash path, nothing mutating); a read action hands back the parsed answer, records only the fact of the call (domain, status, duration — no path, no query, no answer, checked over the whole history) and returns text when the answer is not JSON; a credential echoed back in an answer is redacted to `[redacted]` and never appears in the result; an action belonging to another service is refused by name; a mutating action is refused until Nick confirms (and the request then goes out as POST); a connection with no address is refused before anything is sent; a busy service is retried by an action too; and the history is per connection |
| Engine — migration inventory | `python -m unittest tests.test_v16_r8_migrations` | **4 OK** — 26 (`v20-connection-actions`) is the maximum |
| Desktop types | `cd desktop && bunx tsc --noEmit` | **clean** |
| Desktop tests (full) | `cd desktop && bunx vitest run` | **40 files / 344 tests pass** |
| Desktop — Connections page (jsdom) | `bunx vitest run --project dom tests/unit/connections-page.dom.test.tsx` | **18 pass** — everything above plus: "Do it" runs the action with the credential the shell holds and shows the answer once, with the value absent from the whole rendered page; and something that would change Nick's account asks first (nothing is sent until he confirms, then it is sent confirmed) |
| Desktop — sender guards | `bunx vitest run tests/unit/ipc-sender-channels.test.ts` | **21 pass** — `kel:connection-run` refuses spoofed senders before reading anything, and hands the engine only the fields the shell holds plus the confirmation |

**Not verified for V2-04 actions:** no real service was contacted — every action ran against the local stand-in service; the assistant cannot use an action yet (no chat tool); and nothing Kel can do changes anything, because every catalogue action is a read.

### V2-05 — installability (the donor's PWA machinery, now pinned)

| Suite | Command | Result |
| --- | --- | --- |
| Desktop tests (full) | `cd desktop && bunx vitest run` | **41 files / 349 tests pass** |
| Desktop types | `cd desktop && bunx tsc --noEmit` | **clean** |
| Installability contract | `bunx vitest run tests/unit/pwa-install.test.ts` | **5 pass** — the manifest keeps the fields a home-screen install needs and names Kel in its own words (the donor line's "Kel WebUI for mobile and desktop browsers" is gone); the 192 and 512 icons it promises are on disk, as is the iOS touch icon; the shell the phone loads links the manifest and carries the iOS tags and `viewport-fit=cover`; and the service worker still never caches `/api/` and is only registered from a browser origin (never inside the desktop shell) |

**Not verified for V2-05, and not claimed:** the phone *surface* is not built (the mobile-first pass, one-handed attention actions, voice from the phone); no real iOS Safari behaviour can be confirmed here — that needs Nick's device, and no installed-app check was run for this increment. The installability that exists is the donor's, verified by reading and by these pins, not by installing it on a phone.

## Standing rules for this file

- A phase is never "verified" by a plan, a screenshot alone, or a code change: name the command and the
  result, or the installed-app check and its evidence file.
- When a check cannot run here (no hardware, no credential, no network), say exactly that and record what
  *was* verified instead — never mark it green.

## V2-05 — Kel on a phone (real browser engine)

Evidence: `docs/v2/evidence/v2-05/README.md` + `findings-A|B|C|D|E|F.json` + the step screenshots.

- `desktop/tests/unit/kel-remote-bridge.test.ts` — new pin: the gateway must drop the browser's
  `origin`/`referer` when it forwards to the engine (a browser's Origin can never be the engine's own, so
  every mutating Kel route answered 403 from a browser before the fix).
- `desktop/tests/e2e/kel-mobile.e2e.ts` (new) — the phone journeys, in real Chromium at 393x852 with an
  iPhone UA, against the built renderer served by the real gateway: A home/attention, B composer+paste,
  C attention action, D project surface, E voice, F PWA contract. Measured: 0 horizontal overflow on
  every surface; post-sign-in console clean and no failed reads; manifest/SW/`/api/` cache contract green.
- Reproduce (engine + `bun run package` + `bun run webui` + `KEL_DEV_PASSWORD=… bunx playwright test
  tests/e2e/kel-mobile.e2e.ts`) — exact commands in the evidence README.

## V2-05 second pass — mobile voice

- `desktop/tests/unit/kel-mic-button.dom.test.tsx` (new, jsdom): a phone context without `window.kelAPI`
  still records through `/kel/api/transcription`; a failed `stream_start` is surfaced in plain words and
  does not fake a live state; a successful stop hands the words to the composer; a dead transcription
  path says so without transport jargon (asserted: no `/kel`, `stream_`, `quick_`, session ids).
- Journey E (real browser, real Muse, real speech): see `evidence/v2-05/README.md` — transcript
  `Calmuse verification green baseball 64`, no practice text, 28 transcription calls through the gateway.
- Whole phone suite re-run green: A, B, C, D, E, G, F — 7 passed (1.4m), 0 horizontal overflow, clean
  post-sign-in console, PWA contract intact. `bunx tsc --noEmit` clean; focused unit files 10 passed.
- Journey G (new): the phone reaches Providers and Connections — the V2-01…V2-04 connection surfaces are
  usable from a phone. Model selection and the positive send path are still open.

## V2-05 third pass — the phone sends for real

- `desktop/packages/web-host/src/kel-integration.unit.test.ts` (new, 4 tests): a fresh profile gets the
  agent + `kel` assistant with the exact module-form spec and only `kel` enabled; a second run is
  idempotent and refreshes the agent spec; a disabled-`kel`/extra-enabled profile is repaired; a backend
  refusal fails loudly instead of claiming success.
- `desktop/tests/unit/kel-remote-bridge.test.ts` — the D11 pin updated: the shared `KEL_DATA_DIR` also
  seeds the browser profile's Kel assistant.
- Journey H (real browser 393x852 → gateway → aioncore → Kel engine (ACP) → CLI model), 17.8s:
  `assistant-pills ["kel"]` → `send-possible true` → user turn lands → `reply-one "Phone send check
  received."` → settled → second turn lands → `reply-two "still here"`; post-auth watch: 0 failed reads,
  0 WS failures, 0 console errors; overflow OK. Evidence: `findings-H.json`, `H1–H3` PNGs.
- Measured write-ups: assistant replies live in a shadow root (`innerText` cannot see them — read
  `.markdown-shadow-body`); the conversation send control can read as disabled while it still accepts the
  next send (recorded, not gated on).
- Broader: whole desktop suite `bunx vitest run` — 43 files, 358 passed; `bunx tsc --noEmit` clean.
- One authed probe: a full-page load of `/conversation/<id>` on the phone rendered a blank body; the
  drawer/history increment must verify or fix it. (Single observation, not a claim.)

### V2-04a — the assistant bridge (engine journey + live run, 2026-09-21)

- `runtime/tests/test_v2_connection_bridge.py` — 16 tests, all pass: discovery (catalog) through a
  real engine over HTTP; the `kel.conn` helper executed as a subprocess; argument validation; the
  capability control (off → recommendation; one-shot grant consumed exactly once); the mutating
  flow (ask created + announced in the conversation, duplicate asks reused, resolved through the
  real `/api/approval`, executes only then, wrong approval refused, no-run case honest); bounded and
  scrubbed answers; `source: runtime` provenance; the value asserted absent from helper output,
  events, approvals, messages and the database.
- Full engine suite at `d3bbf65`: `python -m unittest discover -s tests` → **1142 tests, OK** (652 s).
- Live runtime journey on the prepared engine: job `3c35e589…` ran a real work turn; the worker
  (codex-code) found the connector via `python -m kel.conn list`, called `github-whoami`, and wrote
  the bounded login into `notes.txt` (`bridge check` / `kel-bridge-live-account`); the stand-in
  service logged `GET /user 200`; the access history recorded `{"action": "github-whoami",
  "source": "runtime", "state": "ok"}`. Raw material: `evidence/v2-04a/live-run.txt`; write-up:
  `evidence/v2-04a/README.md`.
- Measured limits of that run: Claude Code is quota-blocked on this machine today (codex carried the
  work; the fallback is the engine's own); the job closed UNCERTAIN (its verification path shared the
  quota) while the bridge evidence stands; the phone line cannot reach a work turn yet (its turns are
  conversational by design), so Journey J is held, not delivered.

### V2-04b — the OAuth foundation (2026-09-21)

- `runtime/tests/test_v2_oauth.py` — 10 tests, all pass: the whole lifecycle engine-level
  (disconnected → connect → callback → connected → Test Connection → authorized read → refresh →
  revoke → disconnected) against a local stand-in provider that performs a REAL S256 PKCE check;
  state mismatch / replay / malformed / expired answers refused (and never traded); verifier
  mismatch refused; refresh on expiry serves the call with the new token; failed refresh reads
  `needs_reconnect` and stays refused; revoke tells the provider and returns to disconnected;
  one connection's token never rides another's request; missing granted scopes named in plain words;
  tokens absent from every durable table; plus a real-HTTP journey (engine `serve()`, the browser
  callback with **no bearer**, one-time claim, the bridge `call` path, revoke) and untrusted-callback
  refusals.
- Desktop: 5 new unit tests (`connections-surface.test.ts`) — browser open → bounded wait → claim
  once → custody fields → engine pointer + supply; honest refusal when the person does not finish;
  bounded timeout; sign-out clears shell custody and engine memory; spoofed sender refused before
  any call. Whole desktop suite `bunx vitest run` — 43 files, 363 passed; `bunx tsc --noEmit` clean.
- Migration ledger: `v20-oauth` (28) — the migration-set suite updated and green.
- Verification split (this machine, under load): the monolithic `discover` run was replaced by two
  bounded runs with identical coverage — the bulk regression (75 modules: every suite except the two
  HTTP-journey files) → **1126 tests, OK** (527 s), and the two HTTP-journey suites together
  (`test_v2_oauth` + `test_v2_connection_bridge`) → **26 tests, OK** (59 s).
- Live check against the real provider: `oauth-initiate` built a real Google authorize URL
  (S256 `code_challenge`, `offline`+`consent`, the engine's own loopback redirect); the
  unauthenticated callback drove a real token exchange at `https://oauth2.googleapis.com/token`, and
  Google's own answer came back in plain words (“Google did not accept the sign-in — The OAuth client
  was not found.” — a placeholder client id); the page carried no token; the connection read
  `disconnected`; replaying the state answered “That sign-in answer was already used.” A real
  *sign-in* still needs Nick's client ID (`evidence/v2-04b/README.md`).

### V2-04 hardening — the choke point's own rules (2026-09-21)

- `tests/test_v2_connections.py` → **6 new tests** in `ExecutionHardeningTests`, all pass against a
  loopback stand-in: a self-redirecting service stops far below urllib's default ten hops and reports
  the 302 honestly; a service's own `Retry-After: 1` is honoured exactly; an absurd one (600 s) is
  capped at `RETRY_AFTER_CAP`; a network rule stops the request **before** the stub is ever contacted
  and its sentence is the one the person reads; a rule source that raises fails closed with its own
  plain sentence; an answer past the reading cap says “The answer was cut short.” and stays bounded.
  The single-doorway pin was updated to the new opener (`build_opener(` ×1, `.open(` ×1).
- Suites at this commit: **141 OK** in one focused run (`test_v2_connections` incl. the six new
  tests, `test_v2_oauth`, `test_v2_connection_bridge`, `test_capabilities`, `test_v16_r8_migrations`)
  — that is every suite reaching `perform_request` (its only callers are `connections.py`,
  `connection_oauth.py` and `connection_framework.py`). The full-module bulk run of the preceding
  state was green (1126 OK); its re-run after this edit was abandoned after 30 minutes of crawling
  under machine load (the identical module set had taken 527 s twenty minutes earlier), so this
  increment's verification is the focused run — recorded plainly rather than presented as a
  full-suite pass.

### V2-09 — routing intelligence (2026-09-21)

- `tests/test_v2_routing.py` (new, 13 tests) — decay and recovery (four month-old failures read below
  the floor and cannot demote anyone; four fresh verified runs outweigh them), the small-sample floor
  (two runs report **no** rate; the sentence says so), review precedence over an inferred failure, the
  richer fact row (kind/attempts/escalation/model/ms/at/source/reviewer/cost), the half-life constant,
  the demotion reordering plus the explanation shape, preference and explicit choice never demoted,
  and the tool-request predicate — including the **exact measured phone sentence**.
- Bounded groups on the final code (one stack at a time, no monolithic run):
  `test_v2_routing test_service_routing test_model_prefs test_v14_providers test_v15_completion` →
  **57 OK**; `test_workforce_assignment` (via `discover -s tests`) → **43 OK**;
  `test_v16_r8_migrations test_v14_diagnostics test_v14_upgrade test_v15_reliability test_v15_roles
  test_v13_continuation_service test_review_recovery` → **41 OK**; `test_research
  test_v13_work_context test_acp_host` → **41 OK**; `test_coding_boundaries test_coding_recovery
  test_coding_transport` → **22 OK**. Total **204 tests green**.
- Live probe (engine restarted on this code, `C:\Users\Nick\KelV2Runs\prepared\engine`): the measured
  phone turn through `/api/send` created a real job (`state=RUNNING`, provider `codex`, chain
  `['codex','claude']`, `why='lowest cost among the models that are healthy and capable here'`);
  `/api/model {action:'why'}` answered “Kel is using Codex: the lowest cost among the models that are
  healthy and capable here.” and carried `chain/demoted/evidence/excluded/job/provider/selected/why`;
  the chat control created **no** job (delta 0). The probe stack was stopped afterwards (ownership
  checked by PID; nothing of Astra’s was touched).

### V2-10 — learning 2.0 (2026-09-21)

- `tests/test_v2_learning.py` (new, 19 tests) — the required behaviours, pinned: a switched-off
  learning never reaches context and leaves the default view while staying inspectable
  (`include_disabled`, `enabled=False`) with the whole chain intact; switching it back on restores it
  from the same chain; removal takes it out of every view; explain reports source, evidence, history
  and the boundary `effect`; the authority fence refuses permission/spending/file-access/
  irreversible assertions from **every** non-user source and lets a user’s own statement through;
  suggestions need the evidence threshold before anything exists, a run mix below the share floor is
  not suggested, a rejected suggestion never returns until its evidence signature changes, accepting
  one writes it as the person’s own (`user_confirmation`), repeated corrections and repeated
  Connection use each suggest after 3, suggestions never use `decision`/`preference` types, disabled
  state survives a reopen, and the service surface exercises all five new actions.
- Bounded group on the final code: `test_v2_learning test_workforce_learning test_v13_memory
  test_v16_proposals test_v15_memory_packets test_v16_r5_persistence test_service_routing
  test_v14_diagnostics` → **112 OK** (25–32 s; one stack at a time, no monolithic run).
- Live loop (engine restarted on this code with `KEL_WORKFORCE_LEARNING_SHADOW=1`,
  `C:\Users\Nick\KelV2Runs\prepared\engine`), driven only through `/api/memory`: empty evidence →
  `suggested=0`; three decided runs → `suggested=1 states=['pending']`; `accept_proposal` →
  `{"kind": "user_change", "state": "accepted"}`; `learnings` → `[('model.coding.codex',
  'observed')]`; `learning` (explain) → evidence `["routing_outcomes:coding:codex"]` and the effect
  sentence (“…never grants permission, spending, file access or any irreversible authority…”);
  `disable_learning` → default 0 / `include_disabled` 1 with `enabled=False`; `enable_learning` →
  default 1. `RESULT live_loop=ok`. The probe engine was then stopped by PID after checking the
  listener owner.

### V2-11 — long-running work 2.0 (2026-09-21)

- `tests/test_v2_longrun.py` (new, 11 tests) — an expired run with no broker is fenced and never
  re-armed (and fencing is idempotent); a broker-backed run is left for adoption; a fresh lease and an
  in-process active run are never fenced (the `exclude` the engine passes); one `engine.tick()` fences
  an abandoned run; continuing a fenced job re-arms it and the next claim is a fresh attempt;
  `recover_expired` still fences every expired lease (the deliberate CLI difference); and the briefs:
  fenced → “Say *continue*…”, route-blocked → “retries automatically” (not the person), running/queued
  → nothing needed, verified-closed → done; plus the Work surface (`_work()['work']`): `needs_you`
  counts only person-action jobs, the needs-you job sorts first, and the surface says the exact next
  step.
- Bounded group on the final code: `test_v2_longrun test_v16_r6_liveness test_v13_continuation
  test_v13_continuation_service test_core test_review_recovery test_failure_surfacing
  test_v15_reliability test_service_routing` → **119 OK** (43 s; one stack at a time).
- Live observations (engine restarted on this code, `C:\Users\Nick\KelV2Runs\prepared\engine`):
  pre-start live runs `[]`; seven broker-backed runs were adopted and **none** was fenced (states
  `RESULT_RECORDED`/`EXITED`, `orphaned` total 0) — the conservative rule held against real state; the
  Work surface answered `needs_you=0 jobs=1` with the settled probe job reading “Settled: uncertain.”
  The probe engine was stopped by its own pid after checking the listener owner.

### V2-12 — adaptive staffing 2.0 + the two acceptance checks (2026-09-21)

- `tests/test_v2_staffing.py` (new, 13 tests) — thin history changes nothing (and says “minimum 3”);
  two settled missions are below the floor; blocker history asks for one more step (applied); clean
  history asks for one fewer specialist (applied); a hard-rule floor holds against a lower (security
  flag → held at D2, reason names the rule); mixed history is not evidence; a raise never breaks the
  rule table (R1 / low-decomposition holds D2, `applied False`, reason names the gate); `resolve`
  applies the legal step and equals `decide` with no history; graceful when the workforce tables are
  absent; the D1 path applies a step down to solo; the D1 path records a raise without smuggling it;
  the D2 path refuses with its explicit “use run_d1” sentence when history steps down.
- Bounded group on the final code: `test_v2_staffing test_workforce_d1 test_workforce_d2
  test_workforce_parallel test_workforce_assignment test_workforce_assurance test_workforce_learning
  test_v14_team test_v15_roles` → **269 OK** (106 s; one stack at a time).
- **Acceptance check — learning removal:** `test_v2_learning` (now **20 OK**) gained
  `test_removing_a_learning_through_the_surface_purges_it`: a learning recorded through the real
  service disappears from both the default and `include_disabled` views after the existing guarded
  `forget` action. Removal was already satisfied by that path; no new removal code was written.
- **Acceptance check — unbrokered abrupt stop, proved live:** scratch data root with a running
  engine; a run claimed with a 5 s lease, **zero broker rows**, not active in that engine; after
  expiry the **live engine's own tick** fenced it — run `ORPHANED`, event detail
  `{'recovery': 'runtime'}`, job `WAITING_RESOURCE`, milestone `UNCERTAIN`. This is the counterpart to
  the V2-11 live probe (seven broker-backed runs adopted across a restart, `orphaned` total 0):
  brokered = adopted and never fenced; unbrokered = fenced and never replayed. The scratch root was
  removed after the probe and the engine stopped by its own pid.

### V2-13 — local execution isolation (2026-09-21)

- `tests/test_v2_isolation.py` (new, 10 tests) — a Windows system folder is refused with its label; a
  user credential folder is refused; an environment-protected app folder (`KEL_PROTECTED_PATHS`) is
  refused (including an inner path); Kel's own data root is refused while a plain temp project is
  allowed; `coding.snapshot` refuses a sensitive source before any git call; `scrub_secrets` drops
  every secret-shaped name and keeps the named credential plus `KEL_*`; `child_env` keeps only its own
  provider credential and nothing else secret-shaped; the session directory becomes the child's
  TMP/TEMP/TMPDIR and survives cleanup as “removed”; the read-only leaf argv is pinned (`-s`,
  `read-only`, `sandbox_mode="read-only"`, `--disable`).
- Bounded groups on the final code (one stack at a time): `test_v2_isolation test_coding_boundaries
  test_coding_recovery test_coding_transport test_isolated_recovery test_broker_recovery
  test_v15_credentials test_core` → **108 OK** (15 s); `test_apply_changes test_v16_r7_credentials` →
  **11 OK** (6 s). The apply suite exercises the module where the destination guard now sits.
- No live process was killed and no scratch root was needed for this increment: the checks are pure
  rules plus one argv pin, exercised in-process.

### V2-14 — network permissions (2026-09-21)

- `tests/test_v2_network.py` (new, 14 tests) — default `full` changes nothing; `none` blocks with the
  sentence and records it; `approved` matches exact and parent domains; an unlisted host **asks**
  (one pending request + the plain sentence); approving adds the exact host and the next decision
  allows it (subdomains included); denying keeps it blocked; per-Project scopes beat the default and
  per-tool rules beat the project; a tool-scope approval updates the tool rule; `perform_request`
  refuses **before any network I/O**; bind/unbind never leaks a store; history and requests list
  newest-first; a one-argument hook keeps working (arity fallback).
- Bounded group on the final code (one stack at a time): `test_v2_network test_v2_connections
  test_v2_oauth test_v2_connection_bridge test_capabilities test_v16_r8_migrations` → **155 OK**
  (101 s). Two existing hardening pins failed on the first run because `bind()` initially overrode a
  deliberately patched hook; the fix (an explicit rule source wins) is recorded, and the seam's own
  pins hold again.
- Live loop (engine restarted on this code, `C:\Users\Nick\KelV2Runs\prepared\engine`, driven only
  through `/api/connections`): `policy get → default mode=full`; a probe connection saved with an
  unroutable base (`http://203.0.113.9/`); mode `none` → “You set Kel to no internet for default, so
  nothing is sent.”; mode `approved` + `['example.com']` → “203.0.113.9 is not on the approved list
  for default. Approve it in Connections, or change that scope to full internet, then ask again.”
  with `pending asks → 1`; `history` → `[('203.0.113.9','ask'), ('203.0.113.9','blocked')]`; mode
  restored to `full`; the engine was stopped by its own pid and its port shows only TIME_WAIT.

### Priority 9 — the promotion gate's inspection door (2026-09-21)

- Scope resolution first (D-44): `Kibble` is undefined in the directive and roadmap; its only in-repo
  placement is Astra's presentation lane. The queue line's third term — the promotion gate — already
  exists as recorded-never-applied machinery; only a **door** was missing.
- `tests/test_v2_kibble_gate.py` (new, 5 tests) — an empty queue reads as zero with the honest note; a
  queued promotion is visible and project-scoped; a shadow proposal is visible with its prediction and
  mission filter; the door is **read-only** (team_events and memories counts unchanged by reads); and
  with the shadow flag off nothing is recorded, so the door stays empty.
- Bounded group: `test_v2_kibble_gate test_workforce_learning test_v14_team test_v2_staffing
  test_v15_roles` → **67 OK** (19 s).
- **Deferred, not removed:** the dev-mission schema and candidate model wait on Nick's definition of a
  Kibble Build Update (a product concept owned by Nick/Astra; absent from the durable directive). The
  requirement stays in `MARATHON_STATE.md` and `RESUME.md`; the item is NOT complete.
  Evidence: `docs/v2/evidence/p9-promotion-gate/README.md`.

### V2-17 — manual upgrade reliability / migration validation (2026-09-21)

- `tests/test_v2_upgrade.py` (new, 6 tests) — the inventory covers the V2 tables with counts and a
  readable ledger; a backup carries every V2 row and never the credentials file; a restore brings
  every table and the ledger back **exactly** (post-backup mutations gone); a staged restore touches
  nothing live until applied and the second apply is a no-op; the live credentials file survives the
  restore (merge never deletes); re-opening with every V2 module ensuring its schema again changes no
  count and no ledger row.
- Bounded group on the final code: `test_v2_upgrade test_v14_upgrade test_v15_upgrade
  test_v16_r8_migrations test_migration` → **18 OK** (7.5 s).
- Live demonstration (engine restarted on `C:\Users\Nick\KelV2Runs\prepared\engine`, driven only
  through `/api/backup`): `inventory → 107 tables, ledger = 24 migrations`; the real accumulated V2
  spread `{connections: 3, connection_events: 1, network_policy: 1, network_events: 2,
  routing_outcomes: 3, memories: 3, memory_proposals: 1, team_events: 3, oauth_flows: 1}`; `create` →
  description with the V2 counts (`connections 3, conversations 12, jobs 3, memories 3, messages 26,
  projects 2`); `inspect` matched; the copied database's counts matched the live inventory exactly;
  the probe folder was removed and the engine stopped by its own pid.

### Kibble Build Update — the backend contract (2026-09-21)

- Definition correction first (D-46): Kibble is the user-facing name for Fix Capture / Dogfood
  behavior (the definition lived in Nick's handoff, not the repo); the workflow and the measured
  reuse map are recorded in `docs/v2/evidence/kibble-build-update/README.md`.
- `tests/test_v2_build_update.py` (new, 10 tests) — `start()` builds a mission on the existing work
  machinery (findings' context recorded; verified repo identity; baseline revision; the coding
  contract's kind/root/test_command) and REFUSES unknown/closed findings, non-repo sources, sensitive
  roots (containment) and a dirty baseline; `candidate()` reports BUILDING and creates nothing before
  the mission settles; after settle it assembles a candidate under the engine's own `candidates/<id>/`
  (a `build-report.json` on disk; the artifact location is outside the source root); unverified/
  failed evidence is recorded verbatim and still yields only a REVIEWABLE candidate; unresolved
  findings are listed and Fix Capture statuses are never rewritten; `review()` refuses any actor but
  the person and refuses a second review; `promote()` refuses in plain words for every state; and the
  no-promotion proof is structural (no install path exists).
- Migration ledger: build_update is migration 29 (`v21-build-update`); the ledger suite's pins
  (MODULES, EXPECTED_MAX, the owning name) were updated deliberately and re-pass.
- Bounded group on the final code: `test_v2_build_update test_v16_r8_migrations test_v2_upgrade
  test_coding_boundaries test_v2_kibble_gate test_dogfood` → **59 OK** (16 s).
- Live (engine restarted on the real V2 root, driven through `/api/dogfood {action:'build_update'}`):
  a finding was captured (`FIX-0001`), `start` created mission `kbm_e7b488ec` with job `8759bedd`,
  baseline `eb265757` (the pushed HEAD) and scope `['runtime']`; `status` showed the job `READY` with
  stage `OPEN`; `candidate` before settle answered `BUILDING` with no candidate; `promote` refused
  with “Installing a candidate is not part of Build Update…” (HTTP 400); the job was cancelled
  cleanly (`CANCELLED`); and the source checkout's `git status --porcelain` was **empty before and
  after** — the mission never touched it. The first live attempt had been refused by the
  clean-baseline guard while this very increment was still uncommitted: recorded as the guard working.
- Re-verified in the recovery run (2026-09-22, `dev/v2` @ `eb26575`): the same bounded group was re-run
  from `runtime/` — `python -m unittest tests.test_v2_build_update tests.test_v16_r8_migrations
  tests.test_v2_upgrade tests.test_coding_boundaries tests.test_v2_kibble_gate tests.test_dogfood`
  → **59 tests, OK** (15.3 s). That confirms the committed code, not the working copy.

### V2-06 / V2-07 / V2-08 — the missing read surfaces (2026-09-22)

- `tests/test_v2_attention.py` (new, 5 tests) — a fenced run's row carries `priority='now'`, a reason,
  its age, its project/conversation and exactly one direct action (`resume` → `/api/send`, because a
  fenced run resumes as a conversation continuation); a pending approval offers `answer` →
  `/api/approval` and counts in `related.approvals`; a settled-bad job is `soon` with `retry` →
  `/api/retry`; a settled-verified job is `later` with no action; grouping/filters/sorting are reported
  and nothing offers a snooze the authoritative state cannot honour.
- `tests/test_v2_recipes_library.py` (new, 7 tests) — entries carry category/favourite/use; search
  matches name, description and step titles and refuses an empty query; favourites/recent/runs follow
  real use; categories count; `duplicate` drafts a copy (never saves one) and a saved copy stays in one
  project while a second duplicate finds a free id; `history`/`last_result` read the engine's own jobs
  (artifact path + digest included); a category must be short. **The suite caught a real defect:** one
  project's recipe used to make every other project's library raise (`entries()` now skips ids that do
  not resolve for this project).
- `tests/test_v2_activity.py` (new, 6 tests) — plain sentences with project grouping; a row carries its
  result/evidence/recovery hint; project/kind/failure/search/date filters; no payload, contract or run
  id ever reaches a row; an unmapped event is reported as `other` rather than hidden.
- Migration ledger: recipes now owns migration 30 (`v2-recipe-library`); the ledger pins (EXPECTED_MAX,
  the owning name, the module map) were updated deliberately and re-pass.
- Bounded group on the final code: `test_v2_attention test_v2_longrun test_v2_activity
  test_v2_recipes_library test_v16_r8_migrations test_v13_recipes` → **48 OK** (26 s).
- Live journeys on the real root (`docs/v2/evidence/v2-18/runs/2026-09-22-slice3.json`,
  `-slice4.json`): **J-RECIPE PASSED** (all fourteen V2-07 scope items answered by the real surface),
  **J-ACTIVITY PASSED** (the real timeline and its filters), **J-MODEL PASSED** (a real turn's stored
  route read back through `/api/model why` — `selected == provider`, `chain[0] == selected`, the
  sentence naming the model), **J-CONV PASSED** (two real turns, one persisted thread, four messages,
  user/assistant alternating).

### V2-18 — synthetic acceptance journeys (2026-09-22)

- **Slice 1** on the real V2 root (`docs/v2/evidence/v2-18/runs/2026-09-22-slice1.json`, engine pid
  8144 then 61660): J-FIX (Fix Capture round trip), J-UPGRADE (110 tables, 26-row ledger, every V2
  table present), J-SEC (the engine's own data folder, the protected `KelDogfoodCandidate` app folder
  and a non-repository folder each refused with their own sentence) — all PASSED.
- **The Kibble Build Update journey** (`runs/2026-09-22-kbu.json`, then `-r2`/`-r3` on the final code):
  a real codex-code 0.142.5 dispatch repaired a labelled fixture repository inside the isolated
  `repositories/<job_id>` copy, `python -m unittest -v` ran green, `check_evidence == VERIFIED`, the
  candidate carried the workspace revision with the baseline as an ancestor, `review approve` moved it
  to `APPROVED`, a second review was refused, `promote` refused before **and** after approval, Fix
  Capture statuses stayed `OPEN`, and the source checkout was clean before and after. Claims C1–C4 in
  `ACCEPTANCE_MATRIX.md` are shown one by one.
- **Negatives** (`runs/2026-09-22-kbu-negatives.json`): a cancelled mission claims nothing (job
  `CANCELLED`, no candidate record, `evidence: null`).
- **Three defects found and fixed here** (each pinned by a test): a non-repository source was refused
  with a leaked raw git message; a verified candidate still carried `note: "the mission produced no
  artifact"`; and — found by the negatives journey — a mission that closed **FAILED** (its test command
  always failed; the runtime had added a `sitecustomize.py` monkeypatching `sys.exit`, and the
  reviewer's own finding said so) still had its candidate claim `verified: true` and the finding as
  fixed, because one run's evidence was read as the mission's verdict. `_assemble` now requires the
  mission's own `verdict == 'VERIFIED'` **and** milestone `ACCEPTED` before any verified claim; the
  measured example is recorded in `DECISIONS.md` (D-49).
- Bounded group after the fixes: `python -m unittest tests.test_v2_build_update
  tests.test_v16_r8_migrations` → **17 OK** (15.7 s).

### V2-18 — slice 5: Work, Needs Your Attention, Recovery, Remote (2026-09-23)

One owned engine, identity proven before use (pid 15116, port 60979, command line naming the data
root). Evidence: `docs/v2/evidence/v2-18/runs/2026-09-23-slice5-r3.json` (the FAILED first attempts,
`-slice5.json` and `-slice5-r2.json`, are kept as the record).

- **J-WORK PASSED** (2 claims): a real request ran on the real root and settled CLOSED with a recorded
  artifact (`result.md`, 379 bytes, lineage id) and an explained verdict — the `manual_review` check
  said "The reviewer returned no usable assessment." (provider `claude`), the row said "Settled:
  uncertain." and offered the retry; then a real claim with an expired lease went through the engine's
  `recover_abandoned()`: `ORPHANED` with a fresh epoch, milestone `UNCERTAIN` +
  "Expired run; native state requires reconciliation", job `WAITING_RESOURCE`/`UNCERTAIN`, a second
  recovery fenced nothing, the row read `fenced` + `needs_you` + `resume → /api/send`, and
  `/api/diagnostics` reported `expired_unfenced: 0`.
- **J-ATTN PASSED** (3 claims, 1.5 s): a real ask raised through the coding adapter's own `approval()`
  appeared as one attention row (`needs_you`, `priority: now`, `related.approvals: 1`, `direct {answer,
  /api/approval}`); one action answered it `APPROVED`, the waiting runtime continued without a second
  ask (`run` back to `RUNNING`, row `needs_you: false`, `approvals: 0`), and answering the same ask
  twice was refused.
- **J-RECOV PASSED** (2 claims): a real request that could not run kept its text and its reason ("This
  project needs a test command. Set it in Project context before coding.") with no job fabricated;
  `/api/retry` was accepted on the same submission (one row, nothing duplicated) and re-settled with
  the same reason; a request that is not `FAILED`/`INTERRUPTED` was refused with "This request is not
  ready for retry".
- **J-REMOTE PASSED** (2 claims, backend half): the listening web-host gateway was proven by pid +
  command line + port ownership, then probed with no session: the API answered `401 {"success":false,
  "error":"Authentication required","code":"UNAUTHORIZED"}` and the engine's bearer token appeared in
  neither body.
- **Two limits recorded, not passes:** no real work reached `VERIFIED` (the reviewer answered nothing
  usable), and a request that produces no job is recorded as `DISPATCHED` with `job_id: null` and never
  settles. Both are in `KNOWN_LIMITATIONS.md` with their next steps.
