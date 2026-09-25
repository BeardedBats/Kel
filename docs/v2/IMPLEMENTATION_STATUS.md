# KEL V2.0 — IMPLEMENTATION STATUS

What is actually built, as distinct from what is planned. Updated as phases land.

## Desktop current-Figma continuation (2026-09-25)

The canonical source now has a Kel-style scheduled task detail with real Pause/Resume, Edit, Run now, skip protection, delete confirmation, and History actions. The scheduled list has Figma-style Assistant, Model, and Execution mode controls that open the real edit dialog. Activity uses Figma's empty “All clear” copy. Disposable Windows package checks covered these states at 1440 and 800px. Populated Work, waiting and finished Activity, live scheduled History, and many remaining desktop frames still need implementation and verification. The canonical installed App remains on source `8c67121` until the desktop completion install.
Activity's desktop running row now shows a stored milestone beside its job name, a green progress dot, and a Running label. A bounded engine fixture passed packaged checks at 1440 and 800px. Permissions empty cards also match the current Figma frame. Waiting and finished Activity states, populated Permissions, populated Work, and many desktop frames remain open.
The Projects empty map card now matches Figma's 85px height while retaining Refresh map on hover or keyboard focus. Providers' readiness card now shows three truthful rows, including an explicitly untested model reply. Model has Figma's default-model row structure and real Use, Automatic, and Set up actions. The Add model dialog has the compact Figma field order and saves multiple models. Populated custom-model rows expose provider and model toggles, Check, and options actions. Isolated package checks covered these at 1440 and 800px. A loopback check failed as expected; a healthy remote model remains unverified. Diagnostics' cache/restart controls remain disabled because the runtime does not support their stated behavior safely.

## Current canonical state (2026-09-24)

Consolidation moved all source to `C:\Users\Nick\Desktop\Kel\Kel` on `main`. See `MARATHON_STATE.md` and `FEATURE_LEDGER.md` for current phase status. The early "Not built yet" list below describes the V2 base, before the appended implementation blocks. The current incomplete phases are V2-05, V2-16, V2-18, and V2-19; V2-15 and V2-20 remain planned. The r61 System and r62 Appearance passes are recorded under `evidence/figma-full-audit/`.

This continuation corrected two V2-18 state gaps in the existing engine and Shell paths. A cancelled Build Update reports cancellation without creating a candidate. An answered request without a job settles as `SETTLED`; ACP ends that turn. The existing Kibble page shows the cancelled job and explains that no candidate was created. These changes are now in the canonical App. The latest full engine suite passed 1,289 tests and 14 subtests; desktop passed 396. Tools and local enabled WebUI received fresh packaged checks at 1440/800px.

## Where V2 starts from (base `a471e17`, inherited unchanged)

Kel at the V2 base is a working personal assistant: one Electron desktop shell (the donor-inherited UI
plus Kel's own surfaces) talking to a Python engine that owns durable state, and a desktop web-host
gateway for remote browser use.

- **Engine** (`runtime/kel`): conversation/jobs/milestones, projects and memory, providers and routing
  with honest states, transcription (Muse, live + file, with the credential shared from the copied
  Transcriptions app), vetting, recipes, autonomy/leases/continuation, delegation/workforce internals,
  capabilities/authorization, diagnostics, backups, dogfood (Fix Capture) store — migration 22.
- **Desktop** (`desktop/packages/desktop`): the Kel pages — Work, Team, Projects, Providers,
  Transcription, Autonomy, Activity, Onboarding, Diagnostics — plus Fix Capture (overlay, panel,
  Dogfood Fixes view, Prepare Fix Prompt) and the `kel:*` IPC bridge with its route allowlist.
- **Remote**: the web-host gateway (session-gated, server-side bearer) already serves the same renderer
  away from the desktop; V2 grows this into the iPhone PWA (§5 of the directive).

## Not built yet (V2 scope, all queued)

Connections (framework), iPhone PWA V1, Needs Your Attention 2.0, Recipes 2.0, Activity 2.0, routing
intelligence, Learning 2.0, long-running work 2.0, adaptive staffing 2.0, local execution isolation,
network permissions, performance polish, manual upgrade reliability, V2 acceptance and regression.

## Explicitly absent (and staying absent)

Profiles, workforce dashboards, manual rosters, nested spawning, second memory/workflow/auth/permission
systems, second task database, enterprise RBAC, giant vector DB or knowledge graph, Rust migration,
public A2A, native iPhone/Android apps, phone uploads or push, consumer updater infrastructure, cloud
Kel (V2.5), desktop-as-execution-node (V3.0).

## How this file is maintained

Each phase appends a short block: what changed, which files/modules, the tests that prove it, and the
evidence path. Nothing is marked built without a current test or a recorded installed-app check.

## V2-01 — Connections model + central management (BUILT)

One product term, one store, one place to manage them, and nothing per service.

- **Engine** (`runtime/kel/connections.py`, migration 23 `v20-connections`): the `connections` table and
  a `Connections` service — list/get/save/remove plus credential metadata (`set_credential`,
  `delete_credential`). A connection carries the service name, kind (API key / OAuth / Bot or webhook),
  API address, how the credential is sent, documentation and test addresses, and notes; `state` is
  derived (`ready` / `needs_credentials`). Nothing is seeded and no code branches on a service name.
  Served as `/api/connections` (POST actions + GET list) from `service.py`.
- **Credentials** stay where they already were: the OS-backed store in the main process
  (`desktop/packages/desktop/src/process/services/kel/kelCredentials.ts`), now with a documented
  `connection:<id>` namespace that a model provider id cannot collide with. The engine records field
  names and a pointer (`kel:connection:<id>`) and never a value; the credential IPC routes that metadata
  to `/api/connections`, and the provider view no longer lists connection fields.
- **Desktop**: the Connections page (`renderer/pages/kel/connections`) lists every service with its
  state in words, adds/edits/removes a connection, stores a credential (password field, one-way),
  removes a stored credential, and confirms before removing a connection; it reconciles the engine's
  record with what the shell actually holds and says so when they disagree. Reached from the command
  palette and from the Providers integrations card; deliberately not a primary-nav destination.
- **Not in this phase** (by design): Test Connection, real requests, service templates and the
  developer framework (V2-02 / V2-03 / V2-04); `test_endpoint` is stored but nothing is called.
- **Installed-app check**: not performed for V2-01. The surface is covered in jsdom through the shipped
  components and the real bridge contract; the live pass belongs to the V2-15 integration phase.

## V2-02 — Generic REST Connection + Test Connection (BUILT)

The fields are V2-01's; what this phase adds is the one thing that talks to a service.

- **Engine** (`runtime/kel/connections.py`, migration 24 `v20-connection-tests`): `test(connection_id,
  credentials)` calls `test_endpoint` (or the API address when there is none), applies the credential by
  the method the connection declares (header / bearer / query / basic — a bare value stays bare in a
  custom header, and `Authorization` gets its scheme), and records the outcome: state, HTTP status,
  elapsed time and one fixed sentence. `perform_request` is the only place a Connection request leaves
  the computer — the single choke point V2-14's network rules will live in — and it reads the status and
  nothing else, so a service payload cannot land in Kel's records.
- **What a result can say**: `ok`; `refused` (401/403 — a result, not an error); `not_found`; `busy`;
  `error`; `unreachable`; `timeout`. A failed check never silently clears the credential record, and a
  recorded credential never silently claims the service works.
- **The credential is used once, in memory**: the main process decrypts the value and sends it with the
  check; the engine never stores it, never logs it, and scrubs it out of anything durable. The renderer
  receives the record and never the value — the new `kel:connection-test` channel runs the shared sender
  guard and returns the engine's answer only.
- **Desktop**: a `Test connection` button on every connection that has an address, with the engine's
  sentence shown in the row and the confirmation in the note.
- **Not in this phase**: service-specific actions and tools (V2-03 / V2-04) and network rules (V2-14).
  Nothing is called except when Nick clicks Test connection — no automatic or scheduled checks.

## V2-03 — Personal Connections (BUILT)

Pitcher List, Stripe, Raptive, Google Drive, GitHub, ClickUp, Figma and Discord — known as data, with no
per-service code anywhere.

- **`runtime/kel/connection_services.py`**: one row per service — address, header, how the credential is
  presented, documentation, the test endpoint, and what Nick has to go and fetch. Two functions, no
  branching on a service name, no imports; `connections.py` still contains no service name at all. A
  service added by hand is exactly the same kind of connection as one picked from this list.
- **Honest about the addresses**: each entry says `documented`, `assumed` (the standard WordPress layout
  for Pitcher List) or `to-confirm` (Raptive publishes no API address — Kel says the address comes with
  the credential instead of inventing one), and the surface repeats that sentence.
- **How a service wants its credential** is now part of the connection (`auth_prefix`, migration 25):
  GitHub and Stripe `Bearer `, Discord `Bot `, ClickUp and Figma the value exactly as it is, and `null`
  keeps Kel's old "work it out" behaviour. The trailing space is significant and preserved.
- **Desktop**: the services Kel knows appear as "Set up GitHub" rows with the credential sentence; one
  click fills the form in (name, address, header, how it is presented), and the form asks the
  presentation question in plain words rather than exposing a prefix field.
- **Not in this phase**: what Kel can *do* with each service (that is a tool — V2-04) and a live check
  against the real services, which needs Nick's credentials. Nothing here claims a service works because
  it is listed.

## V2-04 — Connection Framework (BUILT)

The standard parts of a Connection, in one place: the three credential templates, the request policy, and
what a developer reads before adding the next service or action (`docs/v2/CONNECTION_FRAMEWORK.md`, which
states each rule beside the test that enforces it).

- **`runtime/kel/connection_framework.py`**: the three templates (API key, Account authorization, Bot or
  webhook) with their labels, hints, credential field names and a plain sentence about what a check does;
  plus the request policy's numbers, re-presented from the one place they live. It knows no service by
  name, and a test fails if it learns one.
- **Bounded, honest retries** in `connections.perform_request`: a GET is tried again only when the service
  is busy (429 or a 5xx) or the connection dropped; a 401/403/404 is never retried. Each attempt is bounded
  by the timeout, the whole request by a budget, and the record says how many times Kel tried.
- **One vocabulary**: the kind labels, hints and credential field names travel with the list, and the
  renderer's own copy was deleted — a test fails if one grows back, so the engine's words and the engine's
  behaviour cannot drift apart.
- **Carried forward instead of claimed**: two things this framework needs are named as follow-ups in
  `FEATURE_LEDGER.md` (V2-04a and V2-04b) rather than being quietly treated as done — a tool the
  assistant could call an action through, and the OAuth account sign-in step (which is why Google Drive
  stays uncheckable beyond a pasted token). No Connections capability switch is offered until the first
  exists, because `capabilities.py` forbids offering a switch a path could not honour.

### V2-04 continued — actions (what Kel can do with a service)

- **`runtime/kel/connection_actions.py`**: eight actions as rows over six of the eight services (GitHub
  whoami + notifications, Stripe account + customers, Figma, ClickUp and Discord whoami, Pitcher List's
  newest posts). No row exists where Kel does not know the address (Raptive) or where the service needs a
  sign-in step that is not built (Google Drive). Nothing branches on a service id.
- **`connections.run()`** (migration 26, `v20-connection-actions`): reads the row, builds the address from
  the connection's API address, applies the credential by the service's declared method, makes the request
  through the same choke point, and hands back the answer — parsed when it is JSON, bounded, and scrubbed
  of the credential. A `mutating` action is refused unless Nick confirmed it.
- **The access history** (`events()`): the fact of each call — connection, action, domain (never the path
  or a query string), status, attempts, duration. This is the trail V2-14's "show contacted domains,
  access history" will read, and it contains no service data at all.
- **Desktop**: a "What Kel can do" card on the Connections page listing each action with a plain "Run",
  the service's answer shown once where it arrived, and a question first for anything that would change
  something in Nick's account. The new `kel:connection-run` channel runs the shared sender guard and hands
  the engine only the fields the shell holds. The current desktop card says `Run`, keeps credential
  editing inside the selected service row, and places confirmation below the action rows. The current
  catalog has read actions only, so the mutating confirmation is DOM-tested but lacks a packaged state.
- **What this does not yet reach**: no conversation can call an action, so the assistant cannot use a
  connection — the assistant's tools come from the coding runtime the desktop agent runs, and that bridge
  is carried as follow-up V2-04a in `FEATURE_LEDGER.md`. V2-04's own scope (the framework) is complete;
  that bridge is a deliberate product step, not a missing row.

## V2-05 increment — the phone can reach Kel at all

`packages/web-host/src/static-server.ts`: `forwardToKel` now drops `origin` and `referer` alongside the
session cookie. Kel's engine authorizes on `Host` + (`Origin` absent or its own) + bearer
(`runtime/kel/service.py`); forwarding the browser's Origin made `/kel/api/providers`, `/kel/api/autonomy`
and every other mutating Kel route answer 403 from a browser, so a phone could read `/api/state` and
nothing else. The gateway holds the token and is session-gated: it now reaches the engine exactly the way
the desktop does.

## V2-05 second pass — the phone can dictate

`renderer/pages/guid/components/KelMicButton.tsx` no longer talks to `window.kelAPI` itself: it uses
`kelRequest`, the shared transport that falls back to the web-host's session-gated `/kel` gateway in a
browser. Failures are no longer swallowed — a failed `stream_start` says live typing is unavailable and
Kel will transcribe on stop, and the final transcription reports plain sentences instead of transport
errors. Verified against real Muse in a real browser (see `evidence/v2-05/README.md`).

## V2-05 third pass — the phone chooses Kel and sends for real

The measured blocker is closed at its root: the `kel` assistant is seeded by the desktop's main process
(`initializeKel`), and the standalone `bun run webui` host never ran that path — so a browser profile had
no assistant to select and `useGuidSend`'s gate could never open. The webui now performs the same
integration after the backend is healthy (`packages/web-host/src/kel-integration.ts`: register the Kel
ACP agent — **module form**, `python -m kel.acp_host`; the script-path form cannot resolve the ACP host's
relative imports during `initialize`, measured — create the single `kel` assistant, leave exactly it
enabled), and the desktop's source branch spawns the same module form. Journey H drives the whole
positive path live: pills `["kel"]` → send enabled → turn lands → real reply → settle → second turn →
second reply ("still here"), post-auth watch clean. Assistant markdown renders inside a shadow root, so
the journey reads `.markdown-shadow-body` explicitly.

## V2-04a — the assistant bridge to Connections (BUILT, 2026-09-21)

The assistant can call a Connection action through the systems that already exist: a `connections`
capability (offered only because a production path can now honour it), the `kel.connection_tools`
bridge behind `catalog`/`call` on `/api/connections`, and the `kel.conn` helper the runtime runs as
an ordinary shell command. Values reach the engine through a shell push into process memory only
(`kelCredentialIpc.ts` at boot and on change; D-33); the runtime never receives one. Mutating
actions wait on the existing approval rows (exact action digest) and appear as ordinary chat cards;
provenance gains a `source` fact (`shell`/`runtime`, migration 27). Proved two ways: the engine
journey test (helper subprocess → real engine → stand-in service, 16 tests) and a live work turn on
the running engine where a real runtime called `github-whoami` behind the stored credential and used
the bounded login (`evidence/v2-04a/README.md`). The live run also found and fixed a real defect:
the engine now exports `python -m kel` to its runtimes (`d3bbf65`).

## V2-04b — the OAuth foundation (BUILT, 2026-09-21)

One reusable sign-in for account-authorization services (D-34): providers as data
(`kel.connection_oauth`), the flow in `oauth_flows` (migration 28 — single-use state, PKCE verifier,
never a token), the trade through `perform_request` (the one outbound choke point, now with a bounded
form body), the tokens in the same in-memory custody every connection value uses. Durability works
like every other value: the shell claims a finished authorization exactly once into the OS-backed
custody and pushes it back; the engine keeps only its working copy. The connection row carries
`auth_state` / `auth_scopes` / `auth_expires` / `oauth_provider` in plain words. Refresh runs on
expiry (failed → `needs_reconnect` + the plain reconnect sentence everywhere); sign-out hits the
provider's revoke endpoint, then clears both custodies. The only public route is `/oauth/callback`
(D-35): the single-use state is the proof, PKCE S256 where the provider supports it. Google Drive is
the first reference (`gdrive-files`, scope `drive.metadata.readonly`, missing granted scope named in
plain words). Desktop: the main process runs the sign-in end to end (browser → bounded wait → claim
→ custody → supply); the Connections page has one Connect/Reconnect/Sign out button and a status
line. Real Google OAuth was not exercised — it needs Nick's own client ID and a browser sign-in.

## V2-04 hardening — the choke point's own rules (BUILT, 2026-09-21)

`perform_request` remains the only door to a service (one opener, built once), and it now carries the
rules the Connection framework promised: the redirect chain is bounded (`MAX_REDIRECTS`); a service's
own `Retry-After` on 429/5xx is honoured but capped (`RETRY_AFTER_CAP`); the V2-14 network-rule seam
(`NETWORK_RULES`) is asked about the host **before anything leaves the computer** and again about a
redirect's host, and a rule source that errors fails closed; an answer that hits the reading cap is
labelled in the note; and a refusal from the choke point reaches the person as its own sentence
(`test()`/`run()` re-raise `PolicyError`). No rules are configured yet — behaviour is unchanged
except where a service (or a stand-in) asks for otherwise. D-36.

## V2-09 — routing intelligence (BUILT, 2026-09-21)

The routing path already existed (`routing_outcomes`, `router.select`, `model_prefs`, the provider
state row, the `run.claimed` route the state surface reads); V2-09 makes it *intelligent and
answerable* without adding a second system. `kel/routing_evidence.py` owns the evidence store: one
fact row per run (verdict, task kind, attempts, escalation, model, observed span, source, reviewer
provenance), decayed at a seven-day half-life inside a thirty-day window, with **no rate reported**
until ~three fresh runs’ worth of weight exists — so small samples never move the defaults. A reviewed
verdict refines an inferred failure, never the reverse. `router.select` takes that evidence as data
and may **demote** a recently-failing eligible model — never removing it, never touching an explicit
choice or a preference — then returns the decision with its own explanation (`why`, `chain`,
`demoted`, `evidence`, `excluded`; policy `eligible-cost-v2`). `/api/model` gained `action: 'why'`,
which reads the stored route back and answers in one plain sentence; `state()` already publishes the
same route per active run. The measured phone gap is closed: `needs_work()` in `kel/router.py` keeps a
command-shaped or connected-service request out of the conversational branch, so it becomes a real
work turn. Live probe on this code: the measured phone turn created a real job (`codex`, chain
`[codex, claude]`), “Why this model?” answered plainly, and the chat control created no job. D-37,
D-38.

## V2-10 — Learning 2.0 (BUILT, 2026-09-21)

The learning layer already rode the V1.3 memory store (learnings are memory records with the trust
ladder, decay and corrections) and the proposal queue already refused to propose decisions or
preferences. V2-10 adds the person's side, the floor and the fence. **Floor:** `suggest_learnings`
proposes only from measured evidence — ≥3 decided runs (model-by-task, from the V2-09
`routing_outcomes` store), ≥3 repeated user corrections, or ≥3 Connection uses in 30 days — and every
suggestion is a proposal in the existing queue (accept/reject/defer, dedupe-by-evidence preserved), so
the learner never applies anything. **Person's side:** a learning switches off without being deleted
(a superseding equal-trust record carries `enabled`; the chain keeps every step), a disabled learning
never reaches model context (`Memory.select`), stays inspectable via `include_disabled`, and comes
back with one call; `/api/memory` gained `learnings` / `learning` (explain) / `disable_learning` /
`enable_learning` / `suggest_learnings`; `explain_learning` reports source, trust, decayed confidence,
evidence, provenance, the full chain, queued promotions and a plain `effect` sentence. **Fence:** any
non-user source whose insight asserts a permission grant, spending authority, filesystem access or
irreversible authority is refused outright — not stored, not even suggested; the person's own
statement passes. Live `/api/memory` loop on this code: empty evidence → 0 suggestions; 3 decided
runs → 1 pending proposal; accept → learning `model.coding.codex`; explain carried the evidence and
the boundary sentence; disable → out of the default list (still inspectable, `enabled=False`); enable
→ back. D-39.

## V2-11 — Long-running work 2.0 (BUILT, 2026-09-21)

The V1.6 liveness truths (no automatic replay of an interrupted attempt; waiting is not completion)
already ruled the floor, but `recover_expired` was reachable only from the CLI — a run killed without
a broker stayed RUNNING forever. V2-11 adds the runtime half and the person's half. **Runtime:**
`Store.recover_abandoned` fences only runs nothing durable can carry — expired lease, no broker row,
not active in this engine — and `Engine.tick` calls it every tick; broker-backed runs are left for
adoption, live leases are left alone, and an unreadable recovery question fences nothing. Fencing is
truth-preserving (ORPHANED + fresh epoch, milestone UNCERTAIN with the reconciliation sentence, job
WAITING_RESOURCE) and never re-arms anything. **Person:** `Continuation.resume_brief` (surfaced in
`_work()['work']`) reports per job what shipped, what is open, why it stopped, the exact next step and
`needs_you` — true only when no automatic step can move it (a routing block clears itself; a fenced
attempt waits for the person's “continue”; a pending approval waits on the request card). Live on the
real data root: 7 broker-backed runs survived startup untouched (`orphaned` total 0) and the Work
brief rendered a settled job in plain words. D-40.

## V2-12 — Adaptive staffing 2.0 (BUILT, 2026-09-21)

The staffing rule table, the D1 delegation path and the D2 pod path already existed (with builder≠
verifier independence, family-diversity preference, frozen contracts, budget reservations and
failure states written on worker failure). V2-12 adds the directive's remaining clause — learn from
outcome history. `staffing.outcome_advice` reads settled missions at the same decided tier and offers
exactly one bounded step: ≥3 with blocker-class findings → one up; ≥3 all clean → one down; mixed or
thin → nothing, with the counts in the reasons. It can never cross R1/R3–R6 floors, `tier_max` or the
caps; `staffing.resolve` applies it within those floors; `delegation.delegate` applies a step down to
solo and records (never smuggles) a step up; `pods.run_d2` applies a step down and then refuses with
its explicit “use run_d1” sentence; every `staffing.decided` event carries the advice beside the
decision. Two acceptance checks closed this turn: _learning removal_ is satisfied by the existing
guarded memory `forget` path (new surface pin), and _unbrokered abrupt-stop recovery_ was proved live
— a 5 s unbrokered lease was fenced by the running engine's own tick (`recovery: runtime`), distinct
from the V2-11 probe where seven broker-backed runs were adopted and never fenced. D-41.

## V2-13 — Local execution isolation (BUILT, 2026-09-21)

The containment Kel already had is real (read-only tool-disabled native argv — codex `-s read-only`
with `sandbox_mode="read-only"` and a long `--disable` list, claude `--safe-mode --tools ''`;
identity-bound process kill with group semantics; coding snapshots into `repositories/<job_id>` with
linked-path refusals; the guarded transactional apply). V2-13 adds the three missing pieces in
`kel/containment.py`, wired where Kel acts autonomously: **sensitive-root refusal**
(`assert_usable_root`: Windows/Program Files, credential folders, Kel's own data root,
`KEL_PROTECTED_PATHS`) at the coding snapshot (every caller and every execute) and before any
application staging; **disposable sessions** (one temp directory per native run, TMP/TEMP/TMPDIR
pointed at it, removed when the transport returns); and the **R7 env rule widened to the shape of the
name** (KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH dropped unless it is the provider's own credential;
`KEL_*` helpers kept). Honest edges: a scrubbed inherit, not an allowlist; sessions for native
children only; a rule at Kel's own seams, explicitly not an OS-level sandbox. D-42.

## V2-14 — Network permissions (BUILT, 2026-09-21)

The `NETWORK_RULES` seam already existed (one hook all outbound paths share; asked before send and
for a redirect's host; fail-closed; `None` = open). V2-14 makes `kel/network_policy` its default
source: modes `none`/`approved`/`full` per scope (`default`, `project:<id>`) plus exact per-tool
rules; with no rows the default stays `full`, so nothing changes until a person chooses. In
`approved`, an unlisted host is never sent — one pending request is recorded and the refusal names
the fix; `resolve_request` approves (adds the host to that scope's list) or denies; every decision is
recorded in `network_events` (`allowed`/`blocked`/`ask`) beside the performed calls in
`connection_events`. The tool and project travel with the call (`perform_request(context=…)`),
the policy binds per store around exactly that call, and **an explicitly configured hook always
wins**. The `/api/connections {action:'network'}` surface carries get/set_mode/set_tool/clear_tool/
requests/resolve/history. Live: mode none refused with “You set Kel to no internet for default, so
nothing is sent.”; approved refused an unlisted host with the ask sentence and one pending request;
history showed `[ask, blocked]`; mode restored to full. D-43.

## V2-17 — Manual upgrade reliability / migration validation (BUILT, 2026-09-21)

§22 done practically. What already existed and was reused: the identity-proofed 0.2.1→V2 legacy
migration (idle-checked, backed up first), the hot-copy backup that **never** carries provider
credentials (`kel-credentials.json` in `NEVER_BACKUP`; secret rows stripped from the copy), the staged
restore with its marker + `restart_required`, `apply_pending_restore` at engine start (merge, never
delete; `…pre-restore-<timestamp>` rollback copy; databases written through SQLite), and the v13→v14 /
v15 / ledger suites. V2-17 adds the missing **proof and tooling**: `backup.table_inventory` (every
table with counts + the migration ledger) surfaced as `/api/backup {action:'inventory'}` — the manual
upgrade's before/after — and a richer backup summary (connections, memories, projects, jobs). Pins:
the inventory covers the V2 tables; a backup carries every V2 row and never the credentials file; a
restore brings every table and the ledger back **exactly** and drops post-backup mutations; a staged
restore touches nothing live until applied and the second apply is a no-op; the live credentials file
survives the restore; and re-opening with every V2 module ensuring its schema changes no count and no
ledger row. Live on the real V2 root: 107 tables, ledger = 24 migrations, and the backup copy's V2
counts matched the live inventory exactly. No updater infrastructure (by directive). D-45.

## Kibble Build Update — the backend contract (BUILT, 2026-09-21)

Definition first (D-46): Kibble is the user-facing name for Fix Capture / Dogfood behavior; the
workflow is capture → select findings → Build Update → isolated development mission → a coding runtime
repairs Kel's source → bounded tests/verification → a separate candidate build → Nick reviews;
promotion/installation needs explicit human approval. `kel/build_update.py` (migration 29
`v21-build-update`) implements the contract on the existing machinery: `start()` records the selected
findings with their screenshot/route/transcript/version context, verifies the repository identity and
a clean baseline (refusing otherwise), and creates an ordinary `compile_coding` job the engine claims
and dispatches into the existing isolated `repositories/<job_id>` copy; `candidate()` reports
`BUILDING` before settle, then assembles a SEPARATE candidate under `candidates/<id>/` (revision,
verbatim bounded test evidence with a `verified` flag, fixed and unresolved findings as candidate
claims only, limitations, a `build-report.json`, an explicit review state); `review()` moves
READY_FOR_REVIEW to APPROVED/REJECTED only for the person; `promote()` always refuses — installation
is not part of Build Update and no code path installs. Surface:
`/api/dogfood {action:'build_update', op:…}`. The future UI contract is in
`PARALLEL_SHELL_TOUCHES.md`. Live on the real engine: a mission was created (baseline = pushed HEAD),
the BUILDING gate held, `promote` refused, the job cancelled cleanly, and the source checkout stayed
byte-clean throughout.

## Kibble Build Update — the verification gate tightened (V2-18 acceptance, 2026-09-22)

The acceptance journeys found that a candidate could claim a verified build from a **single run's**
evidence while the mission's own outcome was `CLOSED`/`FAILED` — the fourth attempt had "passed" only
because the runtime monkeypatched `sys.exit`, and the reviewer's finding said so. `_assemble` now
requires the job's `verdict == 'VERIFIED'` **and** the milestone `ACCEPTED` before any verified claim;
the run's evidence is still recorded verbatim (`mission_verdict` names what the job said), no finding is
claimed repaired otherwise, and `promote` keeps refusing in every state (D-49). Two smaller honesty
fixes came with it: a non-repository source is refused with Kel's own sentence instead of a leaked `git`
message, and the candidate's evidence note describes the mission it belongs to. Measured end to end: a
real codex-code dispatch repaired the fixture inside the isolated `repositories/<job_id>` copy, the
bounded tests ran green, the candidate carried the workspace revision with the baseline as an ancestor,
a human review moved it to APPROVED, and the source checkout stayed clean throughout.
