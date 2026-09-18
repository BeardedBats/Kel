# Kel V1.6 — Pre-Audit Evidence Corpus

status: CAMPAIGN_A_IN_PROGRESS
opened: 2026-09-18T16:05Z, at Main HEAD `fd98cc4`
owner: autonomous Main / Program Director (single writer; see AUTONOMOUS_OPERATION.md)
scope: the whole V1.6 declared surface, emphasized on the post-audit range
forward_roadmap: `docs/v1.6/KEL_CANONICAL_ROADMAP_R2_5.md` — adopted 2026-09-18; governs R0–R12
  (Round 2.5 hardening + the remaining Campaign A critical path). Historical phase docs stay as
  evidence; the roadmap governs what happens next.

## Purpose

This corpus exists so a fresh-context auditor — with no access to any chat history — can
systematically inspect 100% of the declared V1.6 scope, and so a subsequent fresh-context repair
agent can systematically resolve every finding that audit accepts.

It is maintained **while** the Campaign A implementation sprint runs, not reconstructed afterwards.

## Program strategy (three campaigns)

- **Campaign A — implementation sprint (current).** Finish the remaining autonomous V1.6
  implementation and produce a PRE-AUDIT RELEASE CANDIDATE. Independent audit cycles are paused;
  ordinary engineering quality control is not (self-review, focused tests, regression, packaged
  verification, atomic commits, records). Stop before release/freeze/tag/human gates.
- **Campaign B — 100% independent audit (future).** A fresh-context auditor consumes this corpus,
  dispositions every declared scope item, and produces ONE master findings ledger
  (`docs/v1.6/audit-final/MASTER_FINDINGS.md`, created by Campaign B, stable IDs
  AUD-BLOCK-### / AUD-MAJOR-### / AUD-MINOR-### / AUD-SUG-###).
- **Campaign C — 100% repair (future).** A fresh implementation agent verifies and repairs every
  accepted finding, adds discriminating coverage, proves closure, updates the master ledger, and
  produces POST_REPAIR_V1_6_HEAD.

## Key program points (repository truth at corpus open)

- **Last genuinely independently audited production point (Main line): `8a2b25d`** — audit
  increment 24 CONTINUE, covering `ba52869..8a2b25d`; cumulative audited coverage from `5e76b21`
  through `8a2b25d` (records `29`–`37` and packages `increment-16`…`increment-24` in the audit
  worktree `kel-v16-code-audit`).
- Docs-only commits above it on `ux/v15-journeys`: `c4ae724`, `5127bac`, `fd98cc4` (no production
  change; verified per-commit).
- **First intentionally unaudited production commit: TBD — it opens with the first production
  commit of Campaign A** and is recorded in `COMMIT_LEDGER.md` when it lands.
- Current Main HEAD at open: `fd98cc4`; remote tip `origin/ux/v15-journeys` = `fd98cc4`; frozen
  refs `v1.5.0` / `v1.6.0-pre1` verified on the remote and byte-untouched locally.
- **PRE_AUDIT_V1_6_HEAD:** to be recorded at the end of Campaign A
  (`docs/v1.6/PRE_AUDIT_RELEASE_CANDIDATE.md`).
- Visual lane: `ux/v16-visual-fix` @ `ac85eb3` (batches 1–5) — automated + packaged acceptance
  only; **not covered by any independent audit**; not yet integrated into Main. Integration is a
  Campaign A goal (§44 of the sprint directive).
- Rust verdict: NO_MIGRATION_NEEDED_NOW (rust-audit worktree at `9c1e7d0`); freshness re-verified
  in Phase 11.
- Baseline at open: engine suite **878 passed (+10 subtests)** at `fd98cc4` (fresh run
  2026-09-18; evidence in `evidence/campaign-a-baseline/`).
- Open docket at open: P2 = APR-01..03, A1, REL-01, SEC-01, PER-02, PER-03, TR-01, TR-02;
  P3 = APR-04..06, DEAD-06, CAP2-LONGTEXT, INT-01, PER-04, COR-03..06, MDL-01, THM-01,
  SEC-01-multipart, DEAD-05, ERR-01.

## Directory map

| Path | Content |
|---|---|
| README.md | this file — strategy, program points, provenance rules |
| AUDIT_SCOPE.md | the declared V1.6 audit surface; every item gets a Campaign B disposition |
| COMMIT_LEDGER.md | every production-affecting commit from the last audited point → PRE_AUDIT_V1_6_HEAD |
| CHANGE_LEDGER.md | product-behavior changes in the unaudited range (CHG-###) |
| REQUIREMENTS_TRACEABILITY.md | requirement → implementation → commit → tests → evidence matrix |
| INVARIANT_LEDGER.md | cross-cutting invariants with code paths, tests, edge cases, audit targets |
| TEST_EVIDENCE_INDEX.md | test runs: command, commit, date, result, count, category |
| PACKAGED_EVIDENCE_INDEX.md | packaged-app proof per build (never confused with source tests) |
| MIGRATION_LEDGER.md | migrations 1..N — schema, fresh/upgrade tests, packaged boot verification |
| PROVIDER_VALIDATION_MATRIX.md | provider/model/runtime validation, incl. AUTO/PREFERRED/FIXED & fallback |
| VISUAL_EVIDENCE_INDEX.md | visual findings, batches, packaged acceptance, human gate status |
| P2_P3_DISPOSITION.md | every historic P2/P3 and its current disposition |
| RISK_REGISTER.md | risks discovered during implementation (not confirmed bugs) |
| DEFERRED_ITEMS.md | deliberate deferments with rationale, impact, revisit conditions |
| KNOWN_LIMITATIONS.md | honest limitations (credentials, environment, human gates) |
| AUDIT_TARGETS.md | adversarial seed list — where Campaign B should attack first |
| REPAIR_HINTS.md | navigation clues for Campaign C (no prescribed fixes without evidence) |
| FINAL_STATE_MATRIX.md | area × verified-state matrix (completed at RC) |
| AUDIT_HANDOFF.md | the Campaign B entry point (finalized at PRE-AUDIT RC) |
| increments/ | one record per substantial increment |
| evidence/ | raw evidence bundles (logs, outputs) grouped by increment/phase |

## Provenance rules

1. Every claim names a commit, a command, a date and an artifact path.
2. Categories are never blurred:
   - **implementation evidence** — produced by the implementer (diffs, records);
   - **self-review** — the implementer's own critical pass;
   - **parent-executed tests** — run by the implementing thread (most of this corpus);
   - **packaged evidence** — produced from a real packaged build;
   - **independent review** — only what a separate fresh-context reviewer produced (audit
     worktree records, review relay). Campaign A records never become "independent" by age.
3. Unknown stays unknown; deferred stays deferred; unaudited stays unaudited.
4. Publication is never verification (GITHUB_SYNC_POLICY.md).
5. Evidence belongs on disk, bounded and referenced — not in chat history.

## How a fresh auditor should use this package

1. Read `AUDIT_HANDOFF.md` (entry point; when finalized it binds PRE_AUDIT_V1_6_HEAD).
2. Walk `AUDIT_SCOPE.md` and disposition every item (PASS / FAIL / PARTIAL / NOT_APPLICABLE /
   NOT_TESTABLE / DEFERRED_WITH_RATIONALE). No scope item may silently disappear.
3. For each commit in `COMMIT_LEDGER.md`, open its increment record and evidence bundle.
4. Challenge every invariant in `INVARIANT_LEDGER.md`, seeded by `AUDIT_TARGETS.md`.
5. File findings in the Campaign B master ledger using the stable ID scheme.
6. Do not implement fixes (that is Campaign C).
