# KEL V1.3 — ARCHITECTURE

Status: Gate 1 design deliverable. Basis: Gate 0 baseline verified (workspace == Kel-V1.2-Frozen
except approved files; engine PYZ + source provenance CONFIRMED; suite 181 passed + 10 subtests).
Design checkpoint approved by reviewer relay (CONTINUE, 2026-09-14).

This document is the single architectural map for V1.3. Every V1.3 feature must land inside these
boundaries; anything that would create a parallel system is out of bounds by definition.

## 0. Reading guide

- §1 invariants, §2 system map, §3 module interfaces, §4 data flows, §5 integration points,
  §6 trust boundaries, §7 storage + migration numbering, §8 failure modes, §9 budgets and
  measurement, §10 packaging, §11 gate mapping, §12 explicit non-goals, §13 risks,
  §14 evidence status.
- Detailed schemas: memory tables in `KEL_V1.3_MEMORY_MODEL.md` §4/§13; continuation tables in
  `KEL_V1.3_CONTINUATION_SPEC.md` §6; recipe tables in `KEL_V1.3_RECIPE_SPEC.md` §7.

## 1. Principles and invariants (non-negotiable)

1. **One durable store.** All V1.3 state lives in the existing `kel.sqlite3` (WAL). No second
   database, no second job engine, no second workflow engine, no vector store.
2. **One completion authority.** Only `core.Store.assess()` produces completion records; worker
   output, memory records, recipes and continuations are evidence, never verdicts.
3. **One scheduler.** `engine.tick` remains the only claim/execute/review driver. Continuation and
   recipes re-enter through the same `engine.submit` → `runs` → broker path.
4. **One context path.** `kel/composer.py` is the single context-assembly path for the Commander,
   workers, reviewers, and continuation packets. No parallel prompt stack; the legacy
   `context.handoff` packet remains only as the fallback payload inside the composer.
5. **Project isolation is absolute.** Memory, project maps, continuation candidates and recipes are
   scoped by `projects.id`; cross-project reads are impossible by construction (every query carries
   `project_id`), and tests assert it.
6. **Provenance everywhere.** Every memory record, map section, context packet and recipe run
   carries source references, authority level and digests. Inference is never silently promoted.
7. **stdlib-only engine.** New engine modules import only the Python stdlib plus existing `kel`
   modules. No pydantic, no third-party validators, no new runtime dependencies.
8. **V1.2 behavior is preserved.** With empty V1.3 tables (no memories, no map, no recipes), the
   system behaves exactly as V1.2: same classification fallback, same document/coding/research
   compilers, same verdicts, same publication text. V1.3 features activate additively.
9. **Additive migrations only.** New tables and new optional contract fields; no destructive
   changes to V1.2 data; idempotent `CREATE ... IF NOT EXISTS` (see §7).
10. **Human authority is visible.** Every automatic promotion path is explicit and inspectable;
    nothing becomes an authoritative project decision without a user action or a deterministic
    verification.

## 2. System map

### 2.1 Existing engine modules (unchanged responsibilities)

| Module | Role (V1.2) | V1.3 change |
|---|---|---|
| `kel/core.py` | durable store, events, leases, verdicts, approvals, effects, publication | + `validate_contract` accepts optional `recipe` + `source_digest` fields; new helper for cross-module event writes |
| `kel/engine.py` | supervision tick, claims, review scheduling, escalation | + continuation resume entry (`reopen` path), recipe provenance pass-through |
| `kel/commander.py` | plan compiler + independent review context | prompts built from composer packets; review rubric unchanged |
| `kel/router.py` | deterministic classification + hard-filter routing | + continuation intent classification (delegates to `kel/continuation.py`) |
| `kel/coding.py` | repo snapshots, test evidence, ACP transport | + records `source_digest` (base commit/tree) into contract at compile time |
| `kel/research.py` | citation-bound web research | unchanged |
| `kel/runner.py` | detached brokers, fencing, recovery | unchanged (continuation reuses recovery as-is) |
| `kel/native.py`, `kel/appserver.py`, `kel/coding_transport.py` | native CLI + ACP sessions | unchanged (continuation passes stored session ids through existing paths) |
| `kel/service.py` | loopback service + web UI + submit/plan | + continuation + recipe submission routes; + state API fields for Work context |
| `kel/acp_host.py` | ACP presentation for AionCore | + continuation status lines in the stream; approval surface unchanged |
| `kel/migration.py` | legacy 0.2.1 → current upgrade | unchanged (V1.3 tables ship as additive 001–004) |
| `kel/context.py` | projects, conversations, attachments, handoffs, grants | unchanged tables; handoff packet becomes fallback inside composer |
| `kel/web/` | engine web UI | + read-only sections (memory, map, continuation, recipes) + actions |

### 2.2 New engine modules

| Module | Purpose | Depends on |
|---|---|---|
| `kel/memory.py` | C1 project memory: records, authority, conflicts, supersession, retrieval, revalidation, poisoning defenses | core, context |
| `kel/projectmap.py` | C2 durable project map: deterministic inspection, bounded synthesis, versioning/freshness, incremental refresh | core, context, memory (writes verified facts as candidates) |
| `kel/composer.py` | C4 single context-composition path; packets with provenance, budgets, omission records | core, context, memory, projectmap (+ continuation inputs) |
| `kel/continuation.py` | C3 candidate resolution, conversation attachment, resume planning, revalidation | core, context, composer, coding (evidence reuse) |
| `kel/recipes.py` | C5 recipe schema validation + compilation to CompletionContract + versioning | core, coding, research, engine |

### 2.3 Presentation surfaces (Gates 5–6)

- Donor shell renderer: extend the existing Work context drawer (`KelWorkPanel` family) with
  compact sections — Active/Recent Work, Continue Work, Project Knowledge, Project Map, Recipes.
  No new dashboard, no new navigation; routes stay hidden as in V1.2.
- Engine web UI (`kel/web`): equivalent read-only sections for the standalone web surface.
- Chat remains the primary interface: continuation and recipes are invokable in natural language;
  the visual surfaces are inspection/confirmation affordances only.

## 3. New module interfaces (signature sketches)

```python
# kel/memory.py — C1 (full semantics in KEL_V1.3_MEMORY_MODEL.md)
class Memory:
    def record(...) -> str          # L1-L7 write with authority + provenance
    def propose(...) -> str         # L6 inference proposal
    def confirm(id) / correct(id, ...) / retract(id, ...) / forget(id, ...)
    def resolve_conflict(conflict_id, choice, actor='user')
    def revalidate(project_id, digest_map) -> list[str]     # marks stale, never deletes
    def select(project_id, *, purpose, query=None, types=None,
               topic=None, limit=12, max_chars=6000, include_unconfirmed=False)
    def history(memory_id) ; def conflicts(project_id, state='open')
```

```python
# kel/projectmap.py — C2
class ProjectMap:
    def get(project_id) -> dict | None          # latest version: sections, fingerprint, updated
    def refresh(project_id, *, force=False, reason='manual') -> dict
    def stale_sections(project_id, changed_paths) -> list[str]
    # internals: deterministic inspection first (_inspect_*), bounded synthesis second (_synthesize)
```

Map content model (sections stored per version, each with sources + digests):
`identity` (name, root, repo state = branch/HEAD/dirty, language/framework), `execution` (start,
build, test, lint/type-check, package/release commands with source refs), `architecture` (entry
points, core modules, UI layer, runtime/services, data/storage, integrations, key dependencies —
deterministic skeleton with bounded inferred prose), `conventions` (source/test locations, naming,
release conventions, guardrails), `state` (known decisions with refs, active work job ids, recent
meaningful changes from bounded git log, unresolved risks). Freshness: `project_maps` rows are
immutable per version `(project_id, version)` with a `fingerprint` = git tree digest (or key-file
digest bundle when no git); refresh creates a new version and marks changed sections; a section
whose inputs did not change is copied forward with its digests (incremental, never a full rescan).

```python
# kel/composer.py — C4 (single context path)
class Composer:
    def __init__(self, store, memory, projectmap): ...
    def build(self, *, project_id, request, conversation_id, job=None,
              continuation=None, attachments=(), purpose='plan',
              budget_chars=32000) -> dict     # the context packet
```

Packet schema (v1): `{schema, packet_id (digest), project_id, task/job ref, purpose, sources:
[{kind, ref, reason, trust, chars, digest}], omitted: [{kind, ref, reason}], conflicts: [...],
size: {chars, tokens_est}, created}`. Source kinds allowed: `request`, `memories`, `map_sections`,
`job_state` (milestone summaries incl. accepted artifacts by digest), `evidence` (artifact digests),
`recent_turns` (bounded window, default 16 messages / 8k chars), `attachments` (explicit), `changes`
(recent meaningful project changes). Never included: full transcripts, all memories, other
projects, superseded/stale/retracted records, raw worker transcripts, unlabeled external text.

```python
# kel/continuation.py — C3 (full semantics in KEL_V1.3_CONTINUATION_SPEC.md)
class Continuation:
    def resolve(self, *, project_id, conversation_id, text=None) -> Resolution
    def attach(self, job_id, conversation_id, *, reason) -> str
    def plan_resume(self, job_id) -> ResumePlan
    def execute_resume(self, job_id, conversation_id) -> dict
```

```python
# kel/recipes.py — C5 (full schema in KEL_V1.3_RECIPE_SPEC.md)
def validate_recipe(recipe: dict) -> dict                    # canonical + strict; PolicyError on any violation
def compile_recipe(recipe, *, inputs, project_id) -> tuple[dict, dict]   # (contract, provenance)
def list_recipes(store, project_id) ; def get_recipe(ref, version=None)
def propose_from_job(store, job_id, name) -> dict           # explicit user confirmation required to save
def save_recipe(store, recipe, *, project_id=None, actor='user')
```

## 4. Data flows

**A — Submit flow (normal, continuation, recipe).**
`service.submit` classifies (V1.2 deterministic classifier extended with continuation/recipe
intents). Three branches, one destination:
1. *Continuation* → `Continuation.resolve` → exactly-one candidate → `execute_resume`:
   attach conversation (`job_links`), reopen only READY/NEEDS_REPAIR/UNCERTAIN milestones,
   revalidate affected ACCEPTED milestones on digest change, build a continuation packet, then the
   **existing** engine tick claims and executes. No new job is created. Several candidates → the
   user chooses (chat message + Work context list). None → clear "nothing to continue" answer.
2. *Recipe* → `validate_recipe` → `compile_recipe` → `engine.submit(contract)` with recipe
   provenance pinned in the contract. Same scheduler/store/verification/publication.
3. *Normal* → `composer.build(purpose='plan')` → existing compilers (template/commander/
   coding/research — unchanged shape) → `engine.submit`.

**B — Execution with context.** `engine.tick` claims (unchanged) → `_execute` passes the packet
through the existing `contract.context` channel → workers/reviewers consume the packet (reviewers
get the same provenance-labeled packet; rubric unchanged) → verify → `record_review` →
`assess` → `publish` (all unchanged). Native session resume uses `runs.native_session` exactly as
V1.2; when invalid, the continuation packet is the bounded fallback.

**C — Context composition.** select (memory + map + job + turns + attachments) → dedupe by
`(kind, ref)` → precedence order (request > user-confirmed decisions > verified facts > map
sections > accepted milestones > recent turns > inferences) → budget truncation (drop order:
recent turns → inferences → map prose; never request/decisions/constraints) → omissions recorded →
digest computed → packet delivered to Commander/worker/reviewer. Every inclusion has a `reason`.

**D — Project map refresh.** Trigger: manual refresh, first project open, or a composer-time
digest mismatch. Deterministic inspection (bounded directory walk + config/manifest reads) →
skeleton sections; optional single bounded synthesis call for `architecture`/`conventions` prose
(marked inferred) → new `project_maps` version + fingerprint → verified facts offered to memory
(L3 with digests) → sections whose inputs changed are flagged; everything else copied forward.

**E — Memory writes.** Explicit user statement ("remember…") → L2 record; deterministic
inspection during map refresh → L3 facts; reviewed worker output → L5 evidence; model inference →
L6 proposal (visible for confirm/discard); external content → L7 labeled evidence only. Digest
revalidation on map refresh marks stale records; conflict detection runs on every write.

## 5. Integration points (exact places, minimal touch)

| Existing surface | V1.3 touch |
|---|---|
| `service.submit` | classify extension: continuation/recipe intents; `choice`/`none` resolution returns a message instead of creating a job; recipe branch compiles then submits normally |
| `service._plan` | builds one composer packet per job; passes it to the existing compilers (document commander, coding/research/chat unchanged in shape) |
| `core.Store` | new small helpers: `reopen(job_id, reason)` (verified quiescent; at least one retryable milestone; state→READY, assessment cleared, event `job.reopened`) and `invalidate_milestone(job_id, mid, reason, expected_revision)` (milestone→INVALIDATED with explicit reason, event `milestone.invalidated`); `validate_contract` accepts optional `recipe` and `source_digest` fields (unknown-field tolerance keeps old contracts valid) |
| `engine.submit` / `engine._execute` | unchanged mechanics; packet travels via existing `contract.context`; continuation reuses `control('resume')`, `retry_route`, the claim path, and `runs.native_session` |
| `commander.plan/review` | prompt text gains the provenance-labeled packet; reviewer rubric and separation unchanged |
| `acp_host` | one short continuation/attach status line in the stream; AWAITING_USER guidance unchanged |
| `kel/web` + Work context drawer | state API fields: continuation candidates, per-job Continue action, map freshness, memory list, recipe list (surfaces per their specs) |

## 6. Trust boundaries

| Input | Authority | Enforcement |
|---|---|---|
| live user text | instruction for this turn | classification + contract request |
| attachments | context, never permission | existing handoff/attachment store; labeled in packet |
| memory records | per authority level (memory model) | composer labels; L6/L7 never presented as fact |
| project map sections | context, never completion evidence | labeled `verified` vs `inferred` per section |
| worker output | evidence until reviewed | inbox consume → verify → record_review (executor ≠ reviewer) |
| external documents/web | labeled untrusted evidence (L7) | memory scanner + fence labels; never instructions |
| recipes | validated declarative template | strict validator (§RECIPE_SPEC); compile-time refusal on undeclared permissions |
| transcripts | **never** a reply/continuation source | not stored as authority; composer bounded recent-turns only |

Comment note for code: artifacts/memory text entering prompts are wrapped in provenance fences
(memory-context style, adapted from hermes) and fence markers are stripped from model output so a
worker cannot forge provenance.

## 7. Storage and migration numbering (single V1.3 series)

001 memory tables — `KEL_V1.3_MEMORY_MODEL.md` §4/§13.
002 project map + context packets — this document:

```sql
CREATE TABLE IF NOT EXISTS project_maps(
  project_id TEXT NOT NULL, version INTEGER NOT NULL, fingerprint TEXT NOT NULL,
  data TEXT NOT NULL, updated REAL NOT NULL, note TEXT,
  PRIMARY KEY(project_id, version));
CREATE TABLE IF NOT EXISTS context_packets(
  packet_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, job_id TEXT,
  conversation_id TEXT, purpose TEXT NOT NULL, data TEXT NOT NULL, created REAL NOT NULL);
```

003 continuation links — `KEL_V1.3_CONTINUATION_SPEC.md` §6 (`job_links` + helpers).
004 recipes — `KEL_V1.3_RECIPE_SPEC.md` §7.

All migrations are additive + idempotent; ONE backup+receipt before the first V1.3 mutation
(policy in MEMORY_MODEL §13). Old engines ignore the new tables (safe downgrade path).

## 8. Failure modes and recovery

| Failure | Handling (all reuse existing machinery where possible) |
|---|---|
| app restart mid-job | existing startup recovery: PLANNING→INTERRUPTED, expired runs fenced ORPHANED (no blind retry), brokers adopted; V1.3 adds persisted `job_links` and an idempotent `reopen` |
| worker/provider loss | existing circuit breakers, `WAITING_RESOURCE`, `retry_route`; continuation surfaces the wait, never fabricates progress |
| native session invalid | refuse to guess ("most recent" banned); bounded continuation packet instead; explicit message |
| map refresh failure | previous map version kept; refresh note records the error; stale flags only on real digest change |
| memory write failure | job execution unaffected; surfaced as a limitation (memory is a side channel, not a dependency) |
| composer over budget | deterministic drop order (recent turns → inferences → map prose); omissions recorded in the packet; request/decisions/constraints are never dropped |
| ambiguous continuation | user choice; no fallback guess |
| restart while AWAITING_USER | approvals persist in SQLite; badge + Work context re-surface them |
| duplicate/concurrent resume | `job_links` uniqueness + the existing one-active-run-per-milestone index serialize execution |

## 9. Budgets and measurement

Default packet budgets (initial constants; TENTATIVE until Gate 7 measurements): plan 32k chars,
worker 24k chars, review 16k chars; recent-turns window 16 messages / 8k chars; memory top-12
records / 6k chars; map sections ≤ 4 selected. Every packet's structure (sources, reasons, sizes,
omissions) is persisted in `context_packets`; full text is persisted only for job-linked packets
(redaction policy applies).
Measurement protocol (brief C4): on representative tasks (document, coding fix, research), record
source mix + packet chars/tokens before vs after V1.3; results go to
`KEL_V1.3_VERIFICATION_REPORT.md` at Gate 7. **No savings claims without these measurements.**

## 10. Packaging plan

- **Engine**: same PyInstaller pipeline and spec; expected PYZ delta = +5 new modules
  (`memory`, `projectmap`, `composer`, `continuation`, `recipes`) + changed set
  (`core`, `service`, `engine`, `router`, `coding`, `commander`, `acp_host`, plus `kel/web`
  assets). Verify: PYZ inventory comparison, per-module structural check, packaged boot test
  (version, providers, `/api/state`, submit, `/api/shutdown-idle`), V1.2 data opens (migration
  receipt present).
- **Shell**: prefer renderer-only changes (Work context sections); rebuild via electron-vite,
  overlay into the fresh extraction of the deployed asar, repack with `asar-dedup-pack.js`;
  parity checks: entry counts, dedup savings, data-size delta explained; live Kel.exe test.
- **Never accept logical source correctness as packaging proof** (brief). 
- **Frozen discipline**: `Kel-V1.2-Frozen` is never modified; re-verified by hashes at each gate.
- **Repository consolidation (post-approval, user-directed)**: after Gate 1 approval, the
  authoritative V1.2 source + packaging pipeline are consolidated into the new
  `BeardedBats/Kel` repository, the baseline is tagged, and the V1.3 development branch is
  created — before any production implementation begins. Gate 1 performs **no** git operations.

## 11. Gate mapping

| Gate | Deliverable | Exit criteria |
|---|---|---|
| G2 memory foundation | `kel/memory.py` + migration 001 + tests | memory suite green (MEM-01..10); V1.2 suite still 181+10 |
| G3 map + composer | `kel/projectmap.py`, `kel/composer.py` + migration 002 + tests | MAP-01..06, CTX-01..07 green; packet budget tests; measurement harness |
| G4 continuation | `kel/continuation.py` + migration 003 + tests | CONT-01..11 green incl. restart + new-conversation live probes |
| G5 recipes | `kel/recipes.py` + migration 004 + 5 recipes + tests | REC-01..08 green; recipes compile to valid contracts |
| G6 UX | donor renderer + web UI sections | packaged surfaces render; zero page errors; no raw internals exposed |
| G7 adversarial acceptance + freeze | full matrix + packaged live tests + manifest | brief acceptance matrix ALL PASS on the packaged Kel.exe; freeze + hashes |

## 12. Explicit non-goals

Rust migration; KellShell or donor-shell replacement; generic vector DB; broad personal memory;
cloud sync; learned routing; model-quality scoring; generic DAG editor; recursive delegation;
autonomous agent teams; hidden memory; broad UI redesign; mobile; account/sync systems.
Design anti-goals: no second scheduler, no second job store, no parallel prompt stack, no
transcript-based resume, no mutable single-blob memory.

## 13. Risks (unresolved, carried to implementation)

| Risk | Mitigation / probe |
|---|---|
| FTS5 missing in packaged sqlite | probe at migration; bounded LIKE fallback; test both paths |
| Non-git project digest | key-file digest bundle fallback; documented approximation |
| Legacy jobs without `source_digest` | conservative revalidation via existing `check_evidence`; else keep accepted with note |
| Native session id trust | shape validation (UUID-style); quoted ids quarantined; refusal to guess |
| Single-model-key reviewer limitation | unchanged V1.2 limitation; provenance records reality |
| Packet persistence growth | cap + prune policy at G3 (TENTATIVE) |
| Measurement not yet performed | G7 protocol; no claims meanwhile |
| AGPL hygiene (forge) | process rule: behavioral descriptions only; audit at code review |
| Windows WAL/backup timing | reuse migration.py wait/retry discipline |
| Continuation `MARGIN` tuning | deterministic + test-pinned; adjust via tests only |
| Asar renderer change risk | dedup+parity pipeline; live packaged tests |
| Memory scanner false positives | allowlist + fixture tests (MEM-09) |

## 14. Evidence status (this document)

- **CONFIRMED**: Gate 0 baseline (byte-diff, hashes, PYZ provenance, 181+10 suite); donor
  revisions/licenses (see audit); V1.2 integration surfaces named in §5 (read directly in source).
- **STRONGLY INFERRED**: additive-table design preserves V1.2 behavior (no existing table altered;
  empty tables → current code paths).
- **TENTATIVE**: budget constants (§9), FTS5 availability in the packaged runtime, final module
  inventory (may vary ±1 as implementation lands).



