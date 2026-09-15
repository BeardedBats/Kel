# 07 — V1.5 Backlog

Planned product evolution and valid post-release work (not release defects). Sources: this audit
(`03` valid-row list, `05`, `06` deferrals) and the release record's own carried items. V1.5 must start
from V1.4.1's documentation truth, so nothing here is misread as V1.4-conformant.

## 1. Finish what V1.4.1 defers (if enforcement wiring is not done there)
- Wire `Autonomy.check` + guardrail evaluation into runner/coding/apply execution boundaries; record
  `guardrail_decisions.rule_id`; make emergency stop fan out to runs and brokers (D-01/D-03).
- Constrain or explicitly re-state native-host containment; consider OS-level sandboxing (see 08).
- Harden approval resolution (interactive binding) and engine-token file ACLs (D-04).
- Implement credential injection so Kel-managed provider keys actually drive live calls (D-05).

## 2. Provider & cost surfaces (ledger 120, 122, 132, 135)
- Test-connection action; subscription-vs-API explainer; per-task budget meter; usage history page.
- Capability-matrix polish on top of the shipped readiness/preset UI.

## 3. Work Center, verification & continuation UX (ledger 043–062, 087–096, 102–113)
- Task timeline; current-step emphasis; compact activity feed; work search/filters; parent-child work
  map; scope chip on the work card; retry/escalation history; stall-detection display; recovery banners.
- Reviewer-independence indicator; evidence-freshness warning; flaky-test indicator; why-uncertain
  explainer; verification history; requirements-coverage matrix; reviewer-rubric viewer.
- Exact provider-session display; continuation history view; recovered-work banner; resume-summary polish.
- Better-with-access card (ledger 007); per-specialist artifact/evidence grouping (ledger 029).

## 4. Memory & context surfaces (ledger 073–075, 082, 195–196)
- Superseded-history view; stale-memory warning; project-isolation indicator; source-mix indicator;
  context-composition and memory-retrieval metric surfaces (engine data already exists).

## 5. Identity, desktop polish & donor sunset (D-06)
- Fix tray tooltip and web-notification title to "Kel"; purge `[AionUi]` logs and donor copy
  (ChannelConflictWarning etc.); retire or clearly mark donor pages (cron/login/TestShowcase); consider
  consolidating the leftover donor settings tabs (model/agent/skills/tools) behind Advanced.
- Local/private indicator; consolidated project switcher (ledger 178, 182).

## 6. Packaging & harness tooling (D-07/D-09/D-10)
- Exclude carried `debug.log` from release folders; hash manifests with filenames + cover donor
  `aioncore.exe` and the docs set; deterministic pet-enable (wait/retry/assert) and a close handshake so
  capture runs stop via the engine rather than the bounded kill.

## 7. Documentation & ledger hygiene (D-08/D-11)
- Advance the 72 already-delivered rows with the citations in `03`; align version strings/labels.
- Fold this audit's findings into the release docs (truthful enforcement scope).
