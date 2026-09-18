# CHANGE_LEDGER — product-behavior changes in the unaudited range

updated: 2026-09-18T16:05Z

Organized by PRODUCT BEHAVIOR, not commits. One entry per behavior change that Campaign A (or the
pending visual integration) delivers. Earlier, already-audited V1.6 arcs are traced in
REQUIREMENTS_TRACEABILITY.md instead — this ledger is what Campaign B must read closely.

Template (all fields required; write `none` explicitly rather than leaving blanks):

```
ID:            CHG-###
Title:
Phase:
User-visible impact:
Internal impact:
Previous behavior:
New behavior:
Primary files:
Primary symbols/functions/classes:
Data/schema changes:
Failure paths:
Security/privacy implications:
Persistence implications:
Expected invariants:        (pointer into INVARIANT_LEDGER.md)
Tests:                      (what proves it, incl. discriminating coverage)
Packaged evidence:          (or `-`)
Known concerns:
Audit questions:            (what should Campaign B attack on this change)
Repair hints:               (pointer into REPAIR_HINTS.md, if any)
```

## Entries

### CHG-001 — Work-panel knowledge actions follow the record's state (+ tombstone placeholder)

ID: CHG-001 · Phase: 6 · Commit: `22f4a3e` · Date: 2026-09-18

- **User-visible impact:** the records list in the Work-panel Knowledge tab shows only actions that
  apply to the record; refused-action errors are no longer reachable; a forgotten record shows
  "Content removed." instead of a blank line.
- **Internal impact:** new pure helper `memoryRecordActions` mirrors the engine guards; the panel
  uses it for the confirm/edit/retract/forget buttons.
- **Previous behavior:** every record rendered all four buttons; the engine refused non-active
  records ("Only an active memory can be corrected/confirmed/retracted") and the error surfaced in
  the panel; forget re-purged tombstones.
- **New behavior:** confirm = active ∧ unconfirmed ∧ 3≤trust≤6; edit = active; retract = active or
  stale; forget = any record except an already-purged tombstone.
- **Primary files:** `desktop/.../chat/KelWorkPanel.tsx`, `desktop/.../kel/memoryRecordActions.ts`,
  `desktop/tests/unit/memory-record-actions.test.ts`.
- **Primary symbols:** `memoryRecordActions`.
- **Data/schema changes:** none.
- **Failure paths:** none added; engine-side refusals remain as defense in depth and are now
  unreachable from these buttons.
- **Security/privacy implications:** none (no capability or scope change).
- **Persistence implications:** none.
- **Expected invariants:** INV-MEM-001; added note — UI guard parity with engine guards.
- **Tests:** 7 unit tests (action matrix); tsc 0; vitest 76→83.
- **Packaged evidence:** — (RC battery asserts the Knowledge tab; recorded gap).
- **Known concerns:** the helper must follow future engine-guard changes (audit target).
- **Audit questions:** can any refused action still be triggered from the UI? Are active-record
  actions unchanged? Does the packaged app render the gated matrix correctly?
- **Repair hints:** `KelWorkPanel.tsx` records map; `memoryRecordActions.ts`.

### CHG-002 — Forget asks for confirmation

ID: CHG-002 · Phase: 6 · Commit: `22f4a3e` · Date: 2026-09-18

- **User-visible impact:** clicking Forget opens a confirmation ("Forget this record? Its saved
  content is removed and cannot be recovered. A blank placeholder stays in the history.") with
  Forget/Cancel; confirming purges as before.
- **Internal impact:** the button is wrapped in an Arco `Popconfirm`; the same `/api/memory`
  action fires on confirm.
- **Previous behavior:** one click purged content irreversibly.
- **New behavior:** two steps; cancel is the default escape.
- **Primary files:** `desktop/.../chat/KelWorkPanel.tsx`.
- **Primary symbols:** records-list render block.
- **Data/schema changes:** none.
- **Failure paths:** none added; errors still surface via the panel's error state.
- **Security/privacy implications:** none; reduces accidental destructive purge.
- **Persistence implications:** none.
- **Expected invariants:** none changed.
- **Tests:** matrix covered by the CHG-001 unit tests; the dialog itself is UI-only (noted).
- **Packaged evidence:** — (RC battery).
- **Known concerns:** dialog copy is English (locale pass owns translations — DEF-013).
- **Audit questions:** verify no bypass path purges without confirmation; verify copy truthfulness.
- **Repair hints:** `KelWorkPanel.tsx` forget button.

### CHG-003 — Capability recommendations (real capabilities, real actions, no nagging)

ID: CHG-003 · Phase: 7 · Commit: `df87903` · Date: 2026-09-18

- **User-visible impact:** when Kel is blocked because a capability is off here, the Work panel
  shows a card: what was paused, why, and Allow once / Enable for this chat / Keep it off. Keeping
  it off changes nothing and dismisses (no re-nag).
- **Internal impact:** new `capabilities.recommendation()` vocabulary; research + coding blocked
  outcomes carry `capability` + `recommendation`; `core` records it on the job milestone (cleared on
  success); `/api/state` carries it to the shell; `KelCapabilityCard` + helpers render/act.
- **Previous behavior:** refusals were a plain sentence; the three actions existed only in the
  Tools control.
- **New behavior:** refusals from the two real effect paths carry the structured recommendation; the
  card renders exactly the engine's actions and nothing else.
- **Primary files:** `runtime/kel/capabilities.py`, `research.py`, `coding.py`, `core.py`;
  `desktop/.../kel/capabilityRecommendation.ts`, `KelCapabilityCard.tsx`, `chat/KelWorkPanel.tsx`.
- **Primary symbols:** `recommendation()`, `capabilityCardActions`, `capabilityActionRequest`.
- **Data/schema changes:** none.
- **Failure paths:** unknown action ids drop; failed API call shows one plain sentence; unavailable
  capabilities produce no card; a live grant suppresses the recommendation.
- **Security/privacy implications:** none added — no state change without the user's action; the
  session-tools gates are unchanged.
- **Persistence implications:** recommendations are milestone data only; nothing new at the policy layer.
- **Expected invariants:** INV-CAPREC-001 (new); INV-CAP-001/002 preserved.
- **Tests:** engine focused 83; engine full 885 (+10 subtests, was 878); tsc 0; vitest 90 (was 83).
- **Packaged evidence:** — deferred (no provider in this environment; LIM-14; audit target 45).
- **Known concerns:** coding-path attachment lacks a dedicated blocked-run test (audit target 44).
- **Audit questions:** can a forged recommendation create a fake action? Does dismissal persist? Does
  the card ever change state without a click?
- **Repair hints:** guard drift vs `capabilities.recommendation`; card request wiring.

### CHG-004 — Canonical Kel logo across every production-reachable branding surface

ID: CHG-004 · Phase: Campaign A branding requirement (Nick directive 2026-09-18) · Commit: branding commit · Date: 2026-09-18

- **User-visible impact:** every mark the user can see is now the exact Nick-supplied folded-ribbon
  K: exe/installer/shortcut icon, taskbar/window, tray + notifications, favicon/apple-touch/PWA,
  login mark, and a new About-screen mark.
- **Internal impact:** `scripts/make-brand-assets.py` derives all sizes from the canonical source
  (sha256-guarded); `resources/app.ico|app.png|app_dev.png|icon.png|app.icns` and
  `public/pwa/icon-180/192/512.png` + the renderer brand mark replace donor art;
  `kel-builder.json` pins the icon per platform/installer and enables `signAndEditExecutable`
  (which also patches the exe icon — it previously never reached `Kel.exe`).
- **Previous behavior:** donor AionUi mark everywhere; the packaged exe carried no patched icon
  (executable editing was disabled).
- **New behavior:** the K everywhere; exe icon verified by extraction from the built package.
- **Primary files:** `scripts/make-brand-assets.py`, `desktop/resources/*` (icons),
  `desktop/public/pwa/*`, `desktop/packages/desktop/src/renderer/assets/logos/brand/app.png`,
  `AboutModalContent.tsx`, `desktop/kel-builder.json`.
- **Primary symbols:** `make-brand-assets.py` (render/write_ico/write_icns); About `brandMark` img.
- **Data/schema changes:** none.
- **Failure paths:** generation refuses a source whose sha256 ≠ canonical (no wrong-image output).
- **Security/privacy implications:** none (static assets).
- **Persistence implications:** none.
- **Expected invariants:** INV-BRAND-001 (new).
- **Tests:** `make-brand-assets.py --check` determinism; tsc 0; vitest 90; packaged exe-icon
  extraction + boot (PACKAGED_EVIDENCE_INDEX `package-logo`).
- **Packaged evidence:** `package-logo`.
- **Known concerns:** dormant NSIS installer text/identifiers and the dead donor `logo.svg` are
  untouched by policy (audit targets 47–49); `package.json` description/author may be intended
  attribution (audit target 49).
- **Audit questions:** any reachable surface still showing the donor mark? Is the 16 px derivative
  legible? Does the extracted exe icon match the shipped `app.ico` frame exactly?
- **Repair hints:** regenerate via the script; the surface table in `docs/v1.6/branding/CANONICAL_LOGO.md`.

### CHG-005 — Record-bound resolution kinds (findings) + additive workforce migration v17

ID: CHG-005 · Phase: Campaign A (audit carry-forward F18-5 / WF-13) · Commit: implementation commit · Date: 2026-09-18

- **User-visible impact:** none directly (learning-loop/review semantics); a finding's resolution is
  now auditable as recorded data rather than inferred text.
- **Internal impact:** `findings.resolution_kind` (additive column, migration **v17**
  `v17-finding-resolution-kind`); `RESOLUTION_KINDS`/`ACCEPTANCE_KINDS` vocabulary;
  `resolve_finding`/`waive_gate` write the kind; `lens_stats` counts by it; `validate_finding`
  validates it; `_is_acceptance` demoted to a legacy-row derivation helper.
- **Previous behavior:** acceptance was inferred from a prefix on the free-text
  `dismissal_reason` (audit F18-5: not record-bound).
- **New behavior:** the recorded kind is authoritative; pre-v17 rows are derived once; the F17-2
  anti-impersonation guarantee (guarded reason markers) is preserved.
- **Primary files:** `runtime/kel/assurance.py`, `runtime/kel/workforce.py`,
  `runtime/tests/test_v16_resolution_kind.py` (new), `runtime/tests/test_workforce_schemas.py`.
- **Primary symbols:** listed above.
- **Data/schema changes:** `findings.resolution_kind TEXT` (nullable), migration v17 with an
  in-place `ALTER TABLE` for existing stores; no row rewritten.
- **Failure paths:** unknown kind → `PolicyError`; pre-v17 row → derived, never an error.
- **Security/privacy implications:** none (no new inputs).
- **Persistence implications:** additive migration, idempotent across reopens.
- **Expected invariants:** INV-RK-001 (new: a resolved status always carries its kind on the guarded
  paths; statistics never require parsing free text).
- **Tests:** `tests/test_v16_resolution_kind.py` (6) + focused suite 136 passed + full suite (A-13).
- **Packaged evidence:** n/a (engine semantics; the RC packaged battery re-runs the engine suite).
- **Known concerns:** prefixes remain in the stored text (deliberate); no per-kind breakdown exposed.
- **Audit questions:** can any path write `dismissed`/`fixed` without a kind? Does a hand-written
  reason change any statistic? Is the v17 ALTER lossless on a populated pre-v17 store?
- **Repair hints:** extend `RESOLUTION_KINDS` + the writers + the migration note together.

### CHG-011 — Approval resolution is conversation-scoped (R0 / APR-02)

ID: CHG-011 · Phase: Campaign A — roadmap R0 (P2/P3 sweep) · Commit: `8a677d0` · Date: 2026-09-18

- **User-visible impact:** none; resolution can no longer settle an item the user is not looking at.
- **Internal impact:** `chat_approvals._require_owned` + `resolve(..., conversation)` scope the write
  path to the same ownership set as the read path; `service._approvals_action` passes the declared
  conversation; both desktop resolve call sites now declare theirs.
- **Previous behavior:** the resolve path settled by `id` alone (the read path was scoped).
- **New behavior:** a declared conversation that does not own the record is refused
  (`That request belongs to another conversation`); an undeclared conversation keeps the old
  behaviour (additive contract).
- **Primary files:** `runtime/kel/chat_approvals.py`, `runtime/kel/service.py`,
  `runtime/tests/test_v16_approvals.py`, `desktop/.../KelApprovalCard.tsx`,
  `desktop/.../KelWorkPanel.tsx`.
- **Primary symbols:** `_require_owned`, `resolve`, `_job_ids_for`, `Service._approvals_action`,
  `KelApprovalCard.act`, `KelWorkPanel.approvalAct`.
- **Data/schema changes:** none. **Failure paths:** refusals are `PolicyError`s on the existing
  route; the item stays pending and resolvable from its own conversation.
- **Security/privacy implications:** closes the release-relevant half of RISK-003 (bare-id
  addressing) for approvals; digest binding unchanged.
- **Persistence implications:** none. **Known concern:** Round 2.5 R4 should make the declared
  conversation mandatory for in-app routes and add normalization/pre-execution revalidation.
- **Expected invariants:** `INV-APPROVE-002` (partial — scope half); `INV-APPROVE-001` untouched.
- **Tests:** 6 new (A-19). **Packaged evidence:** n/a.
- **Audit questions:** can any resolve path still settle without a scope? Does a refused attempt
  ever mutate the record? Is the ownership set identical to the read path's?
- **Repair hints:** `_require_owned` and `_job_ids_for` are the single gates; R4 extends them.

### CHG-010 — Pre-restore snapshots are pruned; the actor-identity guard is pinned by a test

ID: CHG-010 · Phase: Campaign A — P2/P3 sweep · Commit: `84b5646` · Date: 2026-09-18

- **User-visible impact:** indirect — repeated restores no longer leave an unbounded pile of full
  `.pre-restore-*` copies beside the data.
- **Internal impact:** `backup.SNAPSHOT_KEEP = 2` + `_prune_snapshots(root)` (called on the success and
  the failure path); `tests/test_v16_sweep_fixes.py` gains two snapshot-retention tests and two
  payload-actor guard tests.
- **Previous behavior:** every applied *or attempted* restore added a snapshot directory and nothing
  removed them.
- **New behavior:** only the newest snapshots survive; the one the current attempt wrote always does.
- **Primary files:** `runtime/kel/backup.py`, `runtime/tests/test_v16_sweep_fixes.py`.
- **Primary symbols:** `SNAPSHOT_KEEP`, `_prune_snapshots`.
- **Data/schema changes:** none. **Failure paths:** pruning is best-effort and cannot fail a restore.
- **Security/privacy implications:** none. **Persistence implications:** fewer files beside the data.
- **Expected invariants:** INV-PER03-001 (snapshot count stays bounded; the newest is never pruned).
- **Tests:** 4 new (2 retention incl. the failed-restore path, 2 actor guard) + full suite (A-18).
- **Packaged evidence:** n/a. **Known concerns:** retention is a hard-coded default (2).
- **Audit questions:** can a prune delete the snapshot a failed restore needs? (It cannot: the current
  attempt's directory is the newest.) Is the guard checked on every action family that accepts an
  `actor`?
- **Repair hints:** `_prune_snapshots` is the single retention point.

### CHG-009 — Detached-engine reuse validates `engine_version` (audit A1 / ENG-01)

ID: CHG-009 · Phase: Campaign A — P2/P3 sweep · Commit: `101d8c3` · Date: 2026-09-18

- **User-visible impact:** indirect — after an upgrade the app no longer talks to a leftover engine
  of the previous version; it spawns the engine it shipped and waits for that one.
- **Internal impact:** new `engineVersionAccepted(live, expected)` (pure, unit-tested) and the check
  applied at **both** trust sites in `initializeKel` (the descriptor reuse path and the spawn-wait
  loop, which previously connected to whatever answered first).
- **Previous behavior:** `desktop-session.json` + any `/api/state` answer = reused engine.
- **New behavior:** the live `engine_version` must equal the version this build shipped
  (`app.getVersion()` when packaged; `KEL_ENGINE_VERSION` overrides); an unpackaged dev run passes
  an empty expectation and is deliberately not enforced (its `app.getVersion()` is Electron's).
- **Primary files:** `desktop/packages/desktop/src/process/services/kel/engineVersion.ts` (new),
  `KelService.ts`, `desktop/tests/unit/kelEngineVersion.test.ts` (new).
- **Primary symbols:** `engineVersionAccepted`, `initializeKel`.
- **Data/schema changes:** none. **Failure paths:** a stale engine is simply not reused; port
  handling is untouched (each engine picks its own port), so nothing is stranded.
- **Security/privacy implications:** none. **Persistence implications:** none.
- **Expected invariants:** INV-A1-001 (a reused engine is the engine this build shipped).
- **Tests:** 3 desktop unit tests + `tsc` 0 + vitest 93 (A-17).
- **Packaged evidence:** n/a (the RC packaged battery starts the app, which exercises the path).
- **Known concerns:** the end-to-end spawn fallback has no Electron harness here — the decision is
  unit-tested, the wiring typecheck-verified (audit target §59).
- **Audit questions:** can any path still connect to an engine whose version was not checked? Does a
  stale engine keep holding the descriptor file (the loop re-reads it every 250 ms)?
- **Repair hints:** `engineVersionAccepted` is the single decision point.

### CHG-008 — Sweep batch 2: IPC frame guard, multipart header hygiene, credentials excluded from backups

ID: CHG-008 · Phase: Campaign A — P2/P3 sweep · Commit: implementation commit · Date: 2026-09-18

- **User-visible impact:** none intended (three hardening fixes).
- **Internal impact:** the `kel:artifact-reveal` IPC handler now carries the same sender-frame guard
  as its four siblings (INT-01); `_multipart` sanitises every header parameter through a new
  `_header_safe` (SEC-01-multipart); `Backup.create` skips and reports
  `NEVER_BACKUP = ('kel-credentials.json',)` so a `KEL_DATA_DIR` override can no longer put an
  encrypted credentials file inside a backup (PER-04).
- **Previous behavior:** one privileged handler accepted any frame; a crafted upload filename could
  close the header early; the credentials sidecar travelled in backups under the override layout.
- **New behavior:** uniform IPC surface, injection-proof headers, credentials never in a backup
  (reported in `skipped`/`notes`).
- **Primary files:** `desktop/packages/desktop/src/process/services/kel/KelService.ts`,
  `runtime/kel/transcription.py`, `runtime/kel/backup.py`,
  `runtime/tests/test_v16_sweep_fixes.py`.
- **Primary symbols:** listed in the increment record.
- **Data/schema changes:** none.
- **Failure paths:** unchanged (the IPC rejection keeps the `Unknown Kel window` shape).
- **Security/privacy implications:** three fail-closed hardenings; the backup note already promised
  credentials are excluded, and now the sidecar gap is closed too.
- **Persistence implications:** a backup contains one fewer file and says so.
- **Expected invariants:** INV-SWEEP2-001 (a sanitised header parameter can never start a header
  line; no backup contains the credentials sidecar).
- **Tests:** `tests/test_v16_sweep_fixes.py` (5 new) + desktop `tsc` 0 + full suite (A-16).
- **Packaged evidence:** n/a.
- **Known concerns:** the IPC guard has no automated test (no Electron/IPC harness in this repo) —
  verified by typecheck and parity with four sibling guards (AUDIT_TARGETS §58).
- **Audit questions:** can any header parameter reach the socket unsanitised? Is `NEVER_BACKUP`
  consulted on every backup path (including the hot-database copy)?
- **Repair hints:** `_header_safe` for headers, `NEVER_BACKUP` for backup exclusions.

### CHG-007 — A failed or partial restore is recorded and surfaced (audit PER-02)

ID: CHG-007 · Phase: Campaign A — P2/P3 sweep · Commit: implementation commit · Date: 2026-09-18

- **User-visible impact:** indirect — a restore that cannot start or fails halfway is now reported in
  the engine state instead of vanishing; the renderer banner that shows it belongs to REQ-ELOSS.
- **Internal impact:** `backup.OUTCOME` + `_record_outcome(root, ok, detail)` write a sidecar
  (`restore-outcome.json`) beside the data on both decisive paths; `service._restore_outcome` reads
  it and `Service.state()` carries `restore: {ok, detail, at} | null`; the caller records a
  cannot-start failure while still letting boot proceed.
- **Previous behavior:** `service.py` wrapped `apply_pending_restore` in `try/except: pass` and threw
  the boolean away (Rust-corroborated silent failure).
- **New behavior:** the outcome is durable and observable; `False` keeps its old meaning, and the
  pending marker stays in place after a failed attempt.
- **Primary files:** `runtime/kel/backup.py`, `runtime/kel/service.py`,
  `runtime/tests/test_v16_restore_visibility.py`.
- **Primary symbols:** listed above.
- **Data/schema changes:** none (a sidecar file, not a table — the database is what a restore
  replaces, so the record cannot live in it).
- **Failure paths:** recording never raises; a failed restore still returns `False`.
- **Security/privacy implications:** none — `detail` is an exception *type name*, never a message.
- **Persistence implications:** one new sidecar inside the data root.
- **Expected invariants:** INV-PER02-001 (new: a restore attempt's outcome is durable and queryable;
  boot never aborts on a restore failure).
- **Tests:** `tests/test_v16_restore_visibility.py` (5 new) + full suite (A-15).
- **Packaged evidence:** n/a (the RC battery can assert `state()['restore']` on a staged restore).
- **Known concerns:** the renderer does not surface it yet (REQ-ELOSS, audit target 57); PER-03 shares
  the path and stays open in the sweep.
- **Audit questions:** can a restore fail without an outcome record? Is the marker still present after
  a failure? Does `state()` ever report a stale outcome after a later clean start?
- **Repair hints:** recording in `kel/backup.py`, surfacing in `kel/service.py:state()`.

### CHG-006 — Real-artifact binding: closure verifies the artifact the assignment delivered

ID: CHG-006 · Phase: Campaign A (audit carry-forward F4 / audit-scope WF-12) · Commit: implementation commit · Date: 2026-09-18

- **User-visible impact:** none directly (engine closure semantics); a content-bound task can no
  longer be closed on an artifact nothing delivered.
- **Internal impact:** `Store._record_assignment_artifact` binds each landed milestone artifact to
  its assignment in `assignment_artifacts` (the table had a writer and **no reader**);
  `_artifact_violations` verifies ownership at close and, when an `artifact_root` is supplied,
  existence + digest on disk; `_evidence_violations`/`close_d1` carry the optional root.
- **Previous behavior:** the close compared the evidence's artifact digest against the packet's own
  artifact list, so a self-asserted digest satisfied a content-bound contract.
- **New behavior:** the digest must be recorded for the assignment (real delivery), and a declared
  path must exist and hash to the claim when a root is given.
- **Primary files:** `runtime/kel/core.py`, `runtime/kel/delegation.py`,
  `runtime/tests/test_workforce_d1.py`.
- **Primary symbols:** listed above.
- **Data/schema changes:** none (existing `assignment_artifacts` gains its first reader).
- **Failure paths:** refusals join the existing `PolicyError('Evidence-bound close refused: …')`.
- **Security/privacy implications:** none (strictness increases).
- **Persistence implications:** the binding is written inside the consume transaction
  (`INSERT OR IGNORE`, idempotent).
- **Expected invariants:** INV-F4-001 (new: a content-bound close rests on a recorded delivered
  artifact; on-disk binding when a root is supplied).
- **Tests:** `tests/test_workforce_d1.py` (4 new) + full suite (A-14).
- **Packaged evidence:** n/a (engine semantics; the RC battery re-runs the engine suite).
- **Known concerns:** `run_d1` does not pass an `artifact_root` yet; non-content-bound contracts keep
  their previous scope.
- **Audit questions:** can any path write a content-bound close that no delivered artifact backs?
  Does the recorder double-write on re-landing (it must not)?
- **Repair hints:** recorder next to `_record_lineage`; verifier next to `_evidence_violations`.

Planned Phase-to-CHG mapping (kept current as work lands):

| Phase | Expected CHGs | Status |
|---|---|---|
| 6 — memory reality audit + bounded fixes | CHG-001, CHG-002 delivered (`22f4a3e`); audit record `docs/v1.6/phase6/` | DONE |
| 7 — smart capability recommendations | CHG-003 delivered (`df87903`); record `docs/v1.6/phase7/` | DONE |
| 8 — Advanced Worker View decision | none (decision only; FINAL: deferred beyond V1.6 — `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md`) | DONE |
| 9 — Profiles vs Projects decision/fixes | none (decision only; FINAL: no Profiles concept — Projects remain; `docs/v1.6/phase9/PROFILES_VS_PROJECTS_DECISION.md`) | DONE |
| Canonical logo (Nick directive 2026-09-18) | CHG-004 delivered (branding commit); record `docs/v1.6/branding/` | DONE |
| 10 — real provider validation | none (evidence only; PROVIDER_VALIDATION_MATRIX.md) | PENDING |
| 11/12 — Rust freshness / migration | none expected (verification only) | PENDING |
| F4 real-artifact binding wiring | CHG-006 delivered (implementation commit); record `increments/REQ-F4-REAL-ARTIFACT-BINDING.md` | DONE |
| resolution-kind semantics | CHG-005 delivered (implementation commit); record `increments/REQ-RK-RESOLUTION-KIND.md` | DONE |
| P2/P3 sweep | CHG-0xx per fixed finding | PENDING |
| Visual batches 6–8 + integration | CHG-0xx (per batch; see VISUAL_EVIDENCE_INDEX.md) | PENDING |
| Engine-loss/recovery behavior | CHG-0xx | PENDING |
