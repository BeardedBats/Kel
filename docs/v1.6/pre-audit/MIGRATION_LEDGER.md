# MIGRATION_LEDGER — schema migrations 1..N

updated: 2026-09-18T16:05Z
rule: no unrecorded schema mutation. Every migration row records schema, idempotence, fresh/upgrade
tests, service wiring and packaged-boot verification.

Wiring: `service.py` startup imports and calls the module `ensure_schema` functions (workforce,
assignment, delegation, parallel at startup; memory/others per module use). All share the
`schema_migrations(version INTEGER PRIMARY KEY, name TEXT, applied REAL, note TEXT)` table and the
standard pattern: version check first → `CREATE IF NOT EXISTS` DDL → `INSERT OR IGNORE`. Existing
databases get one backup before the first mutation of a migration family (e.g. memory proposals
`_backup`); fresh databases skip the backup.

| # | Name | Module | Feature | Commit | Schema | Fresh-DB test | Upgrade test | Idempotence | Packaged boot |
|---|---|---|---|---|---|---|---|---|---|
| 1 | v13-memory | memory.py | memory store + audit events + FTS | v1.3 era | memory tables | test_v13_memory | test_v13_memory upgrade paths | version check | v1.3 packages |
| 2 | v13-projectmap | projectmap.py | project map | v1.3 era | project tables | test_v13_projectmap | test_v14_upgrade | version check | v1.3 |
| 3 | v13-continuation | continuation.py | continuation/resume | v1.3 era | continuation tables | test_v13_continuation | idem | version check | v1.3 |
| 4 | v13-recipes | recipes.py | recipes | v1.3 era | recipes tables | test_v13_recipes | idem | version check | v1.3 |
| 5 | v14-solution | solution.py | solution briefs | v1.4 era | solution_briefs | test_v14_solution | idem | version check | v1.4 |
| 6 | v14-team | team.py | team + events | v1.4 era | team tables | test_v14_team | idem | version check | v1.4 |
| 7 | v14-providers | providers.py | provider registry + credentials | v1.4 era | provider tables | test_v14_providers | idem | version check | v1.4 |
| 8 | v14-autonomy | autonomy.py | autonomy + approvals | v1.4 era | approvals, boundary_expansion_requests | test_v14_autonomy | idem | version check | v1.4 |
| 9 | v14-diagnostics | diagnostics.py | diagnostics | v1.4 era | diagnostics tables | test_v14_diagnostics | idem | version check | v1.4 |
| 10 | v15-authorization | authorize.py | authorization/leases | v1.5 era | authorization tables | test_v15_authorize | idem | version check | v1.5 packages |
| 11 | v15-vetting | vetting.py | vetting bank/sessions | v1.5 era | vetting tables | vetting suite | idem | version check | v1.5 |
| 12 | v15-transcription | transcription.py | transcription | v1.5 era | transcription tables | transcription suite | idem | version check | v1.5 |
| 13 | v15-model-prefs | model_prefs.py | model preferences | v1.5 era | model_prefs tables | model prefs tests | idem | version check | v1.5 |
| 14 | v15-conversation-capabilities | capabilities.py | conversation capability overrides | v1.5 era | capability tables | test_capabilities | idem | version check | v1.5 |
| 15 | v16-memory-proposals | memory.py (`PROPOSALS_VERSION=15`, `ensure_proposals`) | memory proposal surface (Phase 1) | `a8c3511` era (verify) | `memory_proposals` + 2 indexes | test_v16_proposals | test_v13_memory / test_v14_upgrade pins moved to 15 by design | version check; one backup before first proposals mutation of existing data | package-final13 (memoryprops PASS) |
| 16 | v16-workforce-schemas | workforce.py | task_contracts, workforce_messages, findings, evidence_records, skill_packs + append-only triggers | Phase 5.0 (`9085335`/`cc909b9`) | 5 tables + triggers | test_workforce suite | planned | version check | **assertion pending** |
| 17 | v16-budget-reservations | assignment.py | budget_reservations | Phase 5.1 (`9d6ed55`/`5b83f0e`) | budget_reservations | test_workforce_assignment | planned | version check | **assertion pending** |
| 18 | v16-workforce-task-link | delegation.py | contract↔milestone link | Phase 5.2 (`894be5b`) | additive unique link | test_workforce_d1 | planned | version check | **assertion pending** |
| 19 | v16-workforce-parallel | parallel.py | parallel mission teams | Phase 5.5 (`5f77f42`) | parallel tables | test_workforce_parallel | planned | version check | **assertion pending** |

Next free version: **20**. (Phase 5.6 deliberately used no new migration; learnings ride the
memory store.)

## RC checklist (to assert on the pre-audit package)

- [ ] no duplicate versions (query `schema_migrations` for duplicate `version`)
- [ ] no missing versions expected by architecture (1..max contiguous)
- [ ] full chain succeeds on a fresh profile
- [ ] supported upgrade succeeds on a real prior DB (fixture at migration 14/15, then full chain)
- [ ] `schema_migrations` max == expected on a packaged boot with a fresh data dir
- [ ] backup-before-first-mutation behavior verified for migration 15 path

## Maintenance rules

- A new migration lands only with: version constant + name constant, idempotence, a focused test,
  a ledger row here, and a packaged assertion plan.
- Never renumber; never reuse.
