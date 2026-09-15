# KEL V1.3 — STATUS

Date: 2026-09-14 (Gate 1 close). Owner: Kel V1.3 lead-engineer session.
Production code changed: **none**. Git operations performed: **none** (per directive — repository
consolidation to `BeardedBats/Kel` happens only after Gate 1 approval).

## Gate board

| Gate | State | Note |
|---|---|---|
| G0 — baseline and source provenance | **COMPLETE** | evidence in §Gate 0 |
| G1 — donor audit + design docs | **COMPLETE — awaiting user approval** | six deliverables below |
| G2 — memory foundation | not started | blocked on approval |
| G3 — project map + context composer | not started | blocked on approval |
| G4 — continuation | not started | blocked on approval |
| G5 — recipes | not started | blocked on approval |
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


