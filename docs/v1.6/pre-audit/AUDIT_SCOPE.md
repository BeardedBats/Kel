# AUDIT_SCOPE — the declared V1.6 audit surface

updated: 2026-09-18T16:05Z (Campaign A open; refined continuously through the sprint, frozen at PRE-AUDIT RC)

Every item below must receive one Campaign B disposition:
`PASS` / `FAIL` / `PARTIAL` / `NOT_APPLICABLE` / `NOT_TESTABLE` / `DEFERRED_WITH_RATIONALE`.
No scope item may silently disappear. "Prior coverage" notes what the historic audits (increments
1–24, `5e76b21..8a2b25d`) already dispositioned — Campaign B may still re-challenge it, but should
not re-litigate without reason.

Legend for audit status now: **PENDING** (Campaign B) for everything; notes carry context.

## 1. Desktop shell

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| DS-01 | Shell startup / boot dialogs | app boots, dialogs truthful, engine handshake | KelService.ts; boot logs; packaged probes | prior: partial (packaged sweeps); PENDING |
| DS-02 | Single-instance / window lifecycle | one instance, close/quit safe, no orphan engine | KelService.ts; packaged probe a | PENDING |
| DS-03 | Update behavior | update paths never fake success; release links | boot-dialog/update links (Phase 4); GITHUB_SYNC_POLICY | PENDING |
| DS-04 | Source identity / version identity | app+engine version strings truthful (1.5.0→1.6 target) | package.json; ENGINE_VERSION; release gates | version bump is an RC task — verify at RC |
| DS-05 | Theme system | theme toggle, overrides deletion (`THM-01` open) | applyTheme.ts; packaged probe a | PENDING |
| DS-06 | i18n (13 locales) | no donor strings; fallback behavior; key parity | docs/i18n-cleanup/00_STATUS.md; audit increment 6 | prior: audited (CONTINUE); PENDING re-check at RC |
| DS-07 | Error translation | infra errors → human copy; no raw errors (`ERR-01`, engine-loss class) | renderer error surfaces; visual finding 16/17 | PENDING; engine-loss is a campaign item |

## 2. Engine core

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| EN-01 | Store / jobs / runs / effects core | durable semantics; state machines | runtime/kel/core.py; existing suites | prior: audited historically; PENDING |
| EN-02 | Guardrails / tamper check | `guardrails_ok` truthful; tamper detected | engine.py; tests | PENDING |
| EN-03 | Engine lifecycle: startup / shutdown / restart | clean start; clean stop; restart; no stuck locks | service.py; instance_lock.py; diagnostics; packaged probes | PENDING |
| EN-04 | Post-launch engine loss | user-facing failure/recovery, no raw errors; **Phase 43 sprint item** | KelService.ts; renderer surfaces; visual batch 6 | OPEN finding (visual 16/17); campaign item |
| EN-05 | IPC bridge | whitelist accuracy; sender-frame validation (`INT-01` open) | KelService.ts frame checks; audit regex checks | PENDING |
| EN-06 | Leases | acquire/release exactly once on every path (INV-LEASE-001) | runtime/kel/parallel.py; lease tests | prior: Phase 5.5 audited; PENDING |
| EN-07 | Approvals | announce/resolve semantics; no bypass (`APR-01..06`) | chat_approvals.py, autonomy.py; docs/in-chat-approvals | PENDING |
| EN-08 | Authorization / grants | policy gate; resume-after-grant; spend at effect | authorize.py; tests | prior: audited; PENDING |
| EN-09 | Capabilities (web/files/terminal/github) | reserved grammar, fail-closed, conversation scoping | capabilities.py, research.py, acp_host.py; test_capabilities | prior: audited (CAP arcs); PENDING |
| EN-10 | Continuation / resume | resume truthfulness; replay safety | continuation.py | PENDING |
| EN-11 | Backup / restore | failure visibility (`PER-02`), snapshot retention (`PER-03`), `KEL_DATA_DIR` (`PER-04`) | backup.py; service.py restore call | PENDING |
| EN-12 | Diagnostics | records truthful; startup/shutdown markers | diagnostics.py | PENDING |
| EN-13 | Search | error handling (`COR-05`); result quality | search.py | PENDING |
| EN-14 | Vetting sessions | ownership scoping (`SEC-01`); dispatch errors (`COR-06`) | vetting_session.py; vetting_bank.py | PENDING |
| EN-15 | Transcription (engine) | `_STREAMS` lifecycle (`TR-01`); multipart filename (`SEC-01-multipart`) | transcription.py | PENDING |
| EN-16 | Model routing / runtime routing | AUTO/PREFERRED/FIXED no silent substitution; fallback recorded | router.py, assignment.py; routing tests | prior: Phase 5.1; PENDING |
| EN-17 | Providers | claude-code / codex / anthropic / deepseek definitions, state probing, key handling | providers.py; Phase 10 matrix | PENDING; real-credential validation = Phase 10 |
| EN-18 | Process runner / durable adapter | process identity, termination safety | runner.py, windows_job.py | PENDING |
| EN-19 | Native adapters (claude/codex CLIs) | bridge correctness, no donor leftovers | native.py, native_claude.mjs | PENDING |
| EN-20 | Engine version identity | packaged engine == fresh build hash; ENGINE_VERSION | service.py; PackageIndex | PENDING; re-prove at RC |

## 3. Persistence / migrations

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| DB-01 | SQLite schema & migrations 1..19 | chain correct, no dup/missing, idempotent | MIGRATION_LEDGER.md; migration modules | PENDING |
| DB-02 | Fresh DB init vs upgrade | fresh install succeeds; supported upgrade succeeds | fresh/upgrade tests (`test_v13_memory`, `test_v14_upgrade`, per-module) | PENDING; packaged assertions 16–19 open |
| DB-03 | Append-only ledgers | triggers hold; no mutation path bypasses | workforce.py triggers; tests | prior: Phase 5.0 audited |
| DB-04 | Memory store | isolation, provenance, trust ladder, decay, forget | memory.py; test_v13_memory; docs/v1.3 KEL_V1.3_MEMORY_MODEL | Phase 6 audit = campaign item |
| DB-05 | Memory proposals | review surface, dedupe keys, states | memory.py; test_v16_proposals; docs/memory-proposals | prior: Phase 1; PENDING |
| DB-06 | Artifact lineage | every generated artifact says where it came from | runtime/kel/lineage (core schema); docs/artifact-lineage | prior: Phase 2; PENDING |
| DB-07 | Conversation / project isolation | no cross-project/conv leakage (INV-MEM-001) | memory.py, model_prefs, capabilities scoping | PENDING — see AUDIT_TARGETS |
| DB-08 | Workforce tables 16–19 | schemas, links, budgets, parallel tables | MIGRATION_LEDGER.md | PENDING |

## 4. Workforce OS

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| WF-01 | Role registry / skill registry / contracts / completion packets | v1 validators, ceilings, append-only | workforce.py, contracts.py; phase records 5.0 | prior: audited |
| WF-02 | Agent-to-model assignment | modes, requirement profiles, fail-closed grants, reservations | assignment.py; 5.1 record | prior: audited |
| WF-03 | Staffing decision + D0–D4 | bands, floors, tier_max; commander never spawned | staffing.py, delegation.py; 5.2 record | prior: audited |
| WF-04 | D1 delegation | contract issuance, evidence-bound close, no nesting | delegation.py; 5.2 record | prior: audited |
| WF-05 | D2 pods | Builder ≠ Verifier, family diversity, verdict consistency | pods.py; 5.3 record | prior: audited |
| WF-06 | D3 parallel missions | disjoint-write streams, leases, integration, ignored paths (`F20-6`) | parallel.py; 5.5 record | prior: audited (limitations carried) |
| WF-07 | Assurance / Sentinel / Oracle | scope gating, anti-anchored dispatch, never-gate, waive rules | assurance.py; 5.4 record | prior: audited |
| WF-08 | Findings / evidence | ledger integrity, staleness rejection, close refusals | workforce.py, evidence.py | prior: audited |
| WF-09 | Learning loop (shadow) | learning-as-memory, caps, promotion queue, zero auto-apply | learning.py; 5.6 record | prior: audited (24-N1..N3 informational) |
| WF-10 | Adaptive staffing disposition | stays deferred (5.7) | 5.7_DECISION_DEFERRED.md | DEFERRED_WITH_RATIONALE expected |
| WF-11 | Advanced Worker View disposition | product decision (Phases 5.8/8) | 5.8_DECISION_DEFERRED.md | decision recorded in campaign; then disposition |
| WF-12 | Real-artifact binding (`F4`) | evidence binds to real delivered artifacts | campaign wiring item | OPEN carry-forward; campaign item |
| WF-13 | Evidence-bound review rows + resolution-kind (`F17-4`/`F18-5`) | close semantics complete | campaign wiring item | OPEN carry-forward; campaign item |

## 5. Memory (Phase 6 surface)

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| MEM-01 | Reachable controls | every control reachable; no no-op surfaces | campaign Phase 6 record | campaign item |
| MEM-02 | Persistence | memories survive restart; edits durable | Phase 6 record; probes | campaign item |
| MEM-03 | Conversation isolation | cross-conversation reads/writes impossible | memory.py scoping; tests | campaign item |
| MEM-04 | Project isolation | cross-project reads/writes impossible | memory.py `_require_project`; tests | campaign item |
| MEM-05 | Source / provenance | trust ladder honest; user-stated vs inferred | memory.py; learning.py SOURCE_TRUST | campaign item |
| MEM-06 | Edits / corrections | correct/confirm/retract paths truthful | memory.py; tests | campaign item |
| MEM-07 | Forget / delete semantics | tombstone + audit; retrieval stops | memory.py forget; tests | campaign item |
| MEM-08 | Stale memory | decay at read time; nothing silently gates | learning.py decay; test_workforce_learning | campaign item |
| MEM-09 | Backend/UI match | UI shows what backend holds; no hidden mutation | Phase 6 record | campaign item |

## 6. UX surfaces

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| UX-01 | Composer / Model/Tools controls | controls truthful; per-conversation scoping | KelModelControl.tsx; `COR-03`; visual batch 7 | PENDING; batch 7 is a campaign item |
| UX-02 | Sidebar | rows, actions, marks (batch 5 done) | visual evidence index | PENDING (human gate) |
| UX-03 | Team / Office | terminology, APIs, read-mostly | Team surfaces; `active_owned_files` protocol | PENDING |
| UX-04 | Work panel | progress surfaces truthful | KelWorkPanel.tsx | PENDING |
| UX-05 | Projects / Permissions / Profiles vs Projects | semantics decision ships (Phase 9) | campaign Phase 9 record | campaign item |
| UX-06 | Settings | shell routing (batch 2 done); settings half of batch 8 held | visual evidence index | PENDING |
| UX-07 | Transcription UI | standalone IA (batch 4 done); abandoned-stream UX (`TR-02`) | visual evidence index; audit records | PENDING |
| UX-08 | Memory UX | proposals surface (Phase 1) + Phase 6 findings | docs/memory-proposals; Phase 6 record | campaign item |
| UX-09 | Command palette | truthful actions; no dead entries | KelCommandPalette.tsx | PENDING |
| UX-10 | Approvals UI | in-chat approvals journey verified | docs/in-chat-approvals; packaged journey | prior: Phase 3; PENDING |
| UX-11 | Lineage UI | versions view truthful | packaged lineage probe | prior: Phase 2; PENDING |

## 7. Security / privacy

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| SP-01 | Secret scanning | writer-side scans; no secrets in evidence | memory.scan_secret; evidence indexes | PENDING |
| SP-02 | Credential storage | keys not leaked to backups/evidence; `PER-04` | backup.py; kelCredentials.ts | PENDING |
| SP-03 | Capability token grammar | prose never mutates; reserved namespace only | test_capabilities corpora; CAP arcs | prior: audited; re-attack in Campaign B |
| SP-04 | IPC sender-frame validation | all channels checked (`INT-01`) | KelService.ts | PENDING |
| SP-05 | Approval payload actor checks | `APR-01..03` class | chat_approvals.py, service.py | PENDING |
| SP-06 | Ownership scoping by bare id | `SEC-01`/`APR-02` shared root cause | vetting_session.py, approval resolvers | PENDING — systemic pattern, audit first |
| SP-07 | Public repository safety | scan gate on every publication | GITHUB_SYNC_POLICY; sync-recon records | PENDING |
| SP-08 | Privacy constraints on providers | local-only hints, data boundaries | router.py, providers.py | PENDING |

## 8. Failure states / data integrity

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| FI-01 | No false success | closes/approvals/restores never claim success falsely | close_d1 refuses; restore truth (`PER-02`) | PENDING |
| FI-02 | Cleanup vs primary error | cleanup failure never masks primary error (INV-ERROR-001) | backup/restore; guardrails | PENDING |
| FI-03 | Degraded states | engine loss, provider loss, quota states surface honestly | error surfaces; Phase 10 | PENDING |
| FI-04 | Dispatch errors | no KeyError leaks (`ERR-01`/`COR-06`) | service.py dispatch | PENDING |
| FI-05 | Stall/interruption accounting | pods/parallel honest accounting | pods.py; 5.3 record | prior: audited |

## 9. Packaging / runtime identity

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| PK-01 | Packaged app boots with intended engine | engine hash == fresh build (INV-PACKAGE-001) | PACKAGED_EVIDENCE_INDEX.md | PENDING |
| PK-02 | Migrations on packaged boot | schema_migrations 16–19 asserted | packaged battery (carry-forward) | OPEN assertion |
| PK-03 | Routes / journeys in packaged app | sessiontools/approvals/lineage/memoryprops sweeps | PACKAGED_EVIDENCE_INDEX.md | PENDING |
| PK-04 | Update behavior packaged | update paths, honest failures | boot logs; DS-03 | PENDING |
| PK-05 | Freeze tooling | `REL-01` no-op staging understood/fixed; manifest hashes | scripts/freeze-release.ps1 | PENDING |
| PK-06 | Frozen releases | byte-identical (INV-FREEZE-001) | freeze verification scripts | PENDING; verify at RC |

## 10. Release / process

| # | Item | What to verify | Evidence sources | Notes |
|---|---|---|---|---|
| RL-01 | Git safety | clean tree, intended branch, no rewrite | GITHUB_SYNC_POLICY.md | PENDING |
| RL-02 | Remote sync | publication records match ls-remote | sync-recon records | PENDING |
| RL-03 | This corpus | claims match reality; evidence paths resolve | this directory | PENDING |
| RL-04 | PRE-AUDIT RC record | `docs/v1.6/PRE_AUDIT_RELEASE_CANDIDATE.md` complete | to be created | PENDING |

## PRE-AUDIT RC update (2026-09-19)

R9–R12 deltas included in scope: the visual lane (batches 1–8 + R9.D Needs Your Attention) as
integrated at `7267630`; engine-link supervision + failure-state translation (`engineFailure.ts`,
`engineHealth.ts`, `KelService.ts`); the packaged RC (`package-r12`). New audit targets 84–90 cover
the attention surface, supervision honesty, failure-card containment, the loaded-gun close, donor
preview residue, and packaging input hygiene. Everything else in this scope is unchanged.
