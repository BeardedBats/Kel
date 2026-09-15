# KEL V1.3 — MEMORY MODEL (C1: Structured Project Memory)

Status: Gate 1 design deliverable. Design checkpoint approved (reviewer relay: CONTINUE, 2026-09-14).
Scope: the project-scoped memory record, schema, authority/conflict rules, lifecycle, retrieval,
poisoning defenses, migration plan, and UI surface for V1.3's C1 capability.
Evidence basis: donor audit (KEL_V1.3_DONOR_AUDIT.md), Kel V1.2 source (kel/core.py, kel/context.py,
kel/migration.py), Gate 0 baseline (CONFIRMED byte-level).

---

## 1. Principles (non-negotiable)

1. **Project memory, not personal memory.** Every record belongs to exactly one `projects.id`.
   No cross-project visibility, ever. (Brief: "Never leak memories between projects.")
2. **Local and structured.** SQLite in the existing `kel.sqlite3`, structured columns + typed JSON
   values. No vector database, no JSON blob, no second memory database.
3. **Provenance-aware.** Every record carries `source_type`, `source_ref`, `actor`,
   `trust` (authority level), and where applicable `source_digest`.
4. **Evidence, not truth.** Model inferences and worker output are stored as *lower-trust evidence*;
   they never auto-become decisions or preferences. (Pioneer: evidence classes; contradiction never
   auto-approves — adapted idea.)
5. **Supersession preserves history.** Nothing is silently overwritten; old records become
   `superseded` with a `superseded_by` link, or `retracted`. Users can inspect the chain.
6. **Conflicts are surfaced.** Contradictions between records are recorded and shown; resolution is
   deterministic by authority, or delegated to the user when authority is equal for decisions.
7. **Untrusted input stays labeled.** External files, README text, webpages, and worker output are
   stored only as labeled evidence (`external_document`, `web`, `worker_evidence`) and can never
   contain authoritative instructions.
8. **Inspectable and editable.** Users can inspect, edit, confirm, retract, and forget memories
   from the Work context surface; nothing is hidden ("no hidden magical memory").

---

## 2. Memory record model

Stored in `memories` (one row per record; `value` is a typed JSON document):

| Field | Type | Meaning |
|---|---|---|
| id | TEXT PK | stable id (existing `uid()` helper), never reused |
| project_id | TEXT FK | owning project; mandatory; enforced on every query |
| type | TEXT | one of the enumerated types (§3) |
| topic | TEXT | normalized key/topic (e.g. `test-command`, `src-layout`, `review-policy`) |
| value | TEXT (JSON) | structured value; shape depends on type (§3) |
| summary | TEXT | one-to-two-sentence human-readable rendering (shown in UI and context packets) |
| source_type | TEXT | `user_instruction` \| `user_confirmation` \| `repo_inspection` \| `config_inspection` \| `worker_evidence` \| `model_inference` \| `external_document` \| `web` \| `system` |
| source_ref | TEXT | exact reference: file path (+sha), git ref, URL, job id, run id, artifact digest, event id |
| actor | TEXT | `user` \| `kel` \| `worker:<provider>` \| `system` |
| trust | INTEGER 1..7 | authority level (§5); higher authority = lower number |
| confidence | REAL null | model confidence for inferences only (0..1); null for deterministic facts |
| user_confirmed | INTEGER 0/1 | set only by an explicit user action (confirm/decide) |
| status | TEXT | `active` \| `superseded` \| `retracted` \| `stale` |
| supersedes | TEXT null | id of the record this one replaces |
| superseded_by | TEXT null | set on the old record when replaced |
| source_digest | TEXT null | digest of the source *at write time* (file sha256 / git tree digest / config digest) |
| created / updated | REAL | timestamps |
| checked_at | REAL null | last revalidation time (digest compare or user confirmation) |

Example record (decision):

```json
{
  "id": "mem_9f3k...", "project_id": "prj_ab12...", "type": "decision",
  "topic": "packaging.asar-pipeline",
  "value": {"statement": "Use the dedup asar packer; never plain @electron/asar pack.",
            "rationale": "Preserves entry counts + integrity fields (V1.1/V1.2 proven)."},
  "summary": "Packaging must use the dedup asar pipeline, not plain asar packing.",
  "source_type": "user_confirmation", "source_ref": "conversation:.../message:...",
  "actor": "user", "trust": 2, "confidence": null, "user_confirmed": 1,
  "status": "active", "source_digest": null, "checked_at": 1789...
}
```

---

## 3. Memory types and structured values

| type | value shape (JSON) | typical source | notes |
|---|---|---|---|
| fact | `{"statement": str, "evidence": str}` | repo/config inspection | verified deterministic only (trust 3) |
| decision | `{"statement": str, "rationale": str, "scope": str}` | user confirmation / accepted work | user-confirmable; conflicts need user choice |
| convention | `{"rule": str, "applies_to": str}` | user / repo evidence | e.g. naming, layout, release rules |
| preference | `{"statement": str}` | user only | **never inferred from weak evidence** (brief rule) |
| command | `{"name": str, "command": str, "cwd": str, "verified_at": str}` | config inspection + user confirmation | carries `source_digest`; goes stale when config changes |
| path | `{"path": str, "role": str}` | repo inspection | role = entry point / core module / test dir etc. |
| component | `{"name": str, "kind": str, "path": str, "summary": str}` | repo inspection + bounded synthesis | architecture building blocks |
| relationship | `{"from": str, "to": str, "kind": str}` | repo inspection | dependency/ownership edges |
| limitation | `{"statement": str, "impact": str}` | user / review evidence | known limits, e.g. single-key reviewer |
| workflow | `{"name": str, "steps": [str], "source": str}` | user / accepted job | candidate recipes reference these |
| question | `{"question": str, "context": str}` | user / model proposal | unresolved items; excluded from "facts" |
| observation | `{"statement": str, "where": str}` | model inference / worker | lowest stored trust; candidate for promotion |

Structured value, not free text: retrieval filters and conflict detection operate on `(type, topic)`
plus the JSON body; `summary` is the presentation form.

---

## 4. Schema (V1.3 migration 001 — additive, idempotent)

All statements are `IF NOT EXISTS`, executed inside the existing store connection bootstrap.
A `schema_migrations` table records what ran (§13).

```sql
CREATE TABLE IF NOT EXISTS schema_migrations(
  version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);

CREATE TABLE IF NOT EXISTS memories(
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  type TEXT NOT NULL,
  topic TEXT NOT NULL,
  value TEXT NOT NULL,
  summary TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_ref TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL,
  trust INTEGER NOT NULL,
  confidence REAL,
  user_confirmed INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active',
  supersedes TEXT,
  superseded_by TEXT,
  source_digest TEXT,
  created REAL NOT NULL,
  updated REAL NOT NULL,
  checked_at REAL
);
CREATE INDEX IF NOT EXISTS memories_by_project ON memories(project_id, status, type, topic);

-- Append-only audit trail (mirrors the jobs/events philosophy: the record table is the
-- projection; the log is the authority for history).
CREATE TABLE IF NOT EXISTS memory_events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT UNIQUE NOT NULL,
  project_id TEXT NOT NULL,
  memory_id TEXT NOT NULL,
  action TEXT NOT NULL,          -- created|updated|confirmed|corrected|superseded|retracted|forgotten|stale|revalidated
  actor TEXT NOT NULL,
  detail TEXT,
  at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_conflicts(
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  memory_a TEXT NOT NULL,
  memory_b TEXT NOT NULL,
  state TEXT NOT NULL,           -- open|resolved
  resolution TEXT,               -- a_wins|b_wins|merged|dismissed|user_choice
  resolved_by TEXT,
  at REAL NOT NULL,
  resolved_at REAL
);
CREATE INDEX IF NOT EXISTS conflicts_open ON memory_conflicts(project_id, state);

-- Optional full-text search (probe at migration; see §9 for the fallback).
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
  topic, summary, value, mid UNINDEXED);
```

Probe note: the migration attempts the FTS table in a try/except; when unavailable the store sets
`fts_enabled=0` in `schema_migrations.note` and retrieval uses a bounded `LIKE` scan (§9).
`memories_fts` is synced explicitly by the store code (insert/update/delete), not by triggers —
deterministic and unit-testable.

---

## 5. Authority model (trust levels)

Authority order (brief-specified; encoded as `trust` 1..7, lower = stronger):

| Level | Label | Source types | Who may assign |
|---|---|---|---|
| 1 | current explicit user instruction | live message (not persisted as authority) | the turn itself |
| 2 | user-confirmed decision/preference | `user_instruction` (on "remember"/confirm), `user_confirmation` | user action only |
| 3 | verified repo/config fact | `repo_inspection`, `config_inspection` | Kel deterministic inspection only |
| 4 | previously accepted project decision | accepted job contracts/milestones | system, on job acceptance |
| 5 | reviewed worker evidence | `worker_evidence` that passed `record_review` | Kel after review recorded |
| 6 | model inference | `model_inference` | Kel (always a proposal; `confidence` set) |
| 7 | untrusted external content | `external_document`, `web` | stored as labeled evidence only |

Promotion rules:
- L6 → L2 only by explicit user confirmation ("this is right / remember this").
- L7 → anything: never automatic. External content can be *cited*; a user decision referencing it
  is stored as a **user decision** (L2) with the citation in `source_ref`.
- L5 records stay L5; the reviewer boundary (`record_review`, executor ≠ reviewer) is the promotion
  gate from raw worker output to stored evidence.
- Preferences (type `preference`) are valid only at trust ≤2; a preference-shaped inference is
  stored as `observation` (L6) and offered to the user for confirmation.

Display rule: every UI view and context packet entry shows the trust label in user words
("you decided", "verified from the repository", "Kel inferred — unconfirmed", "from an external
document"). Deterministic vs inferred is never blurred.

---

## 6. Confidence and evidence labeling

- `confidence` is required for L6 records and free-form for L5; ignored for L1–L4.
- A context packet never presents L6/L7 entries as facts: they carry the literal prefix label
  (`inferred`, `unverified`, `external`) in the composed text.
- `checked_at` is set whenever a digest revalidation passes or a user re-confirms; UI shows
  "checked N days ago" for records older than 7 days.

---

## 7. Lifecycle operations

| Operation | Semantics |
|---|---|
| propose | create an L6 observation or L7 evidence record; never auto-promoted |
| confirm | user marks a proposed record as correct → `user_confirmed=1`, trust→2, event `confirmed` |
| correct | user edit → new record supersedes the old one (chain preserved), event `corrected` |
| retract | user/knowledge owner marks a record wrong → `status='retracted'`, event `retracted`; hidden from retrieval, kept for audit |
| forget | user removes content: `value`/`summary` cleared, `status='retracted'`, record tombstoned; event `forgotten` carries no content |
| supersede (system) | when a higher-authority write targets the same `(type, topic)`: old → `superseded`, `superseded_by` set; both remain inspectable |
| stale (system) | digest mismatch detected during revalidation → `status='stale'`, reason recorded; excluded from context; UI offers refresh |
| revalidate | digest compare against the current project state; updates `checked_at` or flips to `stale` |

Hard rules:
- A record in `superseded`, `retracted`, or `stale` status is **excluded from context composition**
  by default (inspectable in the UI only).
- Deleting history is not allowed except via `forget` (content purge with tombstone).
- `supersedes`/`superseded_by` links always point within the same project.

---

## 8. Conflict rules (explicit, deterministic)

A conflict exists when two `active` records in the same project share `(type, topic)` and their
values contradict (normalized-JSON inequality after semantic normalization of known keys).

Resolution matrix:

| Situation | Resolution |
|---|---|
| Different authority (e.g. L2 vs L3) | higher authority wins; old record superseded; conflict row recorded and auto-resolved `a_wins`/`b_wins` with reason |
| Equal authority, type ∈ {fact, command, path, component, relationship} | newest verified record wins (supersession), conflict recorded resolved `b_wins` |
| Equal authority, type ∈ {decision, preference} | **no auto-resolution**: conflict stays `open`; both records remain active but composer selects the newer one only with an explicit note; user is asked to choose (UI + chat) |
| L6/L7 vs anything | lower-authority record is superseded; if the pair is L6 vs L7 the newer wins; conflicts never silently deleted |
| User explicitly resolves | `resolution='user_choice'`, `resolved_by='user'`; the losing record is superseded (or retracted if the user says so) |

Additional rules:
- Contradictions never auto-merge. (Adapted from pioneer: contradiction never auto-approves even
  with a high score.)
- A conflict on a `decision` that is referenced by a running job raises a visible notice in Work
  context before the next context packet that would use it.
- Conflict records are part of project history and survive across restarts.

---

## 9. Retrieval and selection

Selection API (`kel/memory.py`):

```python
select(project_id, *, purpose, query=None, types=None, topic=None,
       limit=12, max_chars=6000, include_unconfirmed=False) -> list[Record]
```

Ranking: authority (lower trust first) → recency (updated desc) → topic match (FTS rank when
enabled). Deterministic tie-break on id so packet digests are stable.

Exclusions (always): other projects; `status != 'active'`; secret-flagged rows; L7 entries unless
the request explicitly cites external material; superseded/stale/retracted rows.

Bounds: `limit` and `max_chars` enforced in the selector; the composer (§C4) re-applies the global
packet budget. FTS5 when available; otherwise a bounded `LIKE` scan over `topic`/`summary` capped
at 200 candidate rows, with the same ranking.

Purpose parameter ("why is this being retrieved") is recorded per selected record in the context
packet (§C4) so every inclusion is explainable.

---

## 10. Write paths and poisoning defenses

Writer matrix:

| Writer | May create | Cannot |
|---|---|---|
| User (chat / Work context) | decisions, preferences, conventions, questions (L2); corrections/retractions | fabricate facts |
| Kel deterministic inspection | facts, commands, paths, components, relationships (L3, `source_digest` set) | create decisions/preferences |
| Reviewer-approved worker evidence | facts/limitations as L5 | decisions; L2 promotion |
| Model inference | observations (L6) | L2+ writes; preferences |
| External content (README/web/file) | L7 evidence only (verbatim quote + reference) | everything else |

Defenses (each gets a test — see Test Matrix MEM-*):
1. **README/external instructions never become authoritative.** External text is stored as L7
   evidence; imperative content from external documents is quoted, labeled, and requires explicit
   user confirmation to become a decision.
2. **Worker output cannot self-certify.** Raw worker results enter as run artifacts (existing
   inbox); only reviewed artifacts may produce L5 records.
3. **Cross-project leakage blocked at query level.** Every retrieval and every write filters on
   `project_id`; tests assert Project A memory never appears in Project B.
4. **Stale commands lose authority.** `command`/`path` records carry `source_digest`; when the
   underlying config/repo digest changes, revalidation marks them `stale` (excluded from context).
5. **Superseded decisions cannot override current ones.** Composer excludes non-active records;
   conflicts among active records follow §8.
6. **Prompt-injection fences.** Memory text injected into prompts is wrapped in explicit
   provenance fences (adapted from hermes `sanitize_context`: strip fence markers from model
   output so a model cannot forge provenance); external quotes are additionally marked as quotes.
7. **No secrets persisted.** Write-path scanner rejects/redacts secret-like values (API-key shapes,
   `Authorization:` headers, tokens, private key blocks, `.env` values). Redaction policy: refuse the
   write with an explanation; log event without the value. (Test: MEM-09.)
8. **Bounded growth.** Per-project record caps with LRU-on-observations eviction by `status`
   (only stale/retracted eligible); unbounded growth is a test failure of the composer budget test.

Do not persist list (enforced by the scanner + review): API keys, access tokens, passwords,
authentication cookies, private environment values, large raw transcripts, unnecessary source-file
contents.

---

## 11. Store API (`kel/memory.py`)

A single module owning all memory reads/writes; it uses the existing `Store` connection helpers
and writes audit events into both `memory_events` and the existing `events` table
(`aggregate_id = 'memory:' + id`) so memory activity is visible in the same durable log family.

```python
class Memory:
    def __init__(self, store): ...
    def record(self, project_id, type, topic, value, summary, *, source_type, source_ref,
               actor, trust, confidence=None, user_confirmed=0, source_digest=None) -> id
    def propose(self, project_id, type, topic, value, summary, *, confidence, source_ref) -> id
    def confirm(self, memory_id, *, actor='user') -> id          # L2 promotion
    def correct(self, memory_id, *, value=None, summary=None, actor='user') -> id
    def retract(self, memory_id, *, reason, actor='user')
    def forget(self, memory_id, *, actor='user')                 # content purge + tombstone
    def resolve_conflict(self, conflict_id, choice, *, actor='user')
    def revalidate(self, project_id, digest_map)                  # marks stale; never deletes
    def select(self, project_id, *, purpose, query=None, types=None,
               topic=None, limit=12, max_chars=6000, include_unconfirmed=False)
    def conflicts(self, project_id, *, state='open')
    def history(self, memory_id)                                  # full supersession chain
```

All methods validate inputs with `PolicyError` (same pattern as `context.py`), emit events, and
never touch other projects.

---

## 12. Project isolation guarantees

- `project_id` is required on every write and every read; there is no "all projects" query.
- Tests: create identical topic in two projects; assert select() results and conflicts are fully
  disjoint; assert UI list filters per project.
- The context composer additionally asserts packet records only carry one project id (defense in
  depth against future refactors).

---

## 13. Migration plan (V1.3-001)

Follows the existing `kel/migration.py` discipline (idle check → backup → integrity check →
receipt), applied to the current engine version:

1. **Idempotent DDL**: all `CREATE ... IF NOT EXISTS` statements run on store open; re-running is a
   no-op. `schema_migrations` gets one row per applied migration (`version=1`, `name='v13-memory'`).
2. **Backup before first V1.3 mutation**: on upgrade detection (no `schema_migrations` table yet),
   the engine creates `backups/pre-v13-<timestamp>.sqlite3` using SQLite's online backup API
   (same approach as migration.py), runs `PRAGMA integrity_check` on the copy, and writes
   `migration-receipt.json` beside the DB (existing convention).
3. **Old records tolerated**: V1.2 data has no memory rows; new tables simply start empty. No
   existing table is altered; no column is dropped. Existing jobs/conversations/projects/
   approvals/provenance are untouched.
4. **Downgrade/rollback**: because the migration is additive, a V1.2 engine opening the upgraded DB
   continues to work; the extra tables are ignored. This is the documented safe downgrade path.
5. **Precise documentation**: this document plus the migration note row is the schema-change record;
   any future revision increments `schema_migrations.version` and appends a section here.

Failure behavior: if backup or integrity check fails, the engine refuses to run memory features
(tables may exist but remain unusable) and surfaces a clear failure message; the core durable
work loop is unaffected.

---

## 14. User surface (Work context → "Project Knowledge")

Extends the existing Work context drawer; no new dashboard:

- List view: grouped by type; each row shows summary, trust label, age, project; filters
  (type, status, unconfirmed).
- Record view: full value, source reference, supersession chain, conflict links.
- Actions: confirm, correct, retract, forget; conflict resolution prompt when `open` conflicts
  exist; "Why is this here?" shows `source_ref`.
- Proposals: L6 inferences appear in a "Proposed" group with a one-click confirm/correct/discard.
- Empty states explain what memory is and how it is populated. No raw event streams, no internal
  terminology.

---

## 15. Acceptance mapping

All adversarial acceptance items for MEMORY (brief matrix) are mapped to concrete tests in
KEL_V1.3_TEST_MATRIX.md (section MEM-01..MEM-10), including persistence across restart,
provenance correctness, inference trust level, supersession, correction/retraction/forget,
project isolation, secret rejection, and malicious-README defense.

## 16. Explicit non-goals

- No personal/cross-project memory; no cloud sync; no vector store; no embeddings.
- No hidden memory: every record is inspectable; nothing is inferred into authority.
- No memory write path from the ACP transport layer (KellShell) — memory authority lives in the
  Kel engine.
- No automatic recipe/decision extraction from transcripts beyond L6 proposals.

## 17. As-built addendum (Gate 2 implementation, 2026-09-15)

Delivered in `runtime/kel/memory.py`; evidence: `runtime/tests/test_v13_memory.py` (16 tests).
Adjustments recorded against this specification:

1. `memory_events.action` also uses `refused` (secret-like write rejected): `detail` carries only
   the pattern name, never the value. Refusals are mirrored into the durable `events` log so they
   are auditable without content.
2. Explicit replacement supersession runs through `correct()` (user edit); brand-new contradicting
   decisions at equal authority remain open conflicts until `resolve_conflict` — matching §8's
   "no auto-resolution for decisions".
3. `confirm()` refuses trust-7 rows; external content is adopted only by restating it as a user
   decision (citation kept in `source_ref`).
4. Migration receipt handling: an existing `migration-receipt.json` is preserved as
   `migration-receipt-legacy.json` before the V1.3 receipt is written.
5. FTS: capability probe at migration; both paths are exercised in tests; the LIKE fallback is
   deterministic.
6. Decisions at trust 4 are writable only with `source_type='system'` (accepted work), matching
   §5's "previously accepted project decision".
