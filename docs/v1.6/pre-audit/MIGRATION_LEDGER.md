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
| 16 | — | — | *unused: no module claims version 16 (verified 2026-09-19 against every `MIGRATION_VERSION` constant and packaged DBs; the Phase-5.0 workforce schemas ship under the workforce module stamp below)* | — | — | — | — | — | — |
| 17 | v17-finding-resolution-kind | workforce.py | finding resolution-kind (REQ-RK); also carries the Phase-5.0 workforce schema tables (task_contracts, workforce_messages, findings, evidence_records, skill_packs + append-only triggers) | Phase 5.0 (`9085335`/`cc909b9`) + `7267630` | tables + triggers | test_workforce suite | test_v16_r8_migrations | version check | r10-*/r12-* DBs (stamp 17 present) |
| 18 | v16-workforce-task-link | delegation.py | contract↔milestone link | Phase 5.2 (`894be5b`) | additive unique link | test_workforce_d1 | test_v16_r8_migrations | version check | r10-*/r12-* DBs (stamp 18 present) |
| 19 | v16-workforce-parallel | parallel.py | parallel mission teams | Phase 5.5 (`5f77f42`) | parallel tables | test_workforce_parallel | test_v16_r8_migrations | version check | r10-*/r12-* DBs (stamp 19 present) |
| 20 | chat_approval_announcements | chat_approvals.py | approvals poll marker (APR-05 — the read path performs no DDL once stamped) | `dd34ac2` | marker row (idempotent) | test_v16_sweep_fixes (3) | test_v16_r8_migrations | version check | r10-*/r12-* DBs (stamp 20 present) |
| 21 | v16-budget-reservations | assignment.py | budget_reservations | Phase 5.1 (`9d6ed55`/`5b83f0e`); applied version assigned 21 | budget_reservations | test_workforce_assignment | test_v16_r8_migrations | version check | r10-*/r12-* DBs (max=21) |

Next free version: **22** (max applied = 21; Campaign C reconciliation 2026-09-19 verified every `MIGRATION_VERSION` constant and the packaged DB dumps). (Phase 5.6 deliberately used no new migration; learnings ride the memory store.)

## RC checklist (to assert on the pre-audit package)

- [x] no duplicate versions (query `schema_migrations` for duplicate `version`) — `test_v16_r8_migrations` (A-29)
- [x] no missing versions expected by architecture (1..max; 16 is unclaimed by any module — verified 2026-09-19) — `test_v16_r8_migrations` (A-29)
- [x] full chain succeeds on a fresh profile — `ux-audit/runs/r12-fresh2`
- [x] supported upgrade succeeds on a real prior DB (fixture at migration 14/15, then full chain) — `ux-audit/runs/r12-upgrade`
- [x] `schema_migrations` max == expected on a packaged boot with a fresh data dir — r12-fresh2/r12-upgrade (max 21)
- [x] backup-before-first-mutation behavior verified for migration 15 path — `test_v13_memory` / proposals-backup tests

## Maintenance rules

- A new migration lands only with: version constant + name constant, idempotence, a focused test,
  a ledger row here, and a packaged assertion plan.
- Never renumber; never reuse.

## PRE-AUDIT RC update (2026-09-19)

RC boot evidence: the RC package booted a fresh root (full V1.6 migration chain on first start)
AND a populated 1.6.0 root (no migration drift; conversations preserved) — `ux-audit/runs/r12-fresh2`,
`ux-audit/runs/r12-upgrade`. No new migrations were added after `93b99b5` (max remains **21** plus
the approval marker at 20); the engine suite's fresh/upgrade/interrupted-migration checks run in
`test_v16_r8_migrations.py` (A-29).
