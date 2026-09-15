# KEL V1.3 — STATUS

Date: 2026-09-15. Owner: Kel V1.3 autonomous execution session.
Gate 1 and the repository consolidation were approved 2026-09-15; implementation continues on
`v1.3-dev` (remote `BeardedBats/Kel`).

## Gate board

| Gate | State | Note |
|---|---|---|
| G0 — baseline and source provenance | **COMPLETE** | evidence in §Gate 0 |
| G1 — donor audit + design docs | **COMPLETE — awaiting user approval** | six deliverables below |
| G2 — memory foundation | **COMPLETE** | `kel/memory.py` + 16 tests; migration 001 with backup/receipt; see §Gate 2 (as-built) |
| G3 — project map + context composer | **COMPLETE** | `kel/projectmap.py` + `kel/composer.py` + 17 tests; migration 002; see §Gate 3 (as-built) |
| G4 — continuation | **COMPLETE** | migration 003 + `kel/continuation.py` + service wiring + 26 tests + 8/8 live probes (evidence: docs/v1.3/evidence/gate4-continuation-probe.json); see §Gate 4 below |
| G5 — recipes | **COMPLETE** | migration 004 + `kel/recipes.py` (842 lines) + 5 builtins + 14 tests; suite 254+10; see §Gate 5 |
| G6 — user experience | not started | blocked on approval |
| G7 — adversarial acceptance + freeze | not started | blocked on approval |

## Gate 0 evidence (all CONFIRMED)

1. Workspace `Kel-V1.3-Dev` vs frozen `Kel Releases/Kel-V1.2-Frozen`: `diff -rq` shows exactly
   three deltas — workspace has `Agents.md` (approved workspace instruction file); frozen has
   `RELEASE_MANIFEST.md.txt` + `SHA256Sums.txt.txt`. Everything else byte-identical.
2. Frozen artifact hashes (re-verified unchanged at Gate 1 close): `Kel.exe E048632E…`,
   `resources/app.asar B56816B6…`, `resources/kel-engine/KelEngine.exe 11D9DBC0…` — all equal to
   `SHA256Sums.txt.txt`.
3. Engine provenance: embedded PYZ sha256 `64036e36…` identical to the local build PYZ;
   **22/22** `kel.*` modules structurally identical to the `outputs/Kel-Prototype` source.
4. Shell provenance: deployed `app.asar` extraction byte-identical to its prepack stage tree
   (9,539 files + 1,050 dirs = 10,589 entries).
5. Authoritative baseline suite re-run: **181 passed, 10 subtests passed** (37.04 s).
6. Pipelines identified: engine — PyInstaller 6.19.0, `KelEngine-b3.spec` (canonical
   `work/KelEngine.spec`); shell — electron-vite build of `work/aion-donor` → stage tree →
   `_kel-work/asar-dedup-pack.js` (content-addressed dedup + per-file SHA256 integrity, 4MB
   blocks).
7. Evidence artifacts: `_kel-work/v13-gate0/` (diff results, hash records, provenance scripts,
   suite log, asar extraction) and `_kel-work/v13-donors/` (12 pinned donor clones +
   `revisions.txt`).

## Gate 1 deliverables

| File | Size | State |
|---|---|---|
| `KEL_V1.3_DONOR_AUDIT.md` | 41 KB / 537 lines | complete (18 sections) |
| `KEL_V1.3_ARCHITECTURE.md` | ~23 KB | complete (§0–§14) |
| `KEL_V1.3_MEMORY_MODEL.md` | 22 KB | complete (16 sections) |
| `KEL_V1.3_CONTINUATION_SPEC.md` | ~16 KB | complete (§1–§12) |
| `KEL_V1.3_RECIPE_SPEC.md` | 15 KB | complete (§1–§9) |
| `KEL_V1.3_TEST_MATRIX.md` | ~16 KB | complete (§0–§7) |

Reviewer relay: checkpoint #1 (schemas/authority/continuation/recipe design) = **CONTINUE**
(2026-09-14); checkpoint #2 (gate completion) result recorded in the session's final report.

## Gate 1 approval report

### A. Pinned donor revisions and licenses (inspected at these exact revisions)

| Donor | Revision | Commit date | License (read at revision) |
|---|---|---|---|
| NousResearch/hermes-agent | `40f2702b22a3` | 2026-09-14 | MIT |
| Untrivial-ai/agent-orchestrator | `768ab5034b98` | 2026-09-15 (IST) | Apache-2.0 |
| ephor/warpforge | `d8f3148d3adb` | 2026-09-13 | MIT |
| Chuzom/Chuzom | `5041d169d630` | 2026-08-29 | MIT |
| Orkas-AI/Orkas | `5f1be8f7062c` | 2026-09-14 | MIT (vendored OpenBLAS BSD-style, outside reuse path) |
| microsoft/conductor | `64b71675432c` | 2026-09-11 | MIT |
| pioneerdotai/pioneer | `b9afb60df7f6` | 2026-09-14 | MIT (LGPL-3.0 vendored zstd dir excluded) |
| Adulari/forge | `39a63bb4762b` | 2026-09-14 | **AGPL-3.0 — ideas only, no code** |
| ryderderder/orchestrator | `5bc35eb1432d` | 2026-08-09 | MIT |
| xopcai/xopc | `2c574271d39b` | 2026-09-15 (CST) | MIT |
| block/goose | `a23a8cd5b138` | 2026-09-14 | Apache-2.0 |
| agentscope-ai/CoPaw | `0b8a12f55180` | 2026-09-14 | Apache-2.0 |
| Tier 4: iOfficeAI/AionUi fork | `6744099` + local Kel mods | — | Apache-2.0 |
| Tier 4: AionCore (KellShell) | stock v0.2.2 binary | — | Apache-2.0 |

Clones: `_kel-work/v13-donors/<owner>_<repo>`; pinned table: `v13-donors/revisions.txt`;
file-level citations: `KEL_V1.3_DONOR_AUDIT.md`.

### B. Exact code proposed for STEAL (surgical, license-checked)

1. **hermes context fencing + sanitizer** — `agent/memory_manager.py:167-177` (MIT, ~30 lines,
   pure `re`): strips `<memory-context>` fences from provider output so provenance cannot be
   forged. Copied or transcribed with attribution; mirrored test:
   `test_sanitize_context_strips_fence_escapes` (adapted).
2. **hermes `MemoryProvider` lifecycle seam** — `agent/memory_provider.py:73-193` (MIT):
   the *shape* (required vs optional hooks; storage/retrieval/assembly split). Kel's
   `kel/memory.py` implements a project-scoped subset; no plugin discovery.
3. **Chuzom frozen frontier + retry/escalation loop** — `src/chuzom/agentic/ledger.py:105-142`
   and `engine.py:213-247` (MIT, stdlib, ~150 lines total): freeze semantics, `next_pending`
   DAG frontier, bounded retry → monotonic escalation → terminal block. Reimplemented against
   Kel's store; tests adapted: `test_s12_dag_independent_sibling_progresses`,
   `test_s6_bounded_attempts_then_escalate`, `test_s8_unmeetable_milestone_blocks`,
   `test_replan_is_not_reachable_from_any_entry_point`.

Everything else in the audit is pattern-level (no literal copying). If any further fragment is
copied during G2–G5, it must add attribution + a mirrored test before merge.

### C. Exact patterns proposed for ADAPT (reproduced inside Kel)

- hermes: explicit scope args + session/project rebind; write provenance metadata;
  refuse-to-flush-on-drift posture (posture only).
- agent-orchestrator: pure `derive(facts) → status`; fail-closed observation idiom (zero = unknown,
  callers fail closed); version-counter invalidation + purpose-specific freshness; append-only
  observation accumulation with fail-closed overflow; generation-pinned runtime handles.
- warpforge: durable restore-on-boot; wake-parent via inbox (durable table, not in-memory);
  conversation↔session attach; pause-on-blocked, resume-from-frontier; handoff documents.
- Chuzom: objective acceptance result shape + flaky≠failure distinction; do-nothing-oracle
  rejection + irreversible gate (**plus building the digest/dependency revalidation the donor
  lacks**).
- Orkas: derived model-relative context budget (ratios); executor-owned timeout; worker memory
  read-only.
- conductor: per-type forbidden-field validation; explicit terminate step **plus Kel's third
  UNCERTAIN state**; versioned checkpoint (+ file hash ⇒ recipe version pinning); depth/cycle
  guards as REFERENCE only.
- pioneer: self-review ban keyed to executor identity; evidence classes + default-weak +
  contradiction-never-auto-approves; blocked-only resume with revision bump + re-review.
- forge (ideas only, AGPL): verification ledger where a mutation stales prior evidence; bounded
  completion gate with explicit UNVERIFIED outcome; continuation guard (continuation ≠ success);
  narration stall guard (REFERENCE).
- ryder: exact-session-only resume (never "most recent"); honest auth lattice
  (`signed-in/signed-out/unknown/unprobed`); quota signals auto-expire at reset.
- xopc: hard worker budgets (iterations/tokens/time); default-allowlist + always-blocked denylist;
  structured-output terminating tool with "missing call = failure".
- goose: recursion refusal defense-in-depth (tool not listed + call-time error); bounded subagent
  turns (recipe > env > default); typed subagent sessions.
- CoPaw: ACP session/permission mechanics (already adopted) — reference only; its in-memory
  permission gap is explicitly NOT copied.
- agent-orchestrator/Conductor/Orkas/ryderderder/xopc/goose: **AVOID** the wrappers (readiness
  coordinator, recursive workflow engine, provider-coupled runner, per-harness adapters).

### D. Attribution requirements (before any copy lands)

- `THIRD_PARTY_NOTICES` (or extended `NOTICE.txt`) entry per adopted item: repository URL, commit
  sha, license text (MIT notice + copyright line), and the Kel files containing copied/adapted
  material.
- Apache-2.0 donors (agent-orchestrator, goose, CoPaw): NOTICE-obligation check (§4(d)) before
  copying; attribution in NOTICES even for adapted code where required.
- forge: no attribution needed (no code); keep behavioral descriptions only.
- Every STEAL/ADAPT ships with a test covering the adopted behavior (per the brief).

### E. Final data model (all additive; single `kel.sqlite3`)

| Migration | Tables | Purpose |
|---|---|---|
| 001 | `memories`, `memory_events`, `memory_conflicts`, `memories_fts` (optional) | project memory records + append-only audit + conflicts + FTS |
| 002 | `project_maps`, `context_packets` | versioned map snapshots + packet provenance records |
| 003 | `job_links` | conversation↔job links (origin/continuation) |
| 004 | `recipes` | versioned recipe library (builtin + project scope) |
| (cross) | `schema_migrations` | applied-migration record; FTS availability note |

Contract additions (JSON, optional, backward compatible): `recipe {id, version, digest}` and
`source_digest`. New store helpers: `reopen`, `invalidate_milestone`. No existing V1.2 table is
altered; downgrade = old engine ignores new tables. Full DDL: MEMORY_MODEL §4/§13, ARCHITECTURE
§7, CONTINUATION_SPEC §6, RECIPE_SPEC §7.

### F. Authority and conflict rules (final)

Authority order (1 strongest → 7 weakest): 1) current explicit user instruction; 2) user-confirmed
project decision/preference; 3) verified repository/configuration fact; 4) previously accepted
project decision; 5) reviewed worker evidence; 6) model inference; 7) untrusted external content.
Rules: preferences only at ≤2 (never inferred); L6/L7 never displayed as fact; promotions are
explicit (L6→L2 by user confirmation; L5 only via reviewer gate; L7 never automatic); conflicts are
recorded in `memory_conflicts` and resolved by authority, else newest-wins for facts/commands, and
**user choice required for decision/preference contradictions**; supersession preserves history;
superseded/stale/retracted records are excluded from context; secrets refused at write.

### G. Continuation semantics (final)

Durable job/milestone/run state is the only source of truth; conversation text may filter but never
reconstruct work. Resolution: exactly one obvious candidate → continue; several → user chooses
(top 3 with state/progress/age); none → clear "nothing to continue"; wrong-project references are
refused; VERIFIED jobs are not resumable. Resume: attach (`job_links`) → state routing → revalidate
only digest-affected ACCEPTED milestones (explicit reasons) → reopen only READY/NEEDS_REPAIR/
UNCERTAIN/INVALIDATED milestones → reuse shape-validated native session or bounded continuation
packet → re-verify + re-review (executor ≠ reviewer) → standard publication. Approvals remain
user-only and survive restarts; resume is idempotent; completed work is never mistaken for
unfinished. Full spec: `KEL_V1.3_CONTINUATION_SPEC.md`.

### H. Recipe schema (final)

Strict declarative JSON (stdlib validator; unknown fields are errors): schema_version, recipe_id,
recipe_version, name/description, source, kind (coding|document|research|mixed), inputs, 1–5 steps
(checks limited to contains/min_chars/manual_review; bounded retries; on_fail retry/escalate/block),
permissions (allowlist incl. `commands:run` for declared package/smoke commands; undeclared use =
compile error), verification requirements, terminal_states (must include UNCERTAIN),
budget + retry policy caps. Compiles to the existing CompletionContract (provenance
`{id, version, digest}` pinned); five builtin recipes (Fix Bug, Audit and Repair, Ship Release,
Research Then Implement, Continue Work — the last compiles to the continuation flow, creating no
new job). Storage: append-only `recipes` table (migration 004), project-local recipes shadow
builtins, same-version edits rejected, saving a successful run as a recipe requires explicit user
confirmation. `assess()` untouched. Full spec: `KEL_V1.3_RECIPE_SPEC.md`.

### I. Migration plan

Single additive series 001–004 (memory; map+packets; continuation links; recipes) plus
`schema_migrations`. One backup (SQLite backup API) + integrity check + receipt before the first
V1.3 mutation; idempotent `CREATE ... IF NOT EXISTS` everywhere; no existing V1.2 table altered;
old records tolerated; downgrade = older engine ignores new tables. Failure to back up blocks only
the memory features, never the durable work loop. Details: MEMORY_MODEL §13.

### J. Implementation phases

| Phase | Exit criteria |
|---|---|
| Prerequisite (post-approval) | V1.2 source + pipeline consolidated into `BeardedBats/Kel`; baseline tagged; `v1.3` dev branch created |
| G2 memory foundation | memory suite (MEM-01..12) green; full suite ≥ 181+10 |
| G3 map + composer | MAP-01..07, CTX-01..09 green; measurement harness records packet metrics |
| G4 continuation | CONT-01..11 green incl. restart + new-conversation live probes |
| G5 recipes | REC-01..08 green; 5 builtin recipes compile to valid contracts |
| G6 UX | packaged Work-context surfaces render (PKG-07 level), zero page errors, no raw internals |
| G7 acceptance + freeze | full brief acceptance matrix PASS on packaged Kel.exe (PKG-01..10); freeze + manifest + hashes; V1.2-Frozen proven untouched |

### K. Test plan

64 acceptance items mapped in `KEL_V1.3_TEST_MATRIX.md` (MEM-01..12, MAP-01..07, CTX-01..09,
CONT-01..11, REC-01..08, TRUST-01..07, PKG-01..10) across unit / integration / live / packaged
levels, plus the retention rule (V1.2 suite never weakened) and the C4 before/after measurement
protocol (no savings claims without measurements).

### L. Packaging plan

Engine: same PyInstaller spec; verify PYZ inventory delta (+5 modules, changed set), per-module
structural checks, packaged boot test, V1.2 data opens with migration receipt. Shell: prefer
renderer-only changes; electron-vite build → overlay into fresh deployed-asar extraction →
`asar-dedup-pack.js` repack; entry-count + dedup + data-size parity explained; live Kel.exe test.
`Kel-V1.2-Frozen` remains untouched and hash-verified at every gate. Repository consolidation to
`BeardedBats/Kel` (source + pipeline + baseline tag + v1.3 branch) happens only after Gate 1
approval — nothing was pushed in Gate 1.

### M. Unresolved risks (carried into implementation)

1. FTS5 availability in the packaged sqlite (probe + LIKE fallback).
2. Budget constants are TENTATIVE until G7 measurements.
3. Legacy jobs without `source_digest` (conservative revalidation path).
4. Native session id trust (shape validation; refusal to guess).
5. Single-model-key reviewer independence limit (documented since V1; unchanged).
6. Packet persistence growth (cap + prune policy at G3).
7. Windows WAL/backup timing (reuse migration.py discipline).
8. Continuation MARGIN tuning (deterministic, test-pinned only).
9. Asar renderer-change parity risk (full dedup/integrity checks).
10. Memory scanner false positives (allowlist + fixture tests).
11. AGPL boundary enforcement for forge (process rule + code review).
12. Write-transport clipping during doc production (recovered; all docs verified byte-for-byte on
    disk by size/section/marker scans).

### N. Reviewer checkpoints and stop state

- Checkpoint #1 (memory schema / authority rules / continuation semantics / recipe schema):
  **CONTINUE** (2026-09-14).
- Checkpoint #2 (Gate 1 completion declaration): **CONTINUE** (2026-09-14).
- **STOP STATE**: Gate 1 is complete and awaiting the user's explicit approval. Gate 2 has not
  started; no production code was edited; no git operations were performed.
- **After Gate 1 approval** (in order): (1) consolidate the authoritative V1.2 source and
  packaging pipeline into the new `BeardedBats/Kel` repository; (2) tag the baseline; (3) create
  the V1.3 development branch; (4) begin Gate 2 (memory foundation) on that branch.

## Gate 2 (as-built) — structured project memory  [2026-09-15]

Implemented on `v1.3-dev`:

- `runtime/kel/memory.py` (581 lines): migration 001 (`schema_migrations`, `memories`,
  `memory_events`, `memory_conflicts`, optional `memories_fts`) with a one-time pre-migration
  backup (`backups/pre-v13-*.sqlite3`, integrity-checked) and `migration-receipt.json`;
  deterministic LIKE fallback when FTS5 is unavailable (`Memory(use_fts=False)`; auto-probe
  default); the 7-level authority model; supersession + history chains; open conflicts for
  equal-authority decision contradictions with `resolve_conflict`; `confirm`/`correct`/
  `retract`/`forget`; secret refusal with content-free audit events; strict project isolation;
  durable event-log mirror (`events` rows under `memory:<id>`).
- `runtime/tests/test_v13_memory.py` (16 tests): MEM-01..MEM-12 plus conflict resolution,
  backup-failure refusal, partial-migration recovery, and event-log coverage. Targeted: 16
  passed; full suite: **197 passed + 10 subtests** (was 181+10).

As-built notes (evidence-backed adjustments; specification updates recorded here):

- `memory_events.action` additionally uses `refused` for rejected secret-like writes
  (content-free `detail={'scan': <pattern-name>}`), and refusals are mirrored to the durable
  event log.
- Explicit replacement supersession is driven by `correct()` (new record supersedes the old one
  with a `superseded_by`/`supersedes` chain); brand-new contradicting user decisions at equal
  authority stay open conflicts by design (reconciles matrix MEM-04 with MEMORY_MODEL §8).
- `confirm()` refuses trust-7 (external) rows: external content is adopted only by restating it
  as a user decision (citation kept in `source_ref`).
- Migration receipt: a pre-existing `migration-receipt.json` is preserved as
  `migration-receipt-legacy.json` before the V1.3 receipt is written.
- Donor code copied in Gate 2: **none** (original implementation). The hermes context-fencing
  sanitizer remains scheduled for Gate 3 (`kel/composer.py`) with attribution at copy time.

Next: Gate 3 (project map + context composer).

## Gate 3 (as-built) — project map + context composer  [2026-09-15]

Implemented on `v1.3-dev`:

- `runtime/kel/projectmap.py`: migration 002 (`project_maps`, `context_packets`); deterministic
  inspection (identity/repo state, execution commands with lockfile-based runner detection,
  architecture entry points/packages/dependencies, conventions, state from jobs/memories);
  git-tree + key-file fingerprints; versioned snapshots with probe-first incremental refresh
  (unchanged sections are copied forward without re-inspection); `stale_sections(changed_paths)`;
  optional bounded synthesis hook whose output is labeled `inferred`.
- `runtime/kel/composer.py`: the single context path. Provenance-labeled sources (request,
  memories with authority labels, job state + evidence digests, map sections, bounded
  recent-turns window, explicit attachments), authority-aware memory selection with deterministic
  tie-breaks, open-conflict surfacing with per-record annotations, deterministic deduplication,
  explicit character budget with recorded omissions (request/decisions never dropped),
  digest-stable `packet_id`, persisted structure for every packet and full text only for
  job-linked packets. Contains the **first copied donor code**: hermes fence/sanitizer
  (NousResearch/hermes-agent, MIT, revision `40f2702b22a3`, `agent/memory_manager.py:167-177`,
  adapted in `kel/composer.py`; mirrored test `test_fence_sanitizer_mirrors_donor_behaviour`;
  attribution recorded in THIRD_PARTY_NOTICES at release time).
- Tests: `runtime/tests/test_v13_projectmap.py` (7, MAP-01..07) and
  `runtime/tests/test_v13_composer.py` (10, CTX-01..09 + fence mirror). Targeted: 17 passed;
  full suite: **214 passed + 10 subtests** (was 197+10).
- `runtime/tools/measure_context.py`: C4 measurement harness (legacy handoff vs composer
  packets, source mix, omissions).

Representative measurements (this pass, three fixtures): legacy handoff 1299-1327 chars;
composer packets 1737-1765 chars (~434-441 estimated tokens). The composer adds labeled
provenance, map sections, and per-source reasons rather than minimizing characters; source mix
and omissions are recorded per packet. Savings claims remain withheld until Gate 7 runs the
comparison on live task packets.

As-built fixes during this gate: probe-first refresh (inspection runs only when a section's
cheap inputs changed); `schema_migrations` is created by the migration-002 path when memory's
migration has not run; `records()` no longer shadows the builtin `type()`.

Next: Gate 4 (first-class continuation).

## Gate 4 (core as-built) — first-class continuation  [2026-09-15]

Landed on `v1.3-dev` (this commit; the gate is not yet declared complete):

- `runtime/kel/continuation.py`: migration 003 (`job_links`); project-scoped candidate
  resolution from durable state only (continuable states, CLOSED failed/uncertain with
  retryable milestones, explicit-only CANCELLED); deterministic ranking (text match,
  conversation link, state priority, accepted count, recency); single-vs-choice-vs-none rule
  (single also when the top candidate is linked to this conversation and strictly beats every
  other); idempotent `attach()`; `plan_resume()` (preserve / reopen / revalidate-with-reasons,
  source-digest revalidation, legacy coding fallback via `check_evidence`, native-session
  shape validation — never guessed); `execute_resume()` routes PAUSED to resume,
  WAITING_RESOURCE to retry_route, CLOSED to reopen, then attaches; `explain()` summary.
- `runtime/kel/core.py`: two additive helpers — `Store.reopen()` (refuses VERIFIED jobs,
  requires a retryable milestone, refuses with active runs) and `Store.invalidate_milestone()`
  (explicit reason, revision-guarded, refuses with active runs).
- `runtime/tests/test_v13_continuation.py` (17 tests): isolation, eligibility, single/choice/
  text-ranking/none, VERIFIED refusal, attach idempotency + restart survival, all resume
  routes, revalidation vs preservation, legacy evidence-check fallback (mocked), session
  validation, approval-state attach-only, idempotent double-resume. Full suite: **231 passed
  + 10 subtests**.
- Still open for Gate 4 completion (next session): service/ACP wiring (submit-flow
  classification, Work-context continuation fields), live app-restart and new-conversation
  probes, and the Gate 4 completion checkpoint.

Next: finish Gate 4 wiring + live probes.

## Gate 4 (complete) — first-class continuation  [2026-09-15]

Completion evidence (beyond the core landing above):

- `runtime/kel/service.py` wiring: `submit` accepts an optional explicit `job_id`
  (dashed-UUID validated) carried in the handoff packet; `_plan` routes continuation intent
  (explicit id, kind `continue`, or continue-verb text) through `_continuation()`: a single
  candidate resumes automatically, multiple candidates produce a deterministic list with job
  ids, none explains honestly; explicit ids from other projects are refused with a clear
  message; VERIFIED jobs are refused explicitly; every new job gets an idempotent `origin`
  job link. `state()` exposes project-scoped `continuation` candidates for the Work surface.
- `runtime/tests/test_v13_continuation_service.py` (9 tests): single-resume via chat,
  ambiguity listing (jobs left untouched), explicit-id resume of a CLOSED job, wrong-project
  refusal, none-message, state candidates, VERIFIED refusal, AWAITING_USER + pending approval
  preserved, origin-link helper. Full suite: **240 passed + 10 subtests**.
- Live probes (real `kel.service` subprocesses over loopback HTTP; evidence:
  `docs/v1.3/evidence/gate4-continuation-probe.json`): **8/8** — resume-single-over-http,
  restart-survives, restart-re-resume-idempotent, new-conversation-continues,
  wrong-project-refused, ambiguous-choice-listed, explicit-choice-resumes,
  approval-survives-restart. No orphan processes after the run.

Next: Gate 5 (reusable workflow recipes).

## Gate 5 (complete) — reusable workflow recipes  [2026-09-15]

Implemented:

- `runtime/kel/recipes.py` (842 lines): migration 004 (`recipes` table per RECIPE_SPEC §7);
  strict stdlib validator (unknown fields rejected at every level, typed inputs, step/check/
  retry/policy rules, dependency acyclicity, placeholder discipline, terminal states must
  include UNCERTAIN); append-only storage with immutability per `(id, version, scope,
  project)`; project recipes shadow builtins with both inspectable; `propose_from_job`
  drafts (preview only — saving always requires `confirm=True` plus, for `from_job` sources,
  an existing job); `compile_recipe` maps steps to the existing CompletionContract
  (provenance `{id, version, digest}` pinned, budget carried, coding recipes require
  root + the declared test command). `continue-work` compiles to a continuation descriptor
  (stages list) and creates no job.
- Five approved builtins seeded idempotently (content changes require a version bump —
  guarded): Fix Bug (coding), Audit and Repair (mixed), Ship Release (mixed),
  Research Then Implement (mixed), Continue Work (document/special). `Service.__init__`
  installs them idempotently at startup.
- Tests: `runtime/tests/test_v13_recipes.py` (14): builtin install/validate, unknown-field
  rejection (5 levels), structural rules (18 cases), kind minima + `commands:run` heuristic,
  compile-to-contract (rendering, defaults, explicit failures), confirmation-required saves,
  shadowing + immutability + version listing, propose-from-job (confirm + ghost job),
  builtin tamper guard, frozen accepted steps (claim refused after acceptance), bounded
  repair (attempts 2 then VERIFIED) and bounded failure (attempts 4, FAILED), verdict
  remaining Kel-controlled (`terminal_states` never enters the contract), interrupted-recipe
  resume with accepted milestone preserved and remaining step reopened, continue-work
  creating no job. Full suite: **254 passed + 10 subtests**.

As-built notes: validation enforces only `project:read` as a kind minimum; `project:write`
and `tests:run` are enforced at compile time (per RECIPE_SPEC §4.4 wording "otherwise compile
refuses"). The `commands:run` heuristic flags steps whose ids are `package`/`smoke` or whose
objectives mention a declared package/smoke command. `Store.get` raises `KeyError` for missing
jobs; `propose_from_job` and the service continuation handler normalize it to a user-facing
error.

Next: Gate 6 (Work-context user experience).


