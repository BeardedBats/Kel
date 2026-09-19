# 10 — APPROVALS / CAPABILITIES

Audit target `08f56673…`. Sources: probe-1 (§A/B/F), probes 2/4 (scoping), code reads, suite re-run.

## Approvals

- **Exact action / job / window / duplicates** (probe-1 §B + suite): declared-foreign resolution refused; window-expired → `EXPIRED` recorded, never approved; second resolution refused; pending never authorizes; remembered grant scoped + revocable (suite). PASS.
- **Conversation scope** — **AUD-MAJOR-001**: resolution scoping is opt-in; an undeclared caller settled a foreign approval (`state: approved`) in the probe; the engine route passes the field through; a dormant `/api/approval` route resolves with no scoping at all. UI call sites (`KelWorkPanel.tsx:275`, `KelApprovalCard.tsx:146`) DO declare the conversation. Repair criteria in `MASTER_FINDINGS.md`.
- **Actor identity** (APR-01): payload-provided `actor` refused on every action family (2 explicit raises + suite). PASS.
- Durable records: UI and runtime use the same `approvals` rows (`chat_approvals` is a view over the durable record; anchors are messages). Reviewed.

## Capabilities

- Unknown capability → REFUSED ("That is not a Kel capability."). PASS. (F1)
- Embedded directive grammar (negative controls): quoted / inline code / fenced code / nested brackets / word-embedded / scheme-URL / unknown capability / malformed state → all inert (no clause found); mixed-case and punctuation-adjacent recognition are **by design** (tests assert them); a bare unquoted path/log-line token containing the exact reserved form DOES parse → recorded as **AUD-SUG-001** (docstring vs behavior precision). 
- Ordinary prose does not mutate state (corpus test re-run; negative controls pass).
- Recommendations (`INV-CAPREC-001`): engine vocabulary + card wiring covered by the green suite and CHG-003 records; the card renders only engine-provided actions (unit-pinned). Packaged card evidence remains deferred (LIM-14) — no new claim made.
- Long-paste guard: `directive_clauses` returns [] above 2000 chars (`capabilities.py:447`) — fail-safe confirmed (CAP2-LONGTEXT disposition stands).

## Cross-checks

- All scoping batteries (memory/vetting/transcription) confirm the same ownership style on their surfaces; the approvals chat path is the outlier recorded as MAJOR-001.
