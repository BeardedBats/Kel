# Artifact lineage — where every generated file came from

Status: **implemented and verified** (branch `ux/v15-journeys`; packaged probe green on `package-final15`).

The user-facing promise: every meaningful generated file can answer **"Where did this come from?"** —
project, conversation, the task it belongs to, the request that started it, when it was produced,
and its version history (previous/replacement) — with actions to open it (current or any earlier
version), show it in the folder, and copy its path. Nothing internal is shown in normal UX.

## Entry points

- Engine: `runtime/kel/core.py` — `artifact_lineage` table (created with the core schema, like
  `runs`), `_record_lineage()` (same transaction as the artifact write inside `consume()`),
  `lineage(job_id[, milestone])`, `lineage_artifact(id)` (integrity-checked like the current
  artifact). The current artifact in job data carries `artifact.lineage` (the newest version's id).
- Service: `GET /api/lineage?job=…[&milestone=…]` → `{versions:[…]}` (newest first);
  `GET /api/artifact?lineage=…` → the text of any recorded version.
- Desktop: `KelWorkPanel` milestone rows gain **Where from?** → a modal showing "You asked: …", the
  version list (filename · conversation · project · time · size; current marked), and per-version
  actions **Open / Open this version**, **Show in folder**, **Copy path**. The reveal bridge is
  Kel-native: `kel:artifact-reveal` in `KelService.ts` resolves the store-relative path against the
  engine root (escape-refused) and calls `shell.showItemInFolder`; the preload exposes
  `kelAPI.revealArtifact`. The renderer never builds an absolute path.
- Tests: `runtime/tests/test_v16_lineage.py` (6): full provenance (project/conversation/job/
  milestone/run/filename/digest/turn), tamper refusal, version chaining (v1 fail → v2 pass, previous
  text still readable), renamed filename keeps the chain, job scoping + project resolution,
  job-data round-trip and verification. Packaged probe: `ux-audit/run-lineage-probe.sh`.

## Decisions taken

1. Lineage is recorded **in the same transaction as the artifact itself** (consume), so a lineage row
   can never exist without its file and vice versa.
2. Versions are immutable: replacing a milestone artifact chains `supersedes`/`superseded_by`; old
   rows and files stay, and every version is sha256-checked on read (a changed file is refused).
3. The originating turn is the conversation's user message recorded when the job was created
   (`turn_ref: message:<seq>`), with a text-match fallback for older jobs.
4. Bare engine stores (no `conversations` table) resolve `project_id` to `default` — provenance
   never crashes work on stores that never had conversations.
5. Show-in-folder is main-process work by design; the renderer sends a store-relative path only.

## Evidence (this workstream)

- Engine: full suite **574 passed + 10 subtests** (6 new); tamper/chain/rename/isolation covered.
- Desktop: `bunx tsc --noEmit` 0 errors.
- Packaged (`ux-audit/run-lineage-probe.sh` on `package-final15`, evidence JSON in `ux-audit/runs/lin/out/`):
  the Work panel shows the seeded job; **Where from?** opens the modal with the request, both versions
  (`report.md`, current marked) and the Open / Show in folder / Copy path actions; **Open this version**
  renders the older text (`v1`) in the report drawer; the **reveal bridge** answers `{ok:true}` through
  the main process; `consoleErrors: []`.
- Note for future probes: the report detail renders inside an **open shadow root**
  (`.markdown-shadow`); light-DOM innerText probes are blind to it - read `host.shadowRoot.textContent`.

## Known limitations (v1)

- Work artifacts are text (markdown); non-text artifact types are not produced by the engine today.
- "Open source conversation" is not offered: the modal names the conversation and the request, but
  the engine store id → desktop route mapping is not wired yet (documented, not implied).
- The reveal action opens Explorer selecting the file (human-visible side effect).
- The lineage surface lives in the Work panel next to the artifact buttons; the chat file cards of
  donor-era artifacts are untouched (out of scope for Kel-generated work artifacts).
