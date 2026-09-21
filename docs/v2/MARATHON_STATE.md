# KEL V2.0 — MARATHON STATE

Machine-readable-ish program state. A resume run reads `MARATHON_DIRECTIVE.md` → this file → `RESUME.md`
and then continues the exact `current_item`. Update this file whenever a phase starts or closes.

```yaml
program: kel-v2.0
line: v2                    # development line created by this setup commit
branch: dev/v2
base_commit: a471e17ac25590369e74824ebed0dd7b54e4b00b   # V2.0 base (dev/daily-driver head at setup)
setup_commit: 47eb3b49322a7cfbe85bbee7a0674c77037b127f   # V2 program initialization; this file's hash record is the records commit
remote: https://github.com/BeardedBats/Kel
phase: V2-05                # iPhone Kel PWA V1 — PARTIAL: installability exists and is pinned; the phone surface is not done
next_item: V2-05            # continue V2-05: the phone surface and its journeys (see ROADMAP.md)
status: partial
# V2-04 (the Connection Framework) is closed; its two open needs are carried as V2-04a/V2-04b in FEATURE_LEDGER.md.

paths:
  source_v2: C:\Users\Nick\Desktop\Kel\kel-v2
  source_predecessor: C:\Users\Nick\Desktop\Kel\kel-daily-driver   # dev/daily-driver, reference only
  shared_git_dir: C:\Users\Nick\Desktop\Kel\Kel-Repo\.git         # one object database for all trees
  v2_test_data: C:\Users\Nick\KelV2Runs\prepared                  # V2 development/test data root
  v2_candidate: C:\Users\Nick\KelV2Candidate                      # NOT created yet (install only when a checkpoint needs it)

protected_paths:            # never modify, uninstall, overwrite, reset, migrate, clean or use as V2 test data
  - C:\Users\Nick\KelDogfoodCandidate        # the stable dogfood build Nick actually uses
  - C:\Users\Nick\KelDogfoodRuns\prepared    # real dogfood data (Fixes, screenshots, prompts, library)

phases:
  V2-00: done        # developer line + durable program state (this setup commit)
  V2-01: done        # Connections model + central management (migration 23, /connections surface)
  V2-02: done        # Generic REST Connection + Test Connection (migration 24, perform_request choke point)
  V2-03: done        # Personal Connections: the eight services as data (migration 25, auth_prefix)
  V2-04: partial     # Connection Framework: three templates + request policy/retries built; actions and OAuth not
  V2-05: queued      # iPhone Kel PWA V1
  V2-06: queued      # Needs Your Attention 2.0
  V2-07: queued      # Recipes 2.0
  V2-08: queued      # Activity 2.0
  V2-09: queued      # Routing intelligence
  V2-10: queued      # Learning 2.0
  V2-11: queued      # Long-running work 2.0
  V2-12: queued      # Adaptive staffing 2.0
  V2-13: queued      # Local execution isolation
  V2-14: queued      # Network permissions
  V2-15: queued      # Real dogfood integration pass
  V2-16: queued      # Performance + UX polish
  V2-17: queued      # Manual upgrade reliability / migration validation
  V2-18: queued      # Synthetic V2 acceptance journeys
  V2-19: queued      # Full V2 regression
  V2-20: queued      # V2 release candidate

invariants:
  - "one capable personal assistant with hidden orchestration — Nick never learns workers, leases, scopes, staffing graphs, runtime topology, routing internals, event streams, MCP plumbing or execution packets"
  - "Fix Capture stays exactly as built (OPEN / BATCHED / FIXED / DISMISSED); it is not Jira and is never rebuilt"
  - "no second system of anything: no second memory, workflow, auth, permission or task database"
  - "never single-side colored borders or accent rails; typography, spacing, background tone, subtle full-perimeter neutral borders only"
  - "desktop Kel may stay on; cloud Kel is V2.5 and does not start here"
  - "disk hygiene: no indefinite temporary worktrees, no obsolete node_modules/build copies, no duplicate installers, no accumulating data roots"

temporary_worktrees: []     # disk-hygiene note: none exist right now; record any created here
```

## V2-01 notes for the next run

- **What exists now:** `runtime/kel/connections.py` (migration 23 `v20-connections`) with
  `/api/connections` (`list` / `get` / `save` / `remove` / `set_credential` / `delete_credential`), the
  `/connections` page in the desktop renderer, and credential custody under the `connection:<id>`
  namespace in the existing OS-backed store. The engine stores field names plus a `kel:connection:<id>`
  pointer and never a value.
- **Deliberately absent (do not "fix" it):** no built-in service list, no per-service module or table, no
  network call of any kind, no Test Connection, and no seeded rows. `test_endpoint` is stored for V2-02.
- **V2-02 starts from:** the Generic REST Connection (fields + Test Connection). The store already has
  every field that phase needs; the missing piece is the request layer, the permission gate in front of
  it, and an honest result state (there is no test-result column yet).
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-01 block); engine 1085 OK; desktop 334 pass; `tsc` clean.
- **No candidate was installed** for V2-01 — `C:\Users\Nick\KelV2Candidate` still does not exist.

## V2-02 notes for the next run

- **What exists now:** `Connections.test(id, credentials)` in `runtime/kel/connections.py` with
  `perform_request` as the single outbound choke point, migration 24 (`v20-connection-tests`) holding the
  last check's state/status/duration/sentence, the `test` action on `/api/connections`, the privileged
  `kel:connection-test` channel (sender-guarded; returns the record and never a value), and a
  `Test connection` button on the page.
- **The rule to keep:** nothing calls a service except a click on Test connection. V2-14's network rules
  belong inside `perform_request`; do not add a second HTTP client, and do not add network code to the
  renderer.
- **V2-03 starts from:** the eight personal services still need no code — a service is a Connection Nick
  adds, and what Kel can *do* with it is a tool (V2-04). What V2-03 adds is a real, live check against
  each service and the smallest useful action for each; nothing about the model should change to make
  that possible.
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-02 block); engine 1101 OK; desktop 338 pass; `tsc` clean.
- **No candidate was installed** for V2-02 either, and no real service has been contacted by a test yet.

## V2-03 notes for the next run

- **What exists now:** `runtime/kel/connection_services.py` (the eight services as rows: address, header,
  how the credential is presented, docs, test endpoint, what to fetch, and how sure Kel is), `auth_prefix`
  on a connection (migration 25: `null` = Kel works it out, `''` = exactly as it is, a word = added in
  front), the `catalogue` action on `/api/connections`, and "Set up <service>" rows on the page that fill
  the form in.
- **The rule to keep:** a service is data. No module, table, worker or workflow per service, no branching
  on a service id, and `connections.py` must stay free of service names (a test pins that). Anything Kel
  *does* with a service is a tool — V2-04.
- **V2-04 starts from:** the Connection Framework and its three templates (API Key, OAuth, Bot/webhook),
  standardising credentials, authenticated requests, actions/tools, permissions, Test Connection, errors,
  retries and tests. The OAuth template is what Google Drive needs — its entry knows the address, but the
  account sign-in step does not exist yet, and its note says so. V2-14's network rules belong inside
  `perform_request` in `connections.py`.
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-03 block); engine 1110 OK; desktop 340 pass; `tsc` clean.
- **Still not verified:** no installed-app check, and no real service has been contacted — that needs
  Nick's credentials and stays V2-15's evidence.

## V2-04 closed, and V2-05 notes for the next run

- **V2-04 is closed as the framework** — templates, one request path, data-declared actions, the
  confirmation gate, honest errors, bounded retries, the access history, and the developer page
  `docs/v2/CONNECTION_FRAMEWORK.md`. Two things it needs are carried as follow-ups in
  `FEATURE_LEDGER.md` instead of being claimed: **V2-04a** (a tool the assistant could call an action
  through — the bridge to the coding runtime the desktop agent runs; no Connections capability switch may
  be added before it exists) and **V2-04b** (the OAuth account sign-in flow).
- **V2-05 is the iPhone Kel PWA V1** (login, history, create/continue a conversation, text/paste, voice
  through Muse, Project switching and routing, home showing running/recent/failed work and Needs Your
  Attention, and answering/approving/denying/granting/reviewing/resuming/stopping — nothing else). The
  gateway it grows already exists: the web-host serves the same renderer away from the desktop
  (session-gated, server-side bearer), so V2-05 is about the PWA surface and its journeys, not a second
  backend. No uploads, camera, share sheet, push, or native apps.
- **Carry into V2-05:** the Connections work exposes `/api/connections` (list / get / save / remove /
  set_credential / delete_credential / test / run / actions / events / catalogue). If the PWA surfaces any
  of it, the mutating-confirmation rule and the one-request rule apply there too, and the credential stays
  in the shell — a remote client never receives a value.
- **Reconnaissance done (do not rebuild this):** installability already exists from the donor line and is
  sound — `desktop/public/manifest.webmanifest` (name/short_name/display standalone/theme + background
  colour, 192 and 512 icons), icons at `desktop/public/pwa/icon-180|192|512.png`, and a careful service
  worker at `desktop/public/sw.js` that never caches `/api/`, keeps script/style network-fresh with a
  content-type guard against the SPA fallback, is network-first for navigation, and is version-bumped with
  the old cache deleted on activate. It is registered by `renderer/services/registerPwa.ts`, which skips
  Electron and non-secure origins. V2-05's work is the *surface*, not this machinery; `desktop/tests/
  unit/pwa-install.test.ts` now pins the contract so it cannot quietly rot.
- **What the phone already reaches:** the web-host serves the same renderer (SPA fallback to index.html)
  with the engine behind `/kel/` (session-gated, bearer kept server-side). Routes that exist today:
  `/login`, `/guid`, `/conversation/:id`, `/work` (the Kel work center, which already renders attention
  rows), `/scheduled`, `/activity`, `/transcription`, `/providers`, `/connections`, `/team`, `/settings/*`.
- **So the real V2-05 increment is:** a mobile-first pass over those journeys (viewport and safe-area
  insets, touch targets, no desktop-only affordances), making the home screen's running/recent/failed work
  and Needs Your Attention usable one-handed with answer/approve/deny/grant/review/resume/stop, and voice
  through Muse from the phone on the existing transcription path. Verification is synthetic (a desktop
  browser at a phone viewport over the gateway) plus the installed-app tether check; real iOS Safari
  behaviour can only be confirmed by Nick — recorded in `KNOWN_LIMITATIONS.md`.

## V2-04 build notes (historical — the phase is closed)

- **Built:** `runtime/kel/connection_framework.py` (the three templates: labels, hints, credential field
  names, what a check does, plus the request policy's numbers) and bounded, honest retries inside
  `connections.perform_request` (retry a 429/5xx or a dropped connection; never a 401/403/404; bounded by
  the timeout and a budget; the record says how many tries). The renderer's own kind vocabulary was
  deleted — labels, hints and credential field names come with the list.
- **Not built, and not claimed:** (a) a chat tool that lets the assistant use a connection — the engine and
  the surface can run an action when Nick asks, but nothing in conversation can (now carried as follow-up
  V2-04a, and the reason no Connections capability switch exists yet); (b) the OAuth account sign-in step,
  which is what Google Drive needs (its catalogue note says so; carried as follow-up V2-04b).
- **Actions (built since the note above):** `runtime/kel/connection_actions.py` holds eight actions as rows
  over six services; `connections.run()` reads a row, makes the request through the single choke point,
  leaves the payload nowhere and records the fact of the call (domain, status, duration) in
  `connection_events` (migration 26); `events()` reads that history back. Every catalogue action is a read,
  and a `mutating` action is refused unless Nick confirmed. The page has a "What Kel can do" card.
- **If follow-up V2-04a is picked up:** expose an action as a tool the assistant can call — with the same
  permission rule (mutating actions ask first) and the same one-request rule — and keep V2-14's network
  rules inside `perform_request`. Add the capability switch only once that path can honour it.
- **Evidence:** `docs/v2/TEST_EVIDENCE.md` (V2-04 blocks); engine 1126 OK; desktop 344 pass; `tsc` clean.
- **Still not verified:** no installed-app check; no real service contacted; the retries are proven against
  a local stand-in only.

## Model preferences recorded at setup

- Nick works from the iPhone for chat, voice, status, approvals, Project routing and stop/resume (§5 of
  the directive); the desktop may remain on.
- Real dogfood feedback from the stable candidate outranks synthetic tests and can change priorities;
  every priority change is recorded in `DOGFOOD_FINDINGS.md`.
