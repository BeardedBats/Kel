# Kibble Build Update — the authoritative definition and the backend contract (2026-09-21)

**Status of this file:** the durable home of the Build Update definition (recorded from Nick's
session handoff, per D-46) plus the reuse map the backend contract is built on. It corrects the
earlier Priority-9 evidence file, whose “undefined” conclusion was wrong: the name is absent from
this repository's documents, but the feature is not.

## The product definition (authoritative)

Kibble is the **user-facing name for the existing Fix Capture / Dogfood behavior**. Internal
identifiers stay exactly as they are (`dogfood_fixes`, the `Dogfood` class, migration 22
`v20-fix-capture`, the `/api/dogfood` surface, statuses `OPEN / BATCHED / FIXED / DISMISSED`).

The workflow:

1. Nick captures issues in Kibble.
2. Nick selects findings and chooses **Build Update**.
3. Kel creates an **isolated development mission**.
4. A coding runtime repairs Kel's source.
5. Kel runs bounded tests and verification.
6. Kel produces a **separate candidate build**.
7. Nick reviews the result.
8. **Promotion or installation requires explicit human approval.**

### A development mission is existing work machinery carrying

- the selected findings and their screenshot, route, transcript and version context;
- verified repository identity, baseline revision and a bounded source path;
- an isolated development branch/worktree;
- the authorized repair scope;
- coding runtime invocation;
- test and verification requirements.

### A candidate is a reviewable build result carrying

- its source revision and a **separate artifact location**;
- test and verification evidence;
- fixed and unresolved findings;
- known limitations;
- an explicit review and promotion state.

**Build Update authorizes creating and verifying that candidate. It does not authorize installation
or modifying the running app.** Never edit running installed files in place; keep source work, build
output and candidate installation separate. No automatic promotion; no consumer update platform.
`C:\Users\Nick\KelDogfoodCandidate` and `C:\Users\Nick\KelDogfoodRuns\prepared` stay protected.

## The reuse map (measured before building)

| Build Update piece | Existing machinery it rides |
|---|---|
| Findings + context | `dogfood_fixes` (transcript, screenshot, route, page_title, element, window, diagnostics, version, project_id, conversation) and the `Dogfood` class (`list`/`get`/`set_status`/`prepare_prompt`) |
| Development mission | `compile_coding(request, root, tests, project_id, greenfield=False)` → an ordinary job (`kind='coding'`, `root`, `test_command`, milestone checks incl. `manual_review`) created through `Store.create`; the engine claims and dispatches it |
| Isolated worktree | the existing coding snapshot (`repositories/<job_id>`, linked-path refusals, `.env*` skips) — the project's checkout is never edited |
| Coding runtime invocation | the same engine/adapter path every coding job uses (the V2-04a bridge is the pattern for how Kel exposes an action to a runtime/assistant; no second IPC) |
| Tests + verification | `code_evidence` (tests + baseline tests) and `check_evidence() == 'VERIFIED'`; the milestone's `manual_review` rubric |
| Approvals | the existing approval vocabulary (`approvals` rows, resolver restricted to `actor='user'`) |
| Persistence | one additive migration; no second database |
| Review state | explicit and human-only; **Team `promotions`/`shadow` are NOT assumed to satisfy candidate approval** — they are recorded-never-applied queues for other concerns, and the mapping is proved by tests rather than assumed |

## What this file is NOT

- It is not a promise of installation, promotion or an updater (all forbidden).
- It is not the Shell UI contract; the future Build Update UI contract lives in
  `docs/v2/PARALLEL_SHELL_TOUCHES.md`.
