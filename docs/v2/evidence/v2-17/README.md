# V2-17 — Manual upgrade reliability / migration validation (2026-09-21)

Increment: §22 done practically — **no updater infrastructure**, but a safe manual upgrade, safe
migrations, failure without data loss and a practical developer rollback. Measured first; the missing
piece was the proof that the **new V2 state** survives.

## What was already true (measured, not assumed)

- **The legacy migration** (`kel/migration.py`): a known 0.2.1 engine is migrated only when idle
  (no active/unresolved runs, no PLANNING submissions, no unobserved effects, every job settled),
  with process-identity proof before anything is terminated, and a consistent backup written to
  `migration-backups/` first.
- **The backup machinery** (`kel/backup.py`): `create` hot-copies the database safely under a live
  engine, writes a readable description (`Kel-Backup-<timestamp>/…`), **excludes provider credentials
  and the transcription key** (`kel-credentials.json` in `NEVER_BACKUP`; secret rows stripped from the
  copied database), and reports what it could not read instead of failing silently.
- **The restore path**: `stage_restore` copies into a staging folder + writes a marker and reports
  `restart_required`; `apply_pending_restore` runs at engine start, merges instead of deleting, keeps
  a `…pre-restore-<timestamp>` rollback copy beside the data root, and writes the database through
  SQLite; snapshots are pruned to a keep-count.
- **Upgrade suites** already existed for the v13→v14 and v15 slices and the migration ledger
  (`test_v14_upgrade`, `test_v15_upgrade`, `test_v16_r8_migrations`, `test_migration`).

**The measured gap:** nothing proved the *V2* state (migrations 23–28 plus V2-09…V2-14 inline tables)
survives a backup→restore cycle or an additive re-open, and there was no before/after inventory tool.

## What this increment added

| Piece | Where | What it does now |
|---|---|---|
| Inventory | `backup.table_inventory(db_path)` + `/api/backup {action:'inventory'}` | Every real table with its row count plus the migration ledger — the manual-upgrade before/after, read-only |
| Richer backup summary | `backup._summary` | The backup description now also counts `connections`, `memories`, `projects`, `jobs` (the V2 surfaces a person would miss) |

## Verification (on the final code of this increment)

- `tests/test_v2_upgrade.py` (new, 6 tests) — the inventory covers the V2 tables (`connections`,
  `oauth_flows`, `connection_events`, `routing_outcomes`, `model_prefs`, `network_policy`,
  `network_events`, `memories`, `memory_proposals`, `team_events`, `projects`, `conversations`,
  `schema_migrations`) with counts and a readable ledger; a backup carries every V2 row and **never**
  the credentials file; a restore brings **every table and the ledger back exactly** and drops
  post-backup mutations; a staged restore touches nothing live until applied and the second apply is
  a no-op; the live credentials file survives the restore (merge never deletes); and re-opening the
  same store with every V2 module ensuring its schema again changes **no count and no ledger row**.
- Bounded group on the final code: `test_v2_upgrade test_v14_upgrade test_v15_upgrade
  test_v16_r8_migrations test_migration` → **18 OK** (7.5 s).
- Live demonstration (engine restarted on `C:\Users\Nick\KelV2Runs\prepared\engine`, driven through
  `/api/backup`): `inventory → 107 tables, ledger = 24 migrations`; the V2 spread on the real
  accumulated root `{connections: 3, connection_events: 1, network_policy: 1, network_events: 2,
  routing_outcomes: 3, memories: 3, memory_proposals: 1, team_events: 3, oauth_flows: 1}`; `create`
  produced the description with the V2 counts (`connections 3, conversations 12, jobs 3, memories 3,
  messages 26, projects 2`); `inspect` matched it; the copied database’s counts matched the live
  inventory **exactly**; the probe backup folder was removed and the engine stopped by its own pid.

## Honest limits (also in `KNOWN_LIMITATIONS.md`)

- **The inventory counts tables, not content**: an equal inventory proves no row was lost, not that
  every row is semantically intact (the V2 suites cover semantics).
- **The restore is whole-database**: it replaces the database file (through SQLite) rather than merging
  rows; the pre-restore rollback copy is the recovery for a wrong restore.
- **Credentials are excluded by design**: after restoring onto a machine, provider keys must be
  reconnected (the backup says so in its notes) — a restore never resurrects secrets.
- **No updater infrastructure** (by directive): upgrades are manual — stop, back up, replace the app,
  start; the inventory is the check before and after.
