# KEL V2.0 — IMPLEMENTATION STATUS

What is actually built, as distinct from what is planned. Updated as phases land.

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

## V2-04 — Connection Framework (PARTIAL)

The standard parts of a Connection, in one place: the three credential templates and the request policy.

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
- **Not built in this phase, and not claimed**: what Kel can *do* with a service (actions/tools) and the
  OAuth account sign-in step. Google Drive stays uncheckable beyond a pasted token because of the second
  one, and no connection can be used for anything but Test connection because of the first.

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
- **Desktop**: a "What Kel can do" card on the Connections page listing each action with a plain "Do it",
  the service's answer shown once where it arrived, and a question first for anything that would change
  something in Nick's account. The new `kel:connection-run` channel runs the shared sender guard and hands
  the engine only the fields the shell holds.
- **Still not built**: no chat tool exposes an action, so the assistant cannot use a connection yet — that
  is the next increment of this phase, and the reason V2-04 still reads PARTIAL.
