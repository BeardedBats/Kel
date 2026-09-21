# KEL V2.0 — MARATHON STATE

Machine-readable-ish program state. A resume run reads `MARATHON_DIRECTIVE.md` → this file → `RESUME.md`
and then continues the exact `current_item`. Update this file whenever a phase starts or closes.

```yaml
program: kel-v2.0
line: v2                    # development line created by this setup commit
branch: dev/v2
base_commit: a471e17ac25590369e74824ebed0dd7b54e4b00b   # V2.0 base (dev/daily-driver head at setup)
setup_commit: <filled by the setup commit>
remote: https://github.com/BeardedBats/Kel
phase: V2-00                # completed by the setup commit (durable state + developer line)
next_item: V2-01            # Connections model + central management (see ROADMAP.md)
status: ready-to-start

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
  V2-01: queued      # Connections model + central management
  V2-02: queued      # Generic REST Connection
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

## Model preferences recorded at setup

- Nick works from the iPhone for chat, voice, status, approvals, Project routing and stop/resume (§5 of
  the directive); the desktop may remain on.
- Real dogfood feedback from the stable candidate outranks synthetic tests and can change priorities;
  every priority change is recorded in `DOGFOOD_FINDINGS.md`.
