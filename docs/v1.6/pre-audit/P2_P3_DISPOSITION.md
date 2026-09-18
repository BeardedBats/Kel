# P2_P3_DISPOSITION — every finding, current disposition

updated: 2026-09-18 (R9 bookkeeping — denominator reconciliation added; every row carries a final disposition; sprint §40)
The full historic finding set lives in the audit records (`kel-v16-code-audit/docs/code-audit/`,
increments 1–24). This file carries the live disposition table and grows to cover every historic
P2/P3. Campaign B independently re-verifies every disposition; no finding disappears.

Allowed final dispositions: **FIXED · STALE · NOT_APPLICABLE · DEFERRED_NON_RELEASE ·
OPEN_RELEASE_BLOCKER**. Until the sweep sets a final value, rows read `OPEN (sweep pending)`.

**R0 completion (2026-09-18):** this table carries 26 rows (P2 10, P3 16) and all 26 carry a final
disposition — verified by grepping the file for any remaining `OPEN (sweep pending)` row before
commit. REL-01 was the last row to resolve; it is FIXED (`93b99b5`, R8) — see its row.

## Denominator reconciliation — the 27-vs-26 question (R9 bookkeeping, 2026-09-18)

**Determination.** Both **enumerated** slates on disk have always been 26 rows (P2 10, P3 16): this
table, and the independent audit's own reconciled docket (`kel-v16-code-audit/docs/code-audit/`
`AUDIT_STATUS.md` → `p2_open` / `p3_open`, corroborated by `increment-16/review-manifest.md`).
The 27 is **worklist arithmetic**, not an inventory count: **P2 10 + P3 17**. The P3 17 is the
audit material the sprint directive was written against — the increment-1 P3 slate as the audit's
own increment-2 ledger counted it (`12_FINAL_VERDICT.md`: "*+ 14 P3 unchanged from increment 1*")
plus the increment-2 additions `APR-04`/`APR-05`/`APR-06`:

- the 14: `BKP-03, THM-01, MDL-01, SEC-01, SEC-02, ERR-01, ARCH-01, DEAD-01, DEAD-02, DEAD-03,
  DEAD-04, DOC-01, HAR-01, INT-01` — the 11 P3 rows of `11_FINDINGS.md` plus `DEAD-02`–`DEAD-04`
  from `08_DEAD_CODE.md`;
- plus `APR-04`, `APR-05`, `APR-06`.

The frozen 16-row P3 slate = that 17 **minus six** increment-1 entries the audit resolved or
absorbed before its docket froze, **plus five** entries carried under their own IDs that the
worklist count did not include (17 − 6 + 5 = 16). No finding disappears; every original ID below
carries a terminal disposition, re-verified against the tree on 2026-09-18:

| Original ID (as filed) | Terminal state | Evidence (tree-verified 2026-09-18) |
|---|---|---|
| `DEAD-01` | RESOLVED during the P1 remediation arc (audit increment 3 records it; "superseded") | `capabilities._OFF`/`_ON` are absent from the module — the parser is the single source of the directive forms |
| `DEAD-02` | SUPERSEDED by the CAP-01 enforcement rework | `research.py:52-67` passes `capability_for_tool('research')` through `resolve()` before the external request; `EFFECT_KINDS` remains the generic gate's designed vocabulary |
| `DEAD-03` | SUPERSEDED by the same rework | `_TOOL_MAP` is now derived from the capability registry (`capabilities.py:59-62`), never a stale six-tool literal |
| `DEAD-04` | DEFERRED_NON_RELEASE — recorded clean-up note, never a docket row; retained as written ("worth a dedicated clean-up pass, not a V1.6 blocker") | the donor-surface `Navigate` redirect block is still present and reachable by URL (`Router.tsx`, 22 `Navigate` references) |
| `DOC-01` | FIXED within the CAP-02 remediation arc | `directive('web: use default')` is implemented and pinned by the standalone-command corpus (`test_capabilities.py:138,186`) |
| `INT-01` (increment-1 content: hidden donor selector) | NOT_A_DEFECT — filed as an observation in the audit's own ledger ("not a defect"); its ID was re-used by the modern docket for `SEC-02`'s sender-frame content | `AcpModelSelector` is still intentionally mounted with `waitForWarmup` (`ChatConversation.tsx:389-405`) |

The five carried under their own IDs outside the 14+3 count: `COR-03`, `COR-04`, `COR-05`, `COR-06`
(increment-1 `03_CORRECTNESS.md` material — `COR-04`/`COR-05` are near-alias pairs of `MDL-01` and
`ERR-01`, and both IDs are deliberately kept and dispositioned in the table above) and
`CAP2-LONGTEXT` (increment-5 re-audit). The additions are traceability only — **no closed finding
was reopened, and no closed row was changed to fit the count.** No repository evidence revealed a
real gap during this verification.

**Alias map (original ID → canonical row above):** `VET-01`→`SEC-01` · `BKP-01`→`PER-02` ·
`BKP-02`→`PER-03` · `BKP-03`→`PER-04` · `COR-01`→P1 `CAP-02` · `COR-02`→`PER-02` ·
`SEC-01`(inc-1 transcription reading)→`SEC-01-multipart` · `SEC-02`→`INT-01` · `ERR-01`(inc-1
`search.run` reading)→`COR-05` · `ARCH-01`→`DEAD-05` · `HAR-01`→`DEAD-06` · `A1`≡`ENG-01` ·
`A5`≡`REL-01` · `TEST-01`→P1 `CAP-03`.

**Consequence for Campaign B:** the sweep denominator is 26 canonical rows; the original finding
inventory is fully enumerated here (original-ID table + alias map) — accounting for 100% of the
original IDs requires no guessing about which slate a count came from.

## P2 — open at corpus open

| ID | Description (one line) | Severity | Source record | Current disposition | Fix commit | Test | Release relevance | Audit confirm |
|---|---|---|---|---|---|---|---|---|
| APR-01 | `/api/approvals` payload-actor rejection implicit; comment claims a guard that is absent | P2 | `13_PHASE3_DELTA_AUDIT.md`, `17_P1_REMEDIATION_REAUDIT.md` | **FIXED** (2026-09-18, `84b5646`): verification showed the guard **is** explicit — `service._action` raises `PolicyError('Actor identity comes from the authenticated Kel session, not from the request payload')` on the generic path *and* again on `/api/approval` — and the docket's own remedy was a missing **test**, now added (approval route + other action families) | `84b5646` | `tests/test_v16_sweep_fixes.py` (2 new) | none (guard existed; test was the gap) | pending |
| APR-02 | Approval resolution is not conversation-scoped while the read is | P2 | `13_PHASE3_DELTA_AUDIT.md` | **FIXED** (2026-09-18, `8a677d0`): `chat_approvals._require_owned` refuses a resolution whose record's job is not in `_job_ids_for(declared conversation)` — the same ownership set the read path uses — and the desktop now declares its conversation on both resolve call sites. Additive by contract (a caller that declares nothing behaves as before); the digest binding from V1.5 is untouched, and Round 2.5 APPROVAL-EXACT (normalization + pre-execution revalidation) stays with **R4**. Bonus: a latent read-path bug fixed (`_job_ids_for` assumed `job_links` exists) | `8a677d0` | `tests/test_v16_approvals.py` (6 new; full suite 915) | none (scope hardening) | pending |
| APR-03 | `_memory_check_queue` is instance state — queued memory checks lost on crash/restart between commit and flush (`vetting_session.py:95`) | P2 | `13_PHASE3_DELTA_AUDIT.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18: still instance state; Phase 6 reviewed it as a bounded crash-window only, and the durable-drain direction is a feature rather than a release condition) | — | — | none | pending |
| A1 | `engine_version` not validated on the detached-engine reuse path (`KelService.ts:43-52`) | P2 | `15_RUST_LEAD_VERIFICATION.md` | **FIXED** (2026-09-18, `101d8c3`): `engineVersionAccepted(live, expected)` compares the live `/api/state` `engine_version` with the version this build shipped, and the check runs in **both** places that used to trust the answer — the reuse path and the spawn-wait loop (a leftover engine can keep the shared descriptor alive). An unpackaged dev run passes an empty expectation (its `app.getVersion()` is Electron's) and is deliberately not enforced | `101d8c3` | `desktop/tests/unit/kelEngineVersion.test.ts` (3); tsc 0; vitest 93 | none (upgrade-correctness) | pending |
| REL-01 | Freeze staging vs packaged runtime path can diverge (evidence hashes one runtime, the app loads another) | P2 | `13_PHASE3_DELTA_AUDIT.md` | **FIXED** (2026-09-18, `93b99b5`): the divergence was live - `freeze-release.ps1` nested the staged runtime at `resources/kel-engine/KelEngine/...` while the load path kept the package's own engine. The load-path directory is now re-created from the staged runtime and the freeze refuses (SHA-256) a staged copy that did not land, or a package bundling a different engine. Fixture `scripts/validate-freeze.ps1`: positive (freeze + verify against the frozen tree, `OK resources/kel-engine/KelEngine.exe`) and negative (tampered package refused); the frozen load-path engine boots and reports `engine_version 1.6.0` | `93b99b5` | `tests/test_v16_r8_identity.py` (the identity ends are pinned) + the fixture evidence in `increments/R8-PACKAGE-ASSERTIONS.md` | the release freeze itself is a future release step (Campaign A must not perform it); the installer battery re-runs at R12 | pending |
| SEC-01 | Vetting session actions have no project/conversation ownership check (acceptance criteria recorded) | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `49e528e`): `Vetting(store, conversation=…)` carries the acting scope and `session()` — the single load point all by-id actions (ingest/process/finish/help/greybox/apply_pending/_control) already funnel through — refuses a row whose `conversation_id` differs. `panel()` stays the marked display surface (existing `cross_conversation` behaviour preserved). The service builds the Vetting with the conversation it is acting in. Direct callers that declare no conversation are unchanged (additive) | `49e528e` | `tests/test_vetting.py` (7 new: foreign-conversation refusal for every by-id action with the session unchanged, unscoped-instance compatibility, unknown id still null, service-route scope, panel behaviour) | none (scope hardening) | pending |
| PER-02 | A failed or partial restore is silent (`service.py` swallows `apply_pending_restore`) | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` (Rust-corroborated) | **FIXED** (engine half, 2026-09-18): `backup._record_outcome` writes `restore-outcome.json` beside the data on both decisive paths (the DB is what a restore replaces) and the failure path keeps `restore-pending.json`; `service._restore_outcome` surfaces it as `state()['restore']` — boot never aborts. The renderer surface stays with REQ-ELOSS (audit target 57) | `df1997a` | `tests/test_v16_restore_visibility.py` (5 new; full suite 900) | none (no UI claim made) | pending |
| PER-03 | `.pre-restore-*` snapshots unbounded/never pruned; snapshot failure aborts restore silently | P2 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `84b5646`): `SNAPSHOT_KEEP = 2` + `_prune_snapshots(root)` keep only the newest snapshots and run on **both** the success and the failure path (repeated failed attempts accumulate too); the snapshot the current attempt wrote always survives and pruning is best-effort. The "silently aborts" half was already closed by CHG-007 (recorded + surfaced) | `84b5646` | `tests/test_v16_sweep_fixes.py` (2 new) | none (bounded growth) | pending |
| TR-01 | Transcription `_STREAMS` module-level stream sessions — shutdown/cleanup not reviewed | P2 | `02_FILE_REVIEW_LEDGER.md`, `06_RUNTIME_AND_PROCESS.md` | **FIXED** (2026-09-18, `8ab7699`): the lifecycle review the row asked for was performed. Module-level storage is per-process and restart-safe by construction, but a reaped/abandoned stream never released its handle — `_MuseStream._run` blocks on `_queue.get()` until the sentinel, so `_gc_streams()` dropped the entry and left the websocket + reader thread alive. Now: `_MuseStream.close()` (idempotent, non-blocking, safe from the reaper) + `_FixtureStream.close()`; `_gc_streams()` closes before dropping; `stream_finish` closes after finishing. Optional conversation scope added on `_stream`/`stream_chunk`/`stream_status`/`stream_finish` | `8ab7699` | `tests/test_transcription.py` (4 new: over-age stream closed when reaped, finish releases the handle as well as the entry, declared-conversation mismatch refused while undeclared callers keep working, `close()` idempotent + non-blocking) | none (resource lifecycle) | pending |
| TR-02 | Abandoned-stream UX in the transcription renderer (residual) | P2 | `02_FILE_REVIEW_LEDGER.md` | **DEFERRED_NON_RELEASE — bound to R9.A/R10** (reviewed 2026-09-18 against the tree): the backend semantics need no correction and the renderer already handles abandonment honestly — cancel/navigate away stops capture and fires a best-effort `stream_finish`; a stream that died mid-recording is swallowed per chunk (live text is best-effort) and the stop path falls back to `quick_transcribe` over the recorded audio (`KelMicButton.tsx:110-135`, `transcription/index.tsx:228-250`), so the user still gets a transcript. The residual is **transport-failure presentation** (a raw `fetch failed` can reach `Message.error`), which is exactly R9.A batch 6 (failure states / error translation) and R10 (engine-loss/recovery UX) — fixing it here would race the Visual lane for the same files. No false 'implemented UX' claim is made | — | renderer state test (no component-test harness exists — audit target §58) | none (presentation follows R9/R10) | pending |

## P3 — open at corpus open

| ID | Description (one line) | Severity | Source record | Current disposition | Fix commit | Release relevance | Audit confirm |
|---|---|---|---|---|---|---|---|
| APR-04 | `approval_announcements` DDL defined twice, with no migration version | P3 | `13_PHASE3_DELTA_AUDIT.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18: the two blocks are semantically identical — `chat_approvals.py:27-33`, `core.py:157-161`; `IF NOT EXISTS` makes the duplicate inert and there is no schema divergence) | — | none | pending |
| APR-05 | Approvals-arc minor (per-poll DDL fan-out in `chat_approvals.ensure_schema`; full text in `13_PHASE3_DELTA_AUDIT.md`) | P3 | `13_PHASE3_DELTA_AUDIT.md` | **FIXED** (2026-09-18, `dd34ac2`): `MIGRATION_VERSION = 20`; `ensure_schema` early-returns before any DDL once stamped (announcements + sibling ensures + coding tables), and a pre-marker store runs the idempotent body once and is then stamped. The read path (`items()`, polled every 3 s by the approval card) performs no DDL | `dd34ac2` | `tests/test_v16_sweep_fixes.py` (3 new) | none (poll-path work + lock pressure) | pending |
| APR-06 | Approvals-arc minor (card failure message asserts 'already settled' for every failure; full text in `13_PHASE3_DELTA_AUDIT.md`) | P3 | `13_PHASE3_DELTA_AUDIT.md` | **FIXED** (2026-09-18, `594b8b4`): `KelApprovalCard.act()` shows the engine's own sentence when it arrived and says 'Kel could not reach its engine just now, so that decision was not recorded' for a transport failure (fetch/IPC/timeout patterns), never claiming a settlement it cannot know; the 3 s refresh still self-corrects | `594b8b4` | desktop `tsc` 0; vitest 93 (no component harness for this file — audit target §58) | none (decision-surface honesty) | pending |
| DEAD-06 | `packaging/ux-audit.cjs` unwired and misfiled (referenced by nothing outside docs) | P3 | `08_DEAD_CODE.md` | **NOT_APPLICABLE** (verified 2026-09-18: it is the packaged-UI evidence tool — PACKAGED_EVIDENCE_INDEX `package-logo` + phases 6–7 + the visual batches; referenced by the pre-audit corpus, not dead) | — | none | pending |
| CAP2-LONGTEXT | `directive_clauses()` returns `[]` above 2000 chars — reserved directives in long pastes silently ignored (fails safe) | P3 | `19_CAP2_RESIDUAL_REAUDIT.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `capabilities.py:437-448`: >2000 chars → `[]`; the message is forwarded byte-for-byte, so no capability is silently enabled) | — | none | pending |
| INT-01 | Inconsistent sender-frame validation (`kel:artifact-reveal` lacks the check) | P3 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `0596211`): the handler now requires `event.senderFrame === event.sender.mainFrame` and a `file:` URL, byte-for-byte the guard its four siblings carry (verified in `KelService.ts`) | `0596211` | desktop `tsc` 0; no IPC harness exists (audit target §58) | none (parity hardening) | pending |
| PER-04 | `KEL_DATA_DIR` puts `kel-credentials.json` inside the backup root (override path only) | P3 | `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `0596211`): `Backup.create` skips `NEVER_BACKUP = ('kel-credentials.json',)` and reports it in `skipped`/`notes`; the in-database secrets were already stripped | `0596211` | `tests/test_v16_sweep_fixes.py` (2) | none (override-only path, now closed) | pending |
| COR-03 | `KelModelControl.setConversation` has no error path | P3 | `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `594b8b4`): the request is wrapped; the engine's sentence (e.g. 'Open a conversation before choosing its model.') is shown verbatim with a plain fallback for a transport failure, matching `KelToolsControl`; the unhandled rejection is gone | `594b8b4` | desktop `tsc` 0; vitest 93 (no component harness — audit target §58) | none (feedback parity) | pending |
| COR-04 | `set_conversation` accepts a non-existent conversation | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `model_prefs.py:107-110`: only non-empty is validated; callers pass the open conversation, and a stranded preference is inert) | — | none | pending |
| COR-05 | `search.py` bare `except` per section | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `search.py:51,72,91`: per-section `except Exception: pass`; fails soft, sections independent, no data loss) | — | none | pending |
| COR-06 | KeyError leaks from vetting/transcription dispatch | P3 | `11_FINDINGS.md` | **FIXED** (2026-09-18, `5950efb`): `Service._required(data, key, sentence)` replaces direct payload indexing in both dispatch families (session/question/conflict/choice/id/source), and `_vetting_action` now wraps unexpected failures in one plain sentence like `_transcription_action` already did. The same pattern was closed on `/api/retry`, `/api/control`, `/api/apply`, `/api/approval` | `5950efb` | `tests/test_v16_sweep_fixes.py` (3 new: vetting family, transcription family, inline routes — plain sentence + no raw exception string) | none (error-surface honesty) | pending |
| MDL-01 | `set_conversation` accepts a non-existent conversation (with COR-04) | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (same evidence as COR-04) | — | none | pending |
| THM-01 | Theme overrides keyed by theme id survive theme deletion | P3 | `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `594b8b4`): `handleDeleteTheme` drops the deleted theme's override bucket in the same operation (`clearThemeOverrides(themeId)` from `applyTheme.ts`), so a theme re-created with the same id cannot inherit the old colours. Builtin defaults were already never mutated | `594b8b4` | desktop `tsc` 0; vitest 93 (no component harness — audit target §58) | none (stale config rows) | pending |
| SEC-01-multipart | Caller-supplied filename interpolated into a multipart header unescaped (transcription) | P3 | `11_FINDINGS.md` | **FIXED** (2026-09-18, `0596211`): every header parameter now goes through `_header_safe` (CR/LF folded, quotes normalised, backslashes neutralised); a crafted filename can no longer start a header line, and clean names round-trip unchanged | `0596211` | `tests/test_v16_sweep_fixes.py` (3) | none (header-injection hardening) | pending |
| DEAD-05 | `service.py` calls `Vetting` privates (`_questions`, `_format_resurface`) | P3 | `16_FINDING_STATUS.md` | **DEFERRED_NON_RELEASE** (verified 2026-09-18, `service.py:744-745` still call the privates): internal coupling only — no user-visible effect, and a public wrapper is cosmetic; deferred rather than refactored for its own sake | — | none | none | pending |
| ERR-01 | KeyError leaks from dispatch (with COR-06). **Alias note for Campaign B:** `11_FINDINGS.md:23` uses ERR-01 for the `search.run` bare-except claim, which is COR-05 (already DEFERRED_NON_RELEASE); `16_FINDING_STATUS.md:103` and this table bind ERR-01 to the KeyError family. Both descriptions are dispositioned — no reading leaves ERR-01 open | P3 | `11_FINDINGS.md`, `16_FINDING_STATUS.md` | **FIXED** (2026-09-18, `5950efb`) — same fix as COR-06 (shared dispatch contract + tests); the `search.run` reading is COR-05's disposition | `5950efb` | `tests/test_v16_sweep_fixes.py` (3 new) | none (error-surface honesty) | pending |

## Closed / retracted in the audited range (for completeness — do not re-open without cause)

- **CAP-01, CAP-02, CAP-03 (P1)** → FIXED (`75d1f68`, `327e5b2`, `631881a`; audits 3–5 CONTINUE).
- **CAP2-CLAUSE / CAP2-RESIDUAL (P1-adjacent)** → FIXED (bracketed clause → reserved `[kel:...]`
  namespace; negative-control discrimination recorded).
- **DEAD-01** superseded; **DEAD-07** superseded; **DEAD-08** FIXED with fail-closed regression;
  **DOC-01** FIXED (CAP-02 arc), **DEAD-02**/**DEAD-03** superseded by the CAP-01 rework,
  **DEAD-04** DEFERRED_NON_RELEASE, increment-1 **INT-01** NOT_A_DEFECT — all six with tree-verified
  evidence in the denominator reconciliation above.
- **I18N-01** — RETRACTED by the auditor (structurally unobservable; audit 7 self-correction).
- Per-increment F-findings (F1–F23 arcs): closure tables live in the numbered audit records
  `21`–`37`; none remain open except as carried in the rows above (F4/F16-3/F17-4/F18-5/R22-3 are
  carried items with their own dispositions in DEFERRED_ITEMS.md / REQUIREMENTS_TRACEABILITY.md).

## Sweep completion record (sprint §40)

Method: per row, verify the current tree (grep/read) *and* read the source audit record for the
original claim, then set one of the five dispositions with the evidence inline. No row reads
`OPEN (sweep pending)` any more; the string survives only in this documentation.

2026-09-18 — R0 completed the sweep under the marathon directive:

1. **SEC-01** FIXED (`49e528e`) — acting-scope gate on the vetting session load point + service wiring.
2. **TR-01** FIXED (`8ab7699`) — stream handles released on reap/finish; optional conversation scope.
3. **TR-02** DEFERRED_NON_RELEASE, bound to R9.A/R10 (presentation of transport failures only).
4. **APR-05** FIXED (`dd34ac2`) — approvals poll path DDL-free once stamped (migration 20).
5. **APR-06 / COR-03 / THM-01** FIXED (`594b8b4`) — truthful failure messages on the approval card
   and the model pill; theme overrides pruned with the theme.
6. **COR-06 / ERR-01** FIXED (`5950efb`) — dispatch layers answer missing fields with plain sentences
   (`Service._required`), the vetting family wrapped like the transcription family.

Rules for the rest of the sweep (kept for reference):

- Release-relevant → fix in Campaign A; otherwise DEFERRED_NON_RELEASE with a rationale.
- Every fix gets a test + a CHANGE_LEDGER entry + an updated row here.
- Campaign B re-verifies all rows; discrepancies are findings (the 26-vs-27 row count note above is
  deliberately left for that audit rather than silently reconciled).

