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
phase: V2-02                # Test Connection through the single choke point
next_item: V2-03            # personal Connections (see ROADMAP.md)
status: phase-complete

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
  V2-03: queued      # personal Connections (Pitcher List, Stripe, Raptive, Google Drive, GitHub, ClickUp, Figma, Discord)
  V2-04: queued      # Connection Framework + templates/docs/testing
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

## Model preferences recorded at setup

- Nick works from the iPhone for chat, voice, status, approvals, Project routing and stop/resume (§5 of
  the directive); the desktop may remain on.
- Real dogfood feedback from the stable candidate outranks synthetic tests and can change priorities;
  every priority change is recorded in `DOGFOOD_FINDINGS.md`.
