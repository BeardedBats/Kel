# KEL V2.0 — MARATHON STATE

Machine-readable-ish program state. A resume run reads `MARATHON_DIRECTIVE.md` → this file → `RESUME.md`
and then continues the exact `current_item`. Update this file whenever a phase starts or closes.

```yaml
program: kel-v2.0
line: v2                    # development line created by this setup commit
branch: integration/v2       # current packaged integration line; dev/v2 remains its source line
base_commit: a471e17ac25590369e74824ebed0dd7b54e4b00b   # V2.0 base (dev/daily-driver head at setup)
setup_commit: 47eb3b49322a7cfbe85bbee7a0674c77037b127f   # V2 program initialization; this file's hash record is the records commit
remote: https://github.com/BeardedBats/Kel
phase: V2-19                # bounded regression in progress on staged r26
next_item: V2-19 packaged Projects/Knowledge/Map, Kibble, Connections, Permissions, and transcription actions on isolated r26 data; then V2-16 timings where accessible.
status: partial
# V2-04 (the Connection Framework) is closed; its two open needs are carried as V2-04a/V2-04b in FEATURE_LEDGER.md.

deferred:
  - "V2-05-history (the phone drawer/history presentation): deferred for Shell integration — Astra owns the presentation on ux/v2-shell; the requirement is kept, never removed."

paths:
  source_v2: C:\Users\Nick\Desktop\Kel\kel-v2
  source_integration: C:\Users\Nick\Desktop\Kel\kel-v2-integration  # active r26 source checkout
  source_predecessor: C:\Users\Nick\Desktop\Kel\kel-daily-driver   # dev/daily-driver, reference only
  shared_git_dir: C:\Users\Nick\Desktop\Kel\Kel-Repo\.git         # one object database for all trees
  v2_test_data: C:\Users\Nick\KelV2Runs\prepared                  # V2 development/test data root
  v2_candidate: C:\Users\Nick\KelV2Candidate                      # r20 live; r26 is staged separately

protected_paths:            # never modify, uninstall, overwrite, reset, migrate, clean or use as V2 test data
  - C:\Users\Nick\KelDogfoodCandidate        # the stable dogfood build Nick actually uses
  - C:\Users\Nick\KelDogfoodRuns\prepared    # real dogfood data (Fixes, screenshots, prompts, library)

phases:
  V2-00: done        # developer line + durable program state (this setup commit)
  V2-01: done        # Connections model + central management (migration 23, /connections surface)
  V2-02: done        # Generic REST Connection + Test Connection (migration 24, perform_request choke point)
  V2-03: done        # Personal Connections: the eight services as data (migration 25, auth_prefix)
  V2-04: partial     # Connection Framework: three templates + request policy/retries built; actions and OAuth not
  V2-05: partial     # iPhone Kel PWA V1 — voice (real Muse) and the send round trip (real model, continued) proved on the phone; drawer history (DEFERRED for shell integration), job attention, project routing open
  V2-06: queued      # Needs Your Attention 2.0
  V2-07: queued      # Recipes 2.0
  V2-08: queued      # Activity 2.0
  V2-09: done        # Routing intelligence — decayed outcome evidence, evidence-aware Automatic ordering (floor-protected), read-back "Why this model?", tool requests become real work turns
  V2-10: done        # Learning 2.0 — evidence-thresholded suggestions (existing proposal queue), off/on without deletion, explain, authority fence
  V2-11: done        # Long-running work 2.0 — runtime fencing of abandoned runs (never re-played), the Work brief (shipped/open/why/next + needs_you)
  V2-12: done        # Adaptive staffing 2.0 — one bounded step of outcome-history advice on the existing staffing paths (advice recorded on every staffing.decided)
  V2-13: done        # Local execution isolation — sensitive-root refusal at the autonomous seams, disposable per-run sessions, secret-shape env scrub (no VM, no sandbox rewrite)
  V2-14: done        # Network permissions — modes + per-tool/per-Project rules behind the one seam, ask-before-a-new-domain, access history
  V2-15: queued      # Real dogfood integration pass
  V2-16: partial     # Dark Settings and setup path repaired; conversation/project/remote timings pending
  V2-17: done        # Manual upgrade reliability — inventory before/after, and the V2 state proved to survive backup→restore exactly (no updater infra)
  V2-18: partial     # Backend journeys and the F1 rechecks passed; J-REMOTE and Shell/phone journeys remain
  V2-19: partial     # r23 setup and Dark Settings; r26 recipe/Work/attention/recovery plus five engine journeys passed; remaining groups open
  V2-20: queued      # V2 release candidate

invariants:
  - "one capable personal assistant with hidden orchestration — Nick never learns workers, leases, scopes, staffing graphs, runtime topology, routing internals, event streams, MCP plumbing or execution packets"
  - "Fix Capture stays exactly as built (OPEN / BATCHED / FIXED / DISMISSED); it is not Jira and is never rebuilt"
  - "no second system of anything: no second memory, workflow, auth, permission or task database"
  - "never single-side colored borders or accent rails; typography, spacing, background tone, subtle full-perimeter neutral borders only"
  - "desktop Kel may stay on; cloud Kel is V2.5 and does not start here"
  - "disk hygiene: no indefinite temporary worktrees, no obsolete node_modules/build copies, no duplicate installers, no accumulating data roots"

temporary_worktrees: [C:\Users\Nick\Desktop\Kel\kel-v2-integration]  # branch integration/v2 — the candidate build line (see the section below); remove once the candidate is packaged and reviewed, or once Astra's line absorbs the merge
```

## Integration line (2026-09-22) — created this turn, kept on purpose

`C:\Users\Nick\Desktop\Kel\kel-v2-integration` on branch `integration/v2` @ `fe5e6b7` merges
`dev/v2` @ `7b18618` with Astra's committed Shell baseline `ux/v2-shell` @ `0052075` (verified from the
merge's own second parent; the merge commit's own message still says `681e005`, which was her tip
earlier in the turn — a pushed merge is never rewritten, so this section is the accurate record). One
conflict was resolved in the web-host unit suite; see `docs/v2/evidence/integration/README.md`. The
worktree exists because the packaged candidate must be built from the union, not from either line
alone. Its `desktop/node_modules` is a junction to `dev/v2`'s (bun cannot resolve nested packages
through it, so a real `bun install` is needed before any build there). Remove this worktree once the
candidate is packaged and reviewed, or once Astra's line absorbs the merge — whichever comes first,
and record it here when it goes.

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
- **Layout audit done (so the next run does not go looking):** the shell already handles the notch and
  home indicator — `viewport-fit=cover` is declared in the renderer shell and `env(safe-area-inset-*)` is
  used in `styles/layout.css`, `styles/themes/base.css`, the guid page and the chat action sheet. The Kel
  surfaces' own CSS has no phone-breaking widths: `kel-tokens.css` contains one 132px element, one 560px
  max-width, and `min-width: 0` on the flex children (the pattern that stops a row overflowing). So the
  remaining V2-05 work is **not** a CSS rescue: it is the phone *journeys* — a home screen that shows
  running/recent/failed work and Needs Your Attention one-handed with answer/approve/deny/grant/review/
  resume/stop, and voice through Muse from the phone — and verifying them in a real browser at a phone
  viewport against the built app (which needs a build + the gateway, so it is its own increment, not a
  quick check).

## V2-05 send — closed; the phone sends for real (next: history, attention, routing)

- **The measured blocker is gone and the round trip is proved.** The phone profile had no assistant to
  choose because the `kel` assistant is seeded by the Electron main process (`initializeKel`) and the
  standalone `bun run webui` host never ran that path. The webui now performs the same integration at
  start-up (register the Kel ACP agent in **module form** — `python -m kel.acp_host`; the script-path form
  cannot resolve the ACP host's relative imports during `initialize` — create the single `kel` assistant,
  leave exactly it enabled). The desktop's source branch got the same module-form fix; its packed engine
  never hit this.
- **Journey H now proves the positive path** (real browser 393x852 → gateway → aioncore → Kel engine
  (ACP) → CLI model): one `kel` pill (auto-selected) → send enables → turn lands → real reply ("Phone
  send check received.") → settle → second thumb-typed turn → second reply ("still here"); post-auth
  watch clean (no failed reads, no dead sockets, no console errors). Evidence:
  `docs/v2/evidence/v2-05/` (findings-H.json, H1-H3 PNGs).
- **Write-ups a next run needs:** assistant replies render markdown inside a shadow root (`ShadowView`),
  so `innerText` cannot see them — read `.markdown-shadow-body` text explicitly; the conversation's send
  control read as disabled even when it accepted the next send (recorded, not gated on); a full-page load
  of `/conversation/<id>` on the phone rendered a blank body in one authed probe; tapping the home's
  recent entry text timed out once (try the drawer path first).
- **V2-05 remains open as:** (c) job-driven attention actions (real job state, no fixtures), (d)
  conversation history / the drawer from the phone above all, and conversational project routing.
  V2-04a/V2-04b remain the next deliberate program items per the directive priorities.
- **Evidence:** `TEST_EVIDENCE.md` (V2-05 third pass); desktop 358 pass (43 files); `tsc` clean; 4 new unit
  tests (`kel-integration.unit.test.ts`).

## V2-04a reconnaissance for the next run (source-backed; no code changed)

The assistant bridge's landing points, read from the tree:

- **The runtime's tools are not MCP.** The shipped coding runtime is Claude Code, invoked with
  `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` (`runtime/kel/native.py:92`), and a test asserts
  no capability row speaks of MCP (`runtime/tests/test_capabilities.py:40`). The bridge must ride the
  existing capability/tool plumbing, not a second MCP server.
- **The capability layer already declares a tool surface.** `runtime/kel/capabilities.py` maps each
  capability to the runtime's real tool names (≈43–52) and feeds `_TOOL_MAP` / `capability_for_tool`. Its
  docstring carries the binding rule this bridge flips: *"Google Drive and Connected apps are
  deliberately absent: this release has no production effect path that could honour them, so they are not
  offered as switches that could not be kept."* — the bridge lands first, the switch second.
- **The action side is data and ready to call.** `runtime/kel/connection_actions.py`: `actions()` (121),
  `actions_for(service_id)` (126), `action(action_id)` (132); the mutating rule sits in the module header
  (line 14: a mutating action is refused unless Nick confirmed — none ship yet). `runtime/kel/connections.py`
  owns schema/run/history (migrations incl. `_add_actions_table` 134; `ensure_schema` 149).
- **A mid-turn confirmation pathway exists.** `runtime/kel/acp_host.py` is poll-based
  (`Host(client, emit, poll_interval=.25)`: 156), emits `agent_message_chunk` (167), and already has
  `_resurface()` (188) — *"After an interruption, bring the active vetting prompts back into view"* — a
  user-prompt/vetting mechanism the bridge's confirmation can build on. `ServiceClient.call()` (129) is
  the engine transport (reads `desktop-session.json`).
- **Open questions the next run must answer before designing:** the direction of `_TOOL_MAP` (does the
  engine observe the runtime's tool calls or provide tools to it?), where Projects state lives for
  per-Project gating (V2-02), and how the access-history writer receives call facts (V2-04's
  connection/action/domain/status/duration shape).

## Parallel-ownership change (2026-09-21) — V2-05-history deferred for shell integration

Astra is actively implementing the Figma Shell on `ux/v2-shell` and now owns the phone drawer/history
presentation, the conversation shell, the composer, the responsive/mobile shell, Tools and Ramble/Kibble
presentation, and the global visual tokens. Implementing V2-05-history (the phone drawer and conversation
opening) now would collide with that work, so it is **temporarily deferred for shell integration**:

- **V2-05 stays PARTIAL.** Its history/attention/routing requirements are kept in this record and in
  `RESUME.md` — they are not dropped, and the phase is not marked complete.
- The measured notes for the history increment (the blank `/conversation/<id>` deep load, the inert rail
  at phone width, the home-entry tap timeout, the drawer as the phone's real navigation) remain valid;
  they are recorded in `KNOWN_LIMITATIONS.md` and stay the checklist for the Shell integration pass.
- **The next safe backend item is V2-04a** (assistant-callable Connection action bridge), whose
  reconnaissance is committed at `7a82996`. Do not start V2-05-history without a fresh recorded decision
  that the Shell integration has landed.
- If a backend change needs a renderer contract Astra will eventually absorb, write it in
  `docs/v2/PARALLEL_SHELL_TOUCHES.md` instead of editing renderer files.

## V2-04b — BUILT (2026-09-21)

The OAuth foundation is done: providers as data (`kel.connection_oauth`), the flow in `oauth_flows`
(migration 28 — single-use state + PKCE verifier, never a token), the trade through
`perform_request`, tokens in the same in-memory custody (`auth_state`/`auth_scopes`/`auth_expires`/
`oauth_provider` on the row in plain words), the shell claims a finished sign-in once into the
OS-backed custody, refresh on expiry (`needs_reconnect` when it fails), revoke through the provider.
The only public route is `/oauth/callback`, protected by the single-use state (D-34, D-35). Google
Drive is the reference (`gdrive-files`). Evidence: `docs/v2/evidence/v2-04b/README.md` — engine
suite 10/10 incl. a real-HTTP lifecycle with a real S256 PKCE check, desktop 363 passed, tsc clean.
Honest limits: real Google sign-in needs Nick's client ID + browser; the phone cannot finish a
sign-in yet (loopback callback); the sign-in between callback and claim lives in engine memory only.
`next_item` moves to Connection execution hardening, then routing intelligence.

## V2-04 hardening — BUILT (2026-09-21)

The choke point now carries its own rules (D-36): one opener built once; a bounded redirect chain;
a service's `Retry-After` honoured but capped; the V2-14 network-rule seam asked **before** anything
leaves the computer (and again for a redirect's host, failing closed when the rule source errors);
an answer past the reading cap labelled as cut short; and a choke-point refusal reaching the person
as its own sentence. Six new tests in `ExecutionHardeningTests` (all green). No rules are configured
yet, so behaviour is unchanged until V2-14 fills the seam. `next_item` moves to routing intelligence.

## V2-04a — BUILT and proved live (2026-09-21, `dev/v2` @ `d3bbf65`)

The assistant-callable Connection action bridge is done: the `connections` capability, the
`kel.connection_tools` bridge, the `kel.conn` helper the runtime runs as a shell command, engine
memory custody pushed by the shell (D-33), mutating confirmation through the existing approval rows
(D-32), and `source` provenance (migration 27). Evidence: `docs/v2/evidence/v2-04a/README.md` —
the engine journey (16 tests) plus the **live** run where a real runtime found the connector, called
`github-whoami`, used the bounded login, and the access history recorded `source: runtime`. The same
run measured two honest limits: Claude Code is quota-blocked on this machine today (codex carried
the work), and the phone's turns are conversational by design, so the bridge is reachable from the
phone only once the Shell's Work route exists (Journey J held, recorded in
`KNOWN_LIMITATIONS.md`). It also found and fixed a real defect: the engine now exports
`python -m kel` to its runtimes (`d3bbf65`). `next_item` moves to V2-04b (the OAuth foundation).

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
