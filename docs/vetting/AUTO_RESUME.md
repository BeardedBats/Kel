# Design Vetting Sessions — continuation record

Status: **feature complete and verified (engine 30/30 tests; full suite 475 passed; packaged live pass verified, including the Vetting panel after the renderer-bridge whitelist fix).** Review checkpoint rebuttal supplied with the live evidence. Recorded 2026-09-16.
Next program: resume the User Journey Auditor work from `docs/product/UX_AUTO_RESUME.md` (batch 2).

## Current state

- Branch/worktree: `ux/v15-journeys` @ `C:\Users\Nick\Desktop\Kel\kel-ux-v15` (base commit: see git log;
  this feature is committed as its own commit after the review checkpoint).
- Engine tests: `tests/test_vetting.py` 25/25; whole engine suite green (3 ACP-mock assertions were
  updated to model the vetting probe; re-run recorded in the commit message and evidence).
- Packaged app: `dist/package/win-unpacked` rebuilt with the new renderer **and** the rebuilt
  PyInstaller `KelEngine` (engine rebuild via `scripts/build-runtime.ps1`).
- Live E2E: `packaging/ux-audit.cjs vetting` against the packaged app on the seeded root — results and
  screenshots in `docs/vetting/evidence/` (+ `Kel/ux-audit/runs/vetting`).

## What is done

1. Durable model (migration `v15-vetting`, composite session keys).
2. `VettingAnswerIngestion` — the source-independent understanding service; Path A (typed chat through
   the real ACP host/service) and Path B (direct calls) produce identical snapshots.
3. Chat integration: `start design vetting: …`, rapid answers with one `Recorded: n of m recorded.`
   line each and **no assistant turn**, controls, interruption resurface on every normal-path exit,
   silent ingestion only for answers/controls.
4. Batches: 28-question Product/UI template, 4–9 options per question, `Recommended` only with a
   reason, one open question; dependency-driven adaptation between rounds.
5. Decisions, revisions, conflicts (keep earlier / use newer / show tradeoff / resolve later),
   low-confidence proposals with confirm/correct.
6. Greyboxes: 4–8 deterministic SVG directions biased by answers, comparison in the panel, feedback,
   combination ("Direction 4 → base, …"), pending state that never blocks the batch.
7. Spec snapshots: honest partial specs (resolved/open/deferred/assumptions), accepted in one command.
8. Vetting tab in the Work drawer mirroring the exact API surface.
9. Docs set (this directory) + User Journey rules JR-31..33 with history entries H11..H13.

## What remains / known gaps

- LLM-authored batch customisation is a documented hook, not shipped (deterministic by design).
- Live transcription ingestion is future work; the pipeline is prepared (`source: transcript`,
  proposals, confidence classes).
- Batch and per-answer acknowledgments are stored as short durable messages (see 09_KNOWN_LIMITATIONS.md #3).
- Single template shipped; the engine is template-agnostic.

## Exact next action

1. Independent review: CHALLENGE answered with the live evidence (bridge fix, panel booleans, engine/donor DB records).
2. Commit the vetting feature together with the journey batch-2 fixes (one commit on `ux/v15-journeys`).
3. User Journey batch 2 (O8/O9/O10) implemented, rebuilt, verified live, archived. Program parked at docs/product/UX_AUTO_RESUME.md.
