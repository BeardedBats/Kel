# FINAL_STATE_MATRIX — area × verified state (draft; completed at RC)

updated: 2026-09-18T16:05Z
Values: `yes` / `partial` / `pending` / `—` (not applicable). The `independent audit` column is
`PENDING` by design during Campaign A for the unaudited range (Campaign B fills it).

| Area | Implemented | Integrated (Main) | Source tests | Full tests | Packaged test | Real provider | Visual evidence | Human review | Independent audit | Known blocker | Release ready |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Engine core (store/jobs/runs/effects) | yes | yes | yes | yes | partial | — | — | — | covered ≤8a2b25d; pending above | — | pending RC |
| Engine lifecycle (startup/shutdown/restart) | yes | yes | yes | yes | partial | — | — | — | covered ≤8a2b25d | engine-loss UX gap (RISK-001) | pending RC |
| Post-launch engine loss / recovery | partial | partial | partial | partial | repro (probe b) | — | pending | — | pending | findings 16/17 | NO |
| Capabilities (web/files/terminal/github) | yes | yes | yes | yes | yes (p1cap*) | partial (401 wire) | — | — | covered ≤8a2b25d; CAP2-LONGTEXT open | — | pending RC |
| Approvals (in-chat + boundaries) | yes | yes | yes | yes | yes (final16) | — | — | — | covered ≤8a2b25d; APR-01..03 open | APR-02 scope | pending RC |
| Authorization/leases | yes | yes | yes | yes | partial | — | — | — | covered ≤8a2b25d | — | pending RC |
| Memory store | yes | yes | yes | yes | yes (final13) | — | — | — | covered ≤8a2b25d; Phase 6 audit in progress | — | pending RC |
| Memory proposals | yes | yes | yes | yes | yes | — | — | — | covered ≤8a2b25d | — | pending RC |
| Artifact lineage | yes | yes | yes | yes | yes (final15/16) | — | — | — | covered ≤8a2b25d | F4 binding open | pending RC |
| Transcription | yes | yes | yes | yes | yes | — | yes (batch 4) | OPEN | pending | TR-01/02, SEC-01-multipart | pending RC |
| Workforce 5.0–5.6 (schemas→learning) | yes | yes | yes | yes | **assertion pending** | — | — | — | covered ≤8a2b25d | F16-3 no live caller | pending RC |
| Workforce wiring (live product flows) | pending | — | — | — | — | — | — | — | pending | decision pending | NO |
| Routing (AUTO/PREFERRED/FIXED) | yes | yes | yes | yes | partial | partial (401) | — | — | covered ≤8a2b25d | matrix completion | pending RC |
| Providers (4) real validation | pending | yes | yes | yes | partial | **no real success yet** | — | — | pending | Phase 10 | NO |
| Desktop shell (startup, updates, source identity) | yes | yes | yes | yes | yes | — | yes | OPEN | covered ≤8a2b25d | — | pending RC |
| Settings | yes | yes | yes | yes | yes | — | partial (batches) | OPEN | pending (visual) | batch 8 settings half | pending RC |
| Work/Projects/Permissions | yes | yes | yes | yes | partial | — | held (batch 3) | OPEN | covered ≤8a2b25d | — | pending RC |
| Team/Office | yes | yes | yes | yes | partial | — | held (batch 5 team half) | OPEN | pending | — | pending RC |
| Sidebar | yes | yes | yes | yes | yes (visual5) | — | yes (batch 5) | OPEN | pending | integration pending | pending RC |
| Composer / Model / Tools | yes | yes | yes | yes | partial | — | pending (batch 7) | — | covered ≤8a2b25d | batch 7 | pending RC |
| Error translation / failure states | partial | partial | partial | partial | repro | — | pending (batch 6) | — | pending | findings 16/17 | NO |
| i18n (13 locales; donor cleanup) | yes | yes | yes | yes | yes (final17) | — | — | — | covered (audit 7) | — | pending RC |
| Migrations 1–19 | yes | yes | yes | yes | **pending assertions** | — | — | — | covered ≤8a2b25d (14/15); 16–19 pending | packaged assertions | pending RC |
| Packaging / runtime identity | yes | yes | yes | yes | yes | — | — | — | covered ≤8a2b25d | A1/REL-01 open | pending RC |
| Visual integration (batches 1–5 → Main) | no | no | yes | yes | yes | — | yes | OPEN | never audited | not merged | NO |
| P2/P3 sweep | pending | — | — | — | — | — | — | — | pending | docket open | NO |
| Pre-audit corpus itself | yes | yes (this commit) | — | — | — | — | — | — | pending | grows per increment | pending RC |
