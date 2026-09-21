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

Connections (Generic REST, personal services, framework), iPhone PWA V1, Needs Your
Attention 2.0, Recipes 2.0, Activity 2.0, routing intelligence, Learning 2.0, long-running work 2.0,
adaptive staffing 2.0, local execution isolation, network permissions, performance polish, manual
upgrade reliability, V2 acceptance and regression.

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
