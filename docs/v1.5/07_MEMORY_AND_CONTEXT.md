# 07 — Memory and Context (Kel V1.5, G6 audit)

Status: **audited + one real gap fixed** — the memory store was already deep (MEM-01..15); this
gate proved the user-visible lifecycle end to end and closed the one residue it exposed.

## What exists and is proven (source-traced)

| Property | Mechanism | Evidence |
|---|---|---|
| Provenance | `source_type` (trust ladder) + `source_ref` + `source_digest` on every record | `test_v13_memory` MEM-02 |
| Trust | 1..7 trust from source; inference stays lower trust; preferences only from explicit user confirmation | MEM-03, `record` validation |
| Correction | `correct()` supersedes with history (new record + superseded link) | MEM-04 |
| Conflict resolution | open conflicts recorded; `resolve_conflict` (a/b/dismiss), loser superseded with a link | `test_v13_memory`, `test_v13_composer` CTX-04 |
| Scope | every record and read is project-scoped (`_require_project`, project_id in every query) | MEM-07, CTX-07 |
| Freshness | `revalidate()` compares source digests; changed sources mark stale; stale excluded from selection but visible in `records(status='stale')` | MEM-10 + G6 probes |
| Retract / forget | retract keeps content but excludes it; forget purges content and keeps a content-free tombstone + audit event | MEM-05/06 + G6 probes |
| Activity | append-only `memory_events` (recorded/corrected/retracted/stale/revalidated/forgotten/superseded) | MEM-15 |
| Context packets | `Composer` selects active memories, surfaces conflicts, bounds budget, persists packets, strips fence markers | CTX-01..09 |

## The G6 gap that was found and fixed

The new packet-lifecycle probes (`test_v15_memory_packets.py`) scan the store's durable bytes after
`forget`. The first run found the marker still present: the logical purge was correct, but freed
SQLite cells, WAL frames, and FTS index internals could retain the old value. Fix (all three):

1. `PRAGMA secure_delete=ON` on every engine connection — freed cells are zeroed as they are freed;
2. `forget` merges the FTS segments (`'optimize'`) after deleting the row;
3. `forget` checkpoints the WAL (`TRUNCATE`) so pre-forget pages are not retained (best effort
   under concurrent readers — the logical purge is already durable).

Verified by `test_v15_memory_packets.py` (4/4): retracted memory leaves the packet; stale memory
leaves the packet and stays inspectable; forgotten content leaves zero bytes and zero search hits;
one project's retraction never touches another project's packet.

## Deliberately out of V1.5 scope (honest)

- **Global (cross-project) memory** does not exist: memory is project-scoped only. This keeps the
  V1 product promise ("one assistant", not a personal-life OS); V2+ may revisit.
- The four memory *surfaces* (superseded history view, stale warning, isolation indicator,
  source-mix indicator — ledger V14-073/074/075/082) are desktop work; the engine data they need is
  live as of V1.3/G6. They are tracked with the G7 desktop program.
