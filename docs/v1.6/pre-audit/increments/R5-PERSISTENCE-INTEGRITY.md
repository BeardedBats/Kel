# Increment — R5: persistence integrity contract (PERSIST-CANONICAL)

increment_id: V16-R5-PERSISTENCE-INTEGRITY
invariant: **PERSIST-CANONICAL** — only canonical, validated, serializable, reconstructable state may
be durably committed
requirement: `REQ-R25-R5` (roadmap R2.5 §R5; marathon directive §13)
phase: Campaign A — R5
base_commit: `8c899c8`
production_commit: `b2ffed1`
status: complete

## R5.A — durable external input inventory (what reaches the database from outside the engine)

| Ingress | External source | Existing control | Verdict |
|---|---|---|---|
| `submissions` (row + `submission_packets` + `message_files` + a user message) | the renderer/HTTP caller | text type + 1..20000 chars; at most ten attachments; duplicate id returns the same sid; **type check added here** | **FIXED** |
| `inbox` result payloads | worker/broker processes | `isinstance(result, dict)`; `encode(...)`; duplicate id is a no-op; **non-finite payloads now refused** | **FIXED** |
| `effects.receipt` | external effect observation | receipt required; identical re-observation is a no-op, a contradictory one is refused (R2) | SAFE |
| `providers` row `data` (failures/latency/cost/observed_at) | provider processes and the engine's own observation | `provider_outcome` validates shapes; **non-finite reports are now ignored instead of persisted** | **FIXED** |
| `native_progress` / `code_evidence` / `code_workspaces` manifests | the native coding process | manifest digests verified against the workspace before apply; evidence digests re-checked at apply time (`apply_changes.py`) | SAFE |
| Task contracts / CompletionPackets / workforce records | mission workers | `contracts.validate_task_contract` / `validate_completion_packet` / `workforce.assert_safe` (schema, enums, size limits, secret-material refusal) | SAFE |
| Memory proposals / memories | model-authored proposals | `memory` schemas + `scan_secret` + provenance; proposals are never auto-applied | SAFE |
| Artifacts (`artifacts/…` files) | run outputs | explicit 1 MiB cap enforced before any write | SAFE |
| Transcripts/attachments | user files | base64 decode validation, mime/size handling in the transcription path | SAFE |
| Restore records / backup receipts | the backup subsystem | `restore-outcome.json` + durable state; PER-02 visibility | SAFE |
| Events / aggregate revisions | the engine | `UNIQUE(aggregate_id, revision)` + optimistic `revision` check (R2 matrix) | SAFE |

## The contract itself (what was missing)

`core.encode` is the single serialization door for durable JSON, and it allowed Python's
non-standard `NaN`/`Infinity` tokens: `json.loads` reads them back as non-finite floats, and any
strict JSON consumer (the desktop renderer's `JSON.parse`, an external tool reading a packet) cannot
parse them at all. That is exactly the "not reconstructable" class the invariant forbids, and because
`digest()` is built on `encode`, it also made digests implementation-defined.

Repairs (smallest correct):

1. `core.encode`: `allow_nan=False`, with a plain refusal sentence
   ('A value that cannot be stored in canonical JSON (NaN or Infinity) was refused').
2. `core.provider_outcome`: ignore non-finite `duration`/`cost_usd` reports (still record the
   failure itself) — so the new refusal can never lose a legitimate observation.
3. `Service.submit`: check `text` is a string *before* `.strip()`, so a malformed request answers in
   the intended plain sentence instead of an `AttributeError`.

No storage rewrite, no new layer, no migration (the directive's R5 "do NOT rewrite SQLite" honoured).

## Attacks exercised (R5.C / R5.D)

`tests/test_v16_r5_persistence.py` — **7 new**:

1. Non-finite values refused at `encode` (bare and nested).
2. Ordinary values stay canonical (sorted keys, compact separators, unicode preserved).
3. A malformed worker result (NaN member) is refused and **no inbox row** exists; the same
   connection then accepts a well-formed result.
4. A non-object worker result is refused with a plain sentence.
5. A nonsense provider report leaves the provider state finite while the failure is still recorded.
6. An oversized artifact is refused *before* any file is written.
7. A malformed request type and an over-long request answer in plain sentences with **no
   half-written submission or message row** (before/after counts equal).

Focused: R2–R5 suites + `test_core` = **84 passed**. Full engine: TEST_EVIDENCE_INDEX A-24.

## Limitations / audit questions / repair hints

- Malformed *stored* JSON (a row corrupted outside Kel, e.g. hand-edited SQLite) is not covered:
  readers such as `Providers._row` call `json.loads` directly. Recorded as an audit question rather
  than invented behaviour (a repair would need a product decision about surfacing corruption).
- `add_message` has no length cap (trusted internal writers only); the user-facing ingress is capped
  at 20 000 chars.
- UTF-8 artifact boundaries are enforced at 1 MiB per artifact (bytes, not characters).
- Audit questions: (a) are there any remaining `json.dumps` call sites outside `encode` that write
  durable state? (b) does any test fixture store non-finite floats today (none found)? (c) should
  `encode`'s refusal also apply to *derived* metrics that a provider could poison (latency/cost are
  guarded; scores are engine-computed integers)?
- Repair hints: none open from this increment.
