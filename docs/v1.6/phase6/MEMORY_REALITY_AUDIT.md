# Phase 6 — Memory reality audit (bootstrap §28)

date: 2026-09-18
increment: PHASE6-MEMORY-REALITY
scope (directive §31): controls · reachable UX · persistence · conversation isolation · project
isolation · source/provenance · edits · corrections · forget/delete semantics · scope · stale
memory · hidden behavior · no-op behavior · backend/UI mismatch.
method: source-level reality inventory (engine + renderer, file:line evidence), focused test runs,
packaged-evidence review. Everything below is **parent-executed** evidence unless stated otherwise.
status: COMPLETE — bounded fixes CHG-001/CHG-002 delivered in `22f4a3e`; items with dispositions below.

## 1. Reality inventory

### 1.1 Store & schema (engine)
- `runtime/kel/memory.py` (999 lines): `memories`, `memory_events` (seq audit log + durable
  `events` mirror), `memory_conflicts`; optional FTS5 `memories_fts` with LIKE fallback;
  migration 1 `v13-memory`; migration 15 `v16-memory-proposals` (`memory_proposals` + 2 indexes);
  one backup before the first mutation of existing data on each family; idempotent version checks
  (pinned by test_mem12/13/14).
- Trust ladder 1..7 with hard rules: preferences only from explicit user confirmation; decisions
  only from user confirmation or accepted work; external content always trust 7; inference needs a
  confidence; secret-like values refused (10 patterns); value ≤20KB, topic ≤200 chars,
  summary ≤2000 chars.

### 1.2 Write paths (who creates records)
| # | Path | Entry point | Gate |
|---|---|---|---|
| W1 | Work-panel user action | `/api/memory` confirm/correct/retract/forget → `service._owned_memory` project check → `Memory.*` (service.py:370-381) | user action |
| W2 | Accept a proposal | `accept_proposal` — corrects the existing record or records new knowledge as `user_confirmation`; conflict kind resolves the conflict (memory.py:723-776) | user action |
| W3 | Vetting decisions | `flush_memory_checks` → `propose_change(kind='vetting')` only when a stored rule differs (vetting_session.py:806-850; service.py:682-688) | post-commit drain; idempotent by dedupe key |
| W4 | Open conflict | `record()` when the conflict matrix yields an open pair → `kind='conflict'` proposal (memory.py:400-425) | in-transaction |
| W5 | Source changed | `revalidate()` digest mismatch → `stale` mark + `kind='stale'` proposal (memory.py:865-905) | **no production caller (see MEMR-4)** |
| W6 | Workforce learning | `learning.py:148-153` `record(..., source_type='workforce_*')` | flag `workforce.learning.shadow`, default off; engine-level, no live caller (F16-3) |

### 1.3 Read paths
- **Prompt context**: `Composer._add_memories` (composer.py:60-104) — `select(trust≤5)` by default;
  user-confirmed decisions/preferences always ride (must); open-conflict records are labeled
  "user choice pending"; trust≥6 records appear in the packet's `omitted` list; content is
  provenance-fenced (`<memory-context>`), and model output is sanitized (fence stripping,
  case-insensitive, full-block). `_pack` asserts a memory ref can never cross a project boundary
  (composer.py:204-209).
- **Work panel data**: `/api/work` → `_work()` (service.py:341-362) — records (limit 100, all
  statuses), proposals (open = pending + deferred), open conflicts.
- **History**: `/api/memory action=history` → `history_view` plain-language timeline (memory.py:810-861).

### 1.4 UI surfaces (desktop)
- **Work panel** (`KelWorkPanel.tsx`), mounted at the Sider bottom (Sider/index.tsx:198), drawer
  with tabs; the **Knowledge tab** renders: pending+deferred proposal cards
  (`MemoryProposalReview`), the open-conflict block (keep first / keep second / leave both),
  the records list (with actions), and the "What changed" history. Drawer refresh poll 1.5s;
  trigger at KelWorkPanel.tsx:336. Reachability: confirmed.
- **Chat pill** (`KelMemoryProposalControl`, ChatConversation.tsx:400): pending count + popover
  review card; "and N more waiting for review in Work"; 8s background refresh. As declared in
  `docs/memory-proposals/04_UI_AND_COPY.md`.

### 1.5 What does NOT exist (explicit)
- No chat command that writes memory directly ("remember this" does not exist; v1.3 design keeps
  user instructions turn-scoped — knowledge enters via vetting / proposals / corrections).
- No Settings page for memory; the Work panel is the one knowledge UI.
- No UI path creates a brand-new record from nothing (new knowledge arrives by accepting a
  proposal; edits supersede).
- No reactivation path for a retracted record (engine refuses confirm/correct on non-active;
  retract is one-way; forget purges).
- Proposal kinds `user_change`, `repo_state`, `correction` are accepted vocabulary with **no
  emitters** (only vetting/conflict/stale emit).
- `Memory.propose()` (low-trust helper) has no callers.
- `Memory.revalidate()` has no production caller and no production code populates `source_digest`
  → the stale trigger is engine-ready but unwired (MEMR-4).

## 2. Isolation & persistence — verification

- **Project isolation**: every write goes through `_require_project` + transaction; every read
  filters by `project_id`; service actions verify `_owned_memory` / project ownership before
  touching a record, conflict, or proposal (service.py:370-429); Composer asserts packet refs
  never cross projects. Conversation→project mapping `_project_of` fails closed
  ("Conversation missing", service.py:334-340).
- **Evidence**: `test_v13_memory.py` (mem07 isolation; restart persistence mem01; purge mem06),
  `test_v16_proposals.py` (`test_project_isolation_of_proposals_and_memory`),
  `test_v15_memory_packets.py` (`test_retraction_in_one_project_never_touches_another_packet`).
  Focused run 2026-09-18: **68 passed** (test_v13_memory, test_v15_memory_packets,
  test_v16_proposals, test_workforce_learning).
- **Persistence**: SQLite; backup + migration receipts (mem12/13/14); forget = logical + physical
  purge (secure_delete; FTS row delete + optimize; WAL checkpoint — best-effort under readers)
  with a content-free tombstone + audit event (memory.py:500-522; test_mem06; packets test
  "leaves no bytes or search hits").
- **Packaged evidence (historical)**: `package-final13` memoryprops journey PASS (proposal
  surface). No packaged journey yet exercises the Work-panel Knowledge tab specifically —
  recorded as an RC-battery gap.

## 3. Provenance — verification

- Source types + trust map (memory.py:36-60); preference/decision hard rules in `record()`;
  supersede/conflict matrix incl. `user_confirmed` precedence and open-conflict proposals for
  authoritative pairs; correction chains preserve history (test_mem04); external content can
  never become authoritative (mem09); secrets refused at every write surface with refusal events
  (mem08; proposals secret test). PASS.

## 4. Findings & dispositions

| ID | Finding | Severity | Disposition |
|---|---|---|---|
| MEMR-1 | Work panel offered actions the engine refuses (confirm/edit/retract on superseded, stale, retracted rows) → refused-action errors from the UI | minor (UX truth) | **FIXED** `22f4a3e` — status-aware gating via `memoryRecordActions` + 7 unit tests |
| MEMR-2 | Forget (irreversible content purge) had no confirmation | minor (destructive UX) | **FIXED** `22f4a3e` — Popconfirm before purge |
| MEMR-3 | Forgotten tombstones rendered a blank summary line | cosmetic | **FIXED** `22f4a3e` — "Content removed." placeholder |
| MEMR-4 | Stale-detection trigger is engine-ready but unwired: no production `source_digest` producer, no `revalidate()` caller | informational | **DEFERRED, documented** — DEF-012, LIM-13; audit target added |
| MEMR-5 | Reserved proposal kinds + `propose()` helper without callers | informational | **DOCUMENTED** — reserved vocabulary; audit target: confirm no UX promises them |
| MEMR-6 | APR-03 (vetting→memory check queue is instance state; a crash between commit and flush loses one check silently; the decision itself survives) | P2 (docket) | **CARRY** — sweep item; durable-drain direction recorded in REPAIR_HINTS; not fixed in Phase 6 (phase discipline; needs focused tests) |
| MEMR-7 | New knowledge-UI copy is Kel-native English; translations owned by the release program's locale pass (declared in 04_UI_AND_COPY.md) | release concern | **DEFERRED, documented** — DEF-013, LIM-12; audit target added |

## 5. Bounded fixes delivered (commit `22f4a3e`)

- **CHG-001** — records list actions follow record state (`memoryRecordActions` helper; confirm/edit
  active-only, retract active|stale, forget hidden on purged tombstones) + "Content removed."
  tombstone label. Files: `KelWorkPanel.tsx`, `memoryRecordActions.ts` (new),
  `memoryRecordActions` unit tests (new).
- **CHG-002** — Forget asks first (Popconfirm, irreversible-language copy).
- Verification: `bunx tsc --noEmit` → 0 errors; `bun run test` → **83 passed** (was 76; +7);
  engine untouched (focused memory suite 68 passed pre-change). Packaged verification deferred to
  the RC battery (renderer-only change, no runtime-sensitive surface).

## 6. Hidden-behavior / no-op check summary

- Prompt influence is inspectable (packet sources + omitted list; records visible in the
  Knowledge tab; conflicts labeled). No hidden memory mutations found: every write path is a user
  action, a gated deterministic trigger, or the off-by-default engine-level learning loop.
- No-op surfaces: the six items in §1.5, all with dispositions above.

## 7. Audit targets added

See AUDIT_TARGETS.md "Memory reality (Phase 6 additions)": cross-project id probes across every
memory/vetting/prefs endpoint; correct→supersede chain integrity under iteration; forget on a
conflicted record; proposal dedupe when evidence changes; composer conflict labeling; stale loop
behavior once wired; UI-gating vs engine-guard drift; packaged Knowledge-tab rendering.

## 8. Evidence pointers

- Commits: `22f4a3e` (fixes; FIRST unaudited production commit), `785df71` (corpus entry).
- Commands: engine focused `python -m pytest tests/test_v13_memory.py
  tests/test_v15_memory_packets.py tests/test_v16_proposals.py tests/test_workforce_learning.py -q`
  → 68 passed; desktop `bunx tsc --noEmit` → 0; `bun run test` → 83 passed.
- Code: `runtime/kel/memory.py`, `service.py`, `composer.py`, `vetting_session.py`,
  `desktop/.../KelWorkPanel.tsx`, `KelMemoryProposal.tsx`.
- Docs: `docs/memory-proposals/03_TRIGGERS.md`, `04_UI_AND_COPY.md`, `06_KNOWN_LIMITATIONS.md`.
- Audit docket: `kel-v16-code-audit/docs/code-audit/13_PHASE3_DELTA_AUDIT.md` (APR-03).
