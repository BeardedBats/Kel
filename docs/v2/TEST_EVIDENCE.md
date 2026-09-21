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
