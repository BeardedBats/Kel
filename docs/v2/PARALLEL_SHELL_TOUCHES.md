# Parallel shell touches — what the Shell (ux/v2-shell) needs from the backend

Backend changes that will eventually receive renderer work are recorded here instead of editing
renderer files. Owners: backend = this run (`dev/v2`); Shell = Astra (`ux/v2-shell`). Nothing here
asks the Shell to change today; each item is a contract the backend already ships.

## V2-04a — the Connections capability (2026-09-21, `dev/v2` @ `621d337`)

The engine now reports a fifth capability row in every capability surface (`/api/capabilities`,
snapshot / listing / directives), and it is honoured by a real production path (the assistant bridge
in `runtime/kel/connection_tools.py`):

- id `connections`, label "Connections", description "Use the services you connected".
- Availability is honest: `needs_setup` ("Add a service in Connections first.") until at least one
  connection has a stored credential; then `available` ("Kel can use your connected services").
- Chat directives work with the same grammar as the others: `connections: off`,
  `connected services: off`, and the clause form `[kel:connections=off]`.
- Mutating Connection actions surface as ordinary chat approvals: an `approvals` row of kind `action`
  with a `connection` shaped action, resolvable through the existing `/api/approval` route. The card
  sentence comes from `chat_approvals.plain_summary` → `use "<action>" on <service>`. No new card type.
- Access history gains a `source` fact per call: `shell` (a click in the app) or `runtime` (the
  assistant). `/api/connections {action:'events'}` returns it.

No renderer change is required for any of the above — this note exists so the Shell work can reflect
the capability and the source fact deliberately when it lands.

## V2-04b — the account sign-in (2026-09-21, `dev/v2` @ the V2-04b commit)

- Connection rows now carry the sign-in state in plain words: `auth_state` (`''` | `pending` |
  `connected` | `disconnected` | `needs_reconnect`), `auth_scopes` (what the provider granted),
  `auth_expires`, `oauth_provider`. Never a token, and never mandatory for other kinds.
- The desktop shell owns the sign-in end to end: `kel:connection-oauth-connect` (opens the system
  browser, waits boundedly, claims the finished authorization into the OS-backed custody, pushes it
  to the engine) and `kel:connection-oauth-revoke`, both exposed as
  `window.kelAPI.credentials.oauthConnect / oauthRevoke` and both refusing spoofed senders. The
  Connections page shows a plain-words status line and one Connect / Reconnect / Sign out button for
  `kind: 'oauth'` connections — no visual redesign; keep those two strings if the page is redrawn.
- The engine serves exactly one public route, `/oauth/callback`; a sign-in started on a remote
  surface (the phone) finishes only where the engine's own loopback is reachable. The Shell work may
  decide later whether the phone should start sign-ins; no renderer change is needed for that today.

## Kibble Build Update — the future UI contract (2026-09-21, `dev/v2` @ the Build Update commit)

Kibble is the user-facing name for Fix Capture / Dogfood; the backend contract is BUILT (D-46).
Nothing here asks the Shell to change today — it is the contract a Build Update surface will read and
write when the Ramble/Kibble presentation lands.

- **Findings** come from the existing dogfood surface unchanged (`/api/dogfood` list/get/save/
  set_status; statuses OPEN / BATCHED / FIXED / DISMISSED). Selection is simply a list of fix ids.
- **One action family, five ops** — `/api/dogfood {action:'build_update', op:…}`:
  - `start` — `{findings:[ids], source_root, tests:[argv], scope?, conversation?, project_id?}`.
    Refusals arrive as ordinary plain sentences (non-repo source, dirty baseline, closed finding,
    sensitive root). Success returns `{mission, job, contract}`.
  - `status` — `{mission}` → the mission record (findings' context incl. route/version/has_screenshot,
    source_root, baseline_revision, scope, stage) + `{job:{state, verdict, milestones}}` +
    `{candidate}` when one exists. A pure read.
  - `candidate` — `{mission}` → `{state:'BUILDING'}` before the mission settles (nothing is created),
    then `{state:'READY_FOR_REVIEW'|'APPROVED'|'REJECTED', candidate:{…}}`.
  - `review` — `{candidate, decision:'approve'|'reject', note?}`; the state only moves for the person.
  - `promote` — **always refuses** in plain words; a surface should never present it as an action.
- **A candidate carries**: revision, `artifact_location` (under the engine data root's
  `candidates/<id>/` — never the source checkout, never an installation), verbatim bounded test/
  verification evidence with a `verified` flag, fixed and unresolved findings (candidate claims only —
  Fix Capture statuses are untouched), limitations, and the review state. A `build-report.json` sits
  in that folder for a file-level review.
- **Copy discipline for the surface**: “Build Update” creates and verifies a candidate; it never
  installs and never changes the running app. Installation/promotion is a separate future step behind
  an explicit human decision and is not part of this contract.
