# 05 — REMAINING RISKS (Campaign C)

Known external/unchanged gates (not Campaign C work):
1. HUMAN_VISUAL_GATE = PENDING (Nick owns the judgment; automation only).
2. Codex real-provider validation blocked on client version (Campaign B: `gpt-6-astra`).
3. Internal/DeepSeek live-provider validation: no credentials on this machine (synthetic sentinels only).
4. LIM-14 packaged-surfaces evidence class deferred (unchanged from Campaign B).

Campaign C residual-risk notes (appended per finding):
- **AUD-MAJOR-001 (during repair):** adjacent approval surfaces inspected — `/api/state` returns a `PENDING`-approvals array unscoped (read-only display data, no resolution path; unchanged by the narrow repair, flagged for the final re-audit); `/api/autonomy` resolve stays a by-id Work-surface action (no conversation parameter by design; Campaign B reviewed and did not flag it). The resolution authority boundary is the scoped write path.
- **AUD-MAJOR-001 (repaired `44aee9f`):** the two surfaces above were left intentionally unchanged by the narrow ownership repair (read-only display data; Work-surface by-id resolution reviewed by Campaign B); they are carried forward as explicit final-re-audit items.
- **AUD-MAJOR-002 (repaired `eaf7bad`):** the generic `ADAPTER_BRIDGE_EVENT_KEY` dispatcher is retained (donor renderer + WebUI depend on it) and now guarded; pet IPC channels are outside this finding (MINOR-008's disposition). Guard semantics intentionally match the eight previously-guarded channels (top frame of the sending webContents + allow-listed origin schemes); a stricter window-identity check is left for the final re-audit.
- **AUD-MINOR-002 (repaired `7e293ba`):** token/wallclock non-enforcement stays disclosed (`increments/R1-AUTHORITY-CEILING.md`) and is now pinned by a test; run-slot accounting (`job['reserved']`) and planning reservations (`budget_reservations`) remain separate dimensions by design — the envelope aggregates each; the claiming probe confirms actual spend cannot cross the envelope. Reservation write concurrency retains the pre-existing single-writer assumption.
