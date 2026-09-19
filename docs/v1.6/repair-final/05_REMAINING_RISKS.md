# 05 — REMAINING RISKS (Campaign C)

Known external/unchanged gates (not Campaign C work):
1. HUMAN_VISUAL_GATE = PENDING (Nick owns the judgment; automation only).
2. Codex real-provider validation blocked on client version (Campaign B: `gpt-6-astra`).
3. Internal/DeepSeek live-provider validation: no credentials on this machine (synthetic sentinels only).
4. LIM-14 packaged-surfaces evidence class deferred (unchanged from Campaign B).

Campaign C residual-risk notes (appended per finding):
- **AUD-MAJOR-001 (during repair):** adjacent approval surfaces inspected — `/api/state` returns a `PENDING`-approvals array unscoped (read-only display data, no resolution path; unchanged by the narrow repair, flagged for the final re-audit); `/api/autonomy` resolve stays a by-id Work-surface action (no conversation parameter by design; Campaign B reviewed and did not flag it). The resolution authority boundary is the scoped write path.
