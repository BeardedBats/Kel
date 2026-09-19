# 21 — NEEDS YOUR ATTENTION — AUDIT

Audit target `08f56673…`. Surface: `#/work` Needs-Your-Attention section (R9.D; components `KelNeedsAttention.tsx`, `needsAttention.ts`).

## Verified

- **Presence + render (two independent builds):** Campaign A r12-fresh2 probe and the auditor's installed-package probe on the **auditor-built** package both report the section present (`attentionVisible: true`), with 0 console errors, 0 raw leaks, 0 overflow on `#/work`. Screenshots retained (`r12-work.png` in both evidence sets).
- **Derivation (code):** items are derived from engine state (approvals/conflicts/attention-worthy records) via the panel data path; the section adds no authority of its own (render-only surface).
- **Isolation dependence:** each attention item rides the scoping of its source. Memory/vetting/transcription sources are service-enforced (batteries PASS). Chat-approval-sourced items inherit **AUD-MAJOR-001**'s caller-opt-in scoping on the resolve path; the section itself only displays project-scoped data through the panel path.

## Not performed (recorded)

- A dedicated fixture run cross-checking each item type (approve/deny conflict/resolve) against rendered content (accuracy of labels vs underlying rows) was not built this cycle; presence and leak/error checks are the executed evidence.
- No independent cross-project attention-leakage attack beyond the panel/source batteries above.

**Disposition: presence PASS on both builds; accuracy cross-check limited; no new finding; isolation caveat ties to AUD-MAJOR-001.**
