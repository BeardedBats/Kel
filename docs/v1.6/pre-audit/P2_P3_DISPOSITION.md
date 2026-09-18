# P2_P3_DISPOSITION — every finding, current disposition

updated: 2026-09-18T16:05Z (seed; completed during the P2/P3 sweep phase — sprint directive §40)
The full historic finding set lives in the audit records (`kel-v16-code-audit/docs/code-audit/`,
increments 1–24). This file carries the live disposition table and grows to cover every historic
P2/P3. Campaign B independently re-verifies every disposition; no finding disappears.

Allowed final dispositions: **FIXED · STALE · NOT_APPLICABLE · DEFERRED_NON_RELEASE ·
OPEN_RELEASE_BLOCKER**. Until the sweep sets a final value, rows read `OPEN (sweep pending)`.

## P2 — open at corpus open

| ID | Description (one line) | Severity | Source record | Current disposition | Fix commit | Test | Release relevance | Audit confirm |
|---|---|---|---|---|---|---|---|---|
| APR-01 | `/api/approvals` payload-actor rejection implicit; comment claims a guard that is absent | P2 | `13_PHASE3_DELTA_AUDIT.md`, `17_P1_REMEDIATION_REAUDIT.md` | **FIXED** (2026-09-18, `84b5646`): verification showed the guard **is** explicit — `service._action` raises `PolicyError('Actor identity comes from the authenticated Kel session, not from the request payload')` on the generic path *and* again on `/api/approval` — and the docket's own remedy was a missing **test**, now added (approval route + other action families) | `84b5646` | `tests/test_v16_sweep_fixes.py` (2 new) | none (guard existed; test was the gap) | pending |
| APR-02 | Approval resolution is not conversation-scoped while the read is | P2 | `13_PHASE3_DELTA_AUDIT.md` | **FIXED** (2026-09-18, `8a677d0`): `chat_approvals._require_owned` refuses a resolution whose record's job is not in `_job_ids_for(declared conversation)` — the same ownership set the read path uses — and the desktop now declares its conversation on both resolve call sites. Additive by contract (a caller that declares nothing behaves as before); the digest binding from V1.5 is untouched, and Round 2.5 APPROVAL-EXACT (normalization + pre-execution revalidation) stays with **R4**. Bonus: a latent read-path bug fixed (`_job_ids_for` assumed `job_links` exists) | `8a677d0` | `tests/test_v16_approvals.py` (6 new; full suite 915) | none (scope hardening) | pending |
| APR-03 | `_memory_check_queue` is instance state — queued memory checks lost on crash/restart between commit and flush (`vetting_session.py:95`) | P2 | `13_PHASE3_DELTA_AUDIT.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18: still instance state; Phase 6 reviewed it as a bounded crash-window only, and the durable-drain direction is a feature rather than a release condition) | — | — | none | pending |
| A1 | `engine_version` not validated on the detached-engine reuse path (`KelService.ts:43-52`) | P2 | `15_RUST_LEAD_VERIFICATION.md` | **FIXED** (2026-09-18, `101d8c3`): `engineVersionAccepted(live, expected)` compares the live `/api/state` `engine_version` with the version this build shipped, and the check runs in **both** places that used to trust the answer — the reuse path and the spawn-wait loop (a leftover engine can keep the shared descriptor alive). An unpackaged dev run passes an empty expectation (its `app.getVersion()` is Electron's) and is deliberately not enforced | `101d8c3` | `desktop/tests/unit/kelEngineVersion.test.ts` (3); tsc 0; vitest 93 | none (upgrade-correctness) | pending |
| REL-01 | `freeze-release.ps1` engine staging is a no-op for the path the app loads and the manifest hashes | P2 | `15_RUST_LEAD_VERIFICATION.md`, `17_P1_REMEDIATION_REAUDIT.md` | **OPEN_RELEASE_BLOCKER** (verified open 2026-09-18: `kel-builder.json`/`kel-runtime-builder.json` declare `{"from": "../dist/runtime/KelEngine", "to": "kel-engine"}` — the load path the app stages from (`process.resourcesPath/kel-engine`) — while the freeze tool's staging step does not affect that path, so a freeze can ship an engine older than what `dist/runtime` holds. **Not fixed here on purpose:** the only honest verification is a real freeze, which Campaign A is forbidden to perform; the fix (stage into the packaged `resources/kel-engine` and hash *that*) plus its freeze-level verification belong to the RC gate/human. Mitigation available at RC time: the packaged battery can assert the packaged engine identity without freezing) | — | freeze tooling test (gated) | **release-relevant** | pending |
| SEC-01 | Vetting session actions have no project/conversation ownership check (acceptance criteria recorded) | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | OPEN (sweep pending — verified 2026-09-18 as still open: `vetting_session.Vetting.session(session_id)` loads `WHERE id=?` with no project/conversation filter, and the action methods take only a session id; fix sketch: an ownership parameter on the session/approval lookups rather than a re-check per route) | — | cross-scope session attack | TBD | pending |
| PER-02 | A failed or partial restore is silent (`service.py` swallows `apply_pending_restore`) | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` (Rust-corroborated) | **FIXED** (engine half, 2026-09-18): `backup._record_outcome` writes `restore-outcome.json` beside the data on both decisive paths (the DB is what a restore replaces) and the failure path keeps `restore-pending.json`; `service._restore_outcome` surfaces it as `state()['restore']` — boot never aborts. The renderer surface stays with REQ-ELOSS (audit target 57) | `df1997a` | `tests/test_v16_restore_visibility.py` (5 new; full suite 900) | none (no UI claim made) | pending |
| PER-03 | `.pre-restore-*` snapshots unbounded/never pruned; snapshot failure aborts restore silently | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `84b5646`): `SNAPSHOT_KEEP = 2` + `_prune_snapshots(root)` keep only the newest snapshots and run on **both** the success and the failure path (repeated failed attempts accumulate too); the snapshot the current attempt wrote always survives and pruning is best-effort. The "silently aborts" half was already closed by CHG-007 (recorded + surfaced) | `84b5646` | `tests/test_v16_sweep_fixes.py` (2 new) | none (bounded growth) | pending |
| TR-01 | Transcription `_STREAMS` module-level stream sessions — shutdown/cleanup not reviewed | P2 | `02_FILE_REVIEW_LEDGER.md`, `06_RUNTIME_AND_PROCESS.md` | OPEN (sweep pending — verified 2026-09-18 that it is still module-level: `transcription.py:36` `_STREAMS = {}`, `:528` `self._streams = _STREAMS`; the lifecycle review the finding asks for has **not** been done, so this row stays unverified-clear) | — | shutdown cleanup test | TBD | pending |
| TR-02 | Abandoned-stream UX in the transcription renderer (residual) | P2 | `02_FILE_REVIEW_LEDGER.md` | OPEN (sweep pending — not re-reviewed in batch 3: it is a renderer-UX row and needs a visual pass, which is scheduled with the visual batches rather than guessed at here) | — | renderer state test | TBD | pending |

## P3 — open at corpus open

| ID | Description (one line) | Severity | Source record | Current disposition | Fix commit | Release relevance | Audit confirm |
|---|---|---|---|---|---|---|---|
| APR-04 | `approval_announcements` DDL defined twice, with no migration version | P3 | `13_PHASE3_DELTA_AUDIT.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18: the two blocks are semantically identical — `chat_approvals.py:27-33`, `core.py:157-161`; `IF NOT EXISTS` makes the duplicate inert and there is no schema divergence) | — | none | pending |
| APR-05 | Approvals-arc minor (full text in `13_PHASE3_DELTA_AUDIT.md`; one-line completion during sweep) | P3 | `13_PHASE3_DELTA_AUDIT.md` | OPEN (sweep pending) | — | TBD | pending |
| APR-06 | Approvals-arc minor (full text in `13_PHASE3_DELTA_AUDIT.md`; one-line completion during sweep) | P3 | `13_PHASE3_DELTA_AUDIT.md` | OPEN (sweep pending) | — | TBD | pending |
| DEAD-06 | `packaging/ux-audit.cjs` unwired and misfiled (referenced by nothing outside docs) | P3 | `08_DEAD_CODE.md` | **NOT_APPLICABLE** (verified 2026-09-18: it is the packaged-UI evidence tool — PACKAGED_EVIDENCE_INDEX `package-logo` + phases 6–7 + the visual batches; referenced by the pre-audit corpus, not dead) | — | none | pending |
| CAP2-LONGTEXT | `directive_clauses()` returns `[]` above 2000 chars — reserved directives in long pastes silently ignored (fails safe) | P3 | `19_CAP2_RESIDUAL_REAUDIT.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `capabilities.py:437-448`: >2000 chars → `[]`; the message is forwarded byte-for-byte, so no capability is silently enabled) | — | none | pending |
| INT-01 | Inconsistent sender-frame validation (`kel:artifact-reveal` lacks the check) | P3 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `0596211`): the handler now requires `event.senderFrame === event.sender.mainFrame` and a `file:` URL, byte-for-byte the guard its four siblings carry (verified in `KelService.ts`) | `0596211` | desktop `tsc` 0; no IPC harness exists (audit target §58) | none (parity hardening) | pending |
| PER-04 | `KEL_DATA_DIR` puts `kel-credentials.json` inside the backup root (override path only) | P3 | `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `0596211`): `Backup.create` skips `NEVER_BACKUP = ('kel-credentials.json',)` and reports it in `skipped`/`notes`; the in-database secrets were already stripped | `0596211` | `tests/test_v16_sweep_fixes.py` (2) | none (override-only path, now closed) | pending |
| COR-03 | `KelModelControl.setConversation` has no error path | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| COR-04 | `set_conversation` accepts a non-existent conversation | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `model_prefs.py:107-110`: only non-empty is validated; callers pass the open conversation, and a stranded preference is inert) | — | none | pending |
| COR-05 | `search.py` bare `except` per section | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `search.py:51,72,91`: per-section `except Exception: pass`; fails soft, sections independent, no data loss) | — | none | pending |
| COR-06 | KeyError leaks from vetting/transcription dispatch | P3 | `11_FINDINGS.md` | OPEN (sweep pending) | — | TBD | pending |
| MDL-01 | `set_conversation` accepts a non-existent conversation (with COR-04) | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (same evidence as COR-04) | — | none | pending |
| THM-01 | Theme overrides keyed by theme id survive theme deletion | P3 | `16_FINDING_STATUS.md` | OPEN (sweep pending) | — | TBD | pending |
| SEC-01-multipart | Caller-supplied filename interpolated into a multipart header unescaped (transcription) | P3 | `11_FINDINGS.md` | **FIXED** (2026-09-18, `0596211`): every header parameter now goes through `_header_safe` (CR/LF folded, quotes normalised, backslashes neutralised); a crafted filename can no longer start a header line, and clean names round-trip unchanged | `0596211` | `tests/test_v16_sweep_fixes.py` (3) | none (header-injection hardening) | pending |
| DEAD-05 | `service.py` calls `Vetting` privates (`_questions`, `_format_resurface`) | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `service.py:744-745` still call the privates): internal coupling only — no user-visible effect, and a public wrapper is cosmetic; deferred rather than refactored for its own sake | — | none | none | pending |
| ERR-01 | KeyError leaks from dispatch (with COR-06) | P3 | `11_FINDINGS.md` | OPEN (sweep pending) | — | TBD | pending |

## Closed / retracted in the audited range (for completeness — do not re-open without cause)

- **CAP-01, CAP-02, CAP-03 (P1)** → FIXED (`75d1f68`, `327e5b2`, `631881a`; audits 3–5 CONTINUE).
- **CAP2-CLAUSE / CAP2-RESIDUAL (P1-adjacent)** → FIXED (bracketed clause → reserved `[kel:...]`
  namespace; negative-control discrimination recorded).
- **DEAD-01** superseded; **DEAD-07** superseded; **DEAD-08** FIXED with fail-closed regression.
- **I18N-01** — RETRACTED by the auditor (structurally unobservable; audit 7 self-correction).
- Per-increment F-findings (F1–F23 arcs): closure tables live in the numbered audit records
  `21`–`37`; none remain open except as carried in the rows above (F4/F16-3/F17-4/F18-5/R22-3 are
  carried items with their own dispositions in DEFERRED_ITEMS.md / REQUIREMENTS_TRACEABILITY.md).

## Sweep worklist (sprint §40)

Method: per row, verify the current tree (grep/read) *and* read the source audit record for the
original claim, then set one of the five dispositions with the evidence inline. Rows still reading
`OPEN (sweep pending)` are unverified — they must not be read as cleared.

Progress 2026-09-18 (first batch, verified against the tree):

1. **OPEN** — complete one-line descriptions for APR-05/06: the source record lives in the audit
   worktree `kel-v16-code-audit/docs/code-audit/13_PHASE3_DELTA_AUDIT.md`; read it next.
2. **DONE** — DEAD-06, CAP2-LONGTEXT, APR-04, COR-04, COR-05, MDL-01 dispositioned with inline
   evidence (see the tables above).
3. **OPEN** — still need source-record reads + a decision: P2 = APR-01, APR-02, APR-03, A1, REL-01,
   SEC-01, PER-02, PER-03, TR-01, TR-02; P3 = APR-05, APR-06, INT-01, PER-04, COR-06, THM-01,
   SEC-01-multipart, DEAD-05, ERR-01.
4. **A1 note for the sweep** — `KelService.ts` still reuses a running engine after only
   `JSON.parse(descriptor)` + `/api/state`, with no `engine_version` comparison even though the
   `Descriptor` type carries the field (read 2026-09-18). Fix-or-defer is the sweep's decision; a
   fix needs a desktop test for the stale-descriptor path.
Rules for the rest of the sweep:

- Release-relevant → fix in Campaign A; otherwise DEFERRED_NON_RELEASE with a rationale.
- Every fix gets a test + a CHANGE_LEDGER entry + an updated row here.
- Campaign B re-verifies all rows; discrepancies are findings.
