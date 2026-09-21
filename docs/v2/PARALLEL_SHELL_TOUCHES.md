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
