# KEL V1.4 — ARCHITECTURE

Status: v1 (2026-09-15) · Gate 2 design document. Grounded in the current source: `runtime/kel/*`
(durable work engine), `desktop/` (AionUI shell fork), `packaging/` (release tooling).

## 1. Current architecture (verified)

- **Kel Runtime** (`runtime/kel`, packaged as `KelEngine.exe`): durable work engine. SQLite store with
  ~45 tables created across `core.py` (jobs, contracts, runs, inbox, approvals, approval_actions,
  effects, assessments, publications, messages, providers, controller, job_intakes, routing_outcomes),
  `memory.py` (memories, memory_conflicts, memory_events, FTS, schema_migrations), `context.py`
  (projects, conversations, attachments, grants, handoffs), `projectmap.py` (project_maps),
  `recipes.py` (recipes), `coding*.py` (code_workspaces, coding_hosts, coding_phases, coding_calls,
  code_evidence, change_applications), `research.py` (research_evidence), plus brokers/isolated_runs/
  native_processes/native_progress/project_tests/context_packets/job_links.
- **Loopback API** (`service.py`): bearer-token HTTP (`/api/state|work|send|memory|map|recipes|
  control|approval|apply|retry|artifact|project|conversation|attach|revoke|shutdown-idle`).
- **Shell** (AionUI Electron fork): main process bridges via `process/services/kel/KelService.ts`
  (IPC handlers `kel:conversation|history-search|history|request`, allowlisted engine routes) and the
  donor `core()` agent/conversation API; renderer components incl. `chat/KelWorkPanel.tsx`.
- **Providers today**: adapter classes in `router.py`/`internal.py`/`native*.py`; state in the
  `providers` table (failures, circuit_until, quota/quota_reset/quota_source, quality samples,
  planType) refreshed by `telemetry.refresh_codex`; reviewer provenance captured by
  `core.record_review(reviewer_provider, reviewer_model, ...)`.
- **Migrations**: `migration.py` upgrades only a *known idle legacy* DB (`LEGACY_HASHES` gate,
  `require_idle` checks, backup + integrity receipt); V1.3 added steps 001–004 in the same discipline.

## 2. What V1.4 adds (all additive)

- **Team**: `role_templates`, `role_versions` (append-only; tool policy / model preference / budget
  are fields on the version), `role_overrides` (project|task scope),
  `team_assignments` (links `job_id`/`milestone_id`/`run_id`, provider, model, state, budget,
  blocker, start/end, `role_version_id` snapshot), `team_events`, `assignment_artifacts`.
- **Solution quality**: `solution_briefs`, `solution_options`, `option_comparisons`,
  `capability_opportunities`, `solution_reviews` (chosen option, rejected reasons, evidence-to-switch,
  rollback plan, reviewer disposition).
- **Autonomy**: `capability_leases`, `lease_scope` (kind/value rows — root, repo, domain, tool,
  external), `lease_events`, `boundary_expansion_requests`. `guardrail_decisions` is **not yet a
  table** (V1.5; decisions are recorded in `lease_events`).
- **Providers**: keep `providers(id, data)` as the state row (same JSON pattern), add
  `provider_definitions` (class: native-cli | api; auth mode; capability matrix) and
  `provider_usage` (append-only observations), with credential *metadata only* (`credential_ref`).
- **Diagnostics**: `startup_spans`, `health_observations`, `process_observations`,
  `performance_measurements`, `retention_settings` (provider observations live in
  `provider_usage`, providers migration 007).
- **Activity contract**: one append-only stream `team_events(id, at, kind, actor, refs_json, detail)`
  for Office timelines and receipts (mirrors the existing events discipline; never raw reasoning).

## 3. Best Solution Gate (architecture decisions)

| # | Decision | Options considered | Rationale |
|---|---|---|---|
| D1 | Where Team/lease/brief data lives | (a) engine tables, (b) shell-side store, (c) mixed | **(a)** single source of truth; assignments must reference real `runs`/`jobs`; offline engine access; existing backup/migration discipline applies |
| D2 | How the shell reaches new features | (a) extend allowlisted `/api/*` + IPC, (b) new sidecar, (c) direct DB access | **(a)** matches `KelService.ts` allowlist pattern; testable over HTTP; keeps the renderer sandboxed |
| D3 | Credential custody | (a) OS-backed store via shell main (DPAPI/Credential Manager), (b) engine file, (c) env files | **(a)** OS-protected, per-user, namespaced `kel:`; engine receives only per-run transient env; never persisted plaintext (see Security model) |
| D4 | Role versioning | (a) mutable role rows, (b) append-only versions + assignment snapshots | **(b)** traceability: an assignment always answers “which instructions governed this run” |
| D5 | Activity events | (a) reuse `events`, (b) dedicated `team_events`, (c) log files | **(b)** separate append-only stream keeps job revision semantics untouched and is a stable UI contract |

## 4. Migration plan

1. New steps **005+** in the existing order, each: additive `CREATE TABLE IF NOT EXISTS`, no column
   drops/renames, wrapped in one transaction, recorded in `schema_migrations`.
2. Backup + integrity receipt before the first V1.4 mutation (same discipline as 001–004); V1.3 data
   must load unchanged (regression: open a copied V1.3 DB, run the suite).
3. The legacy gate in `migration.py` is **not** weakened; older engines ignore new tables (they are
   never required for V1.3 paths).
4. Tests: `runtime/tests/test_migration.py` extended (idempotent re-run, receipt, V1.3 fixture open,
   new tables present, no data loss).

## 5. Implementation phases (mapped to gates)

| Gate | Engine | Shell |
|---|---|---|
| G3 | solution briefs + roles + assignments + team API + tests | — |
| G4 | activity stream + assignment/artifact APIs | Office/Roster/Studio + Work Center |
| G5 | evidence/verification endpoints (existing tables surfaced) | memory/continuation/verification/recipes UX |
| G6 | provider registry, credential metadata, lease engine + policy checker (execution-path enforcement deferred; V1.4.1 adds tamper detection + protected-path denial) | Provider Setup + Autonomy/Permissions UI |
| G7 | readiness/preflight hooks | onboarding, search, palette, settings, tray, a11y |
| G8 | diagnostics tables + sanitized export | Diagnostics UI |
| G9 | — | full-app visual pass (Repair with the design system) |
| G10 | packaging + release | packaged acceptance |

## 6. Component and token architecture

- Tokens: `--kel-*` CSS custom properties in a new `renderer/styles/kel-tokens.css`, mirrored by a TS
  constant module; consumed by `uno.config.ts` mappings and `arco-override.css` (Arco `primary` →
  `--kel-accent`, waiting/danger pairs, control radius, type scale). Light default, dark via
  `themes/` (same tokens swapped). Fonts stay as sealed (Söhne + SF Pro Text, runtime-registered).
- Components: Arco primitives + Kel wrappers (`KelButton`, `KelStatusChip`, `KelCard`, `KelSheet`,
  `KelTable`, `KelEmpty`, `KelMeter`) so a single place enforces the design system; the Work panel is
  restyled through them.

## 7. Packaging strategy (unchanged pipeline, new content)

`scripts/build-runtime.ps1` (PyInstaller, `runtime/KelEngine.spec`) → new modules ride the PYZ;
`scripts/build-desktop.ps1` (bun + electron-vite) → new renderer chunks; `packaging/asar-dedup-pack.js`
+ `asar-inspect.js` keep entry-count/dedup parity and explain deltas; `verify_engine_pyz.py` proves
module-level structural equality; `verify-packaged-smoke/ui.cjs` + `capture-screens.cjs` provide the
packaged evidence for G10. Candidate packages build into isolated folders; the frozen V1.3 package is
never touched.
