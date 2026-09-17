# In-Chat Approvals — AUTO_RESUME

## Where this sits

V1.6 Phase 3, following Phase 2 artifact lineage (`ffeef73`). Worktree `kel-ux-v15`, branch
`ux/v15-journeys`. Candidate: `dist/package-final16`. Program doc: `docs/v1.6/AUTO_RESUME.md`.

## Done here

- `runtime/kel/chat_approvals.py` (new): conversation-scoped view (`items`), delegating `resolve`,
  `announce_approval`, `announce_denial`, `plain_summary`, `plain_block_reason`, and the
  `approval_announcements` anchor index (core schema, unversioned). Tests:
  `runtime/tests/test_v16_approvals.py` (18).
- `authorize.block_job`: plain pause copy + anchor write in the same transaction as the message.
- `coding.py`: announces each run approval ask once (`announce_approval`).
- `service.py`: `/api/approvals` (GET list + POST resolve; same actor guard as `/api/approval`);
  `/api/autonomy` resolve now also emits the one-sentence denial announcement; `state()` reuses
  `plain_summary`.
- `core.py`: `approval_announcements` DDL; `explain_approval` points at the chat card first.
- Metadata strings made plain (`engine.py`, `coding.py`, `apply_changes.py`, `authorize` defaults).
- Desktop: `KelApprovalCard.tsx` (donor→engine conversation resolution, 3 s poll, submit latch,
  resolved states, Details), `chatLib` `kel_approval` type + MessageList case,
  `KelService` allowlist + idempotent anchor injection in `reconcile()`, message-count added to the
  chat poll fingerprint, Work drawer "Waiting for you" via `/api/approvals`.
- Evidence: engine 592 passed; tsc 0; vitest 76; packaged approvals journey all-green on
  `package-final16`; lineage probe re-pointed to final16 all-green (mirror-pipeline regression).
  Exact results: `docs/in-chat-approvals/00_STATUS.md`.

## Next (Phase 4 — i18n / donor-string cleanup)

Read `docs/v1.6/AUTO_RESUME.md` and continue with Phase 4:

- Audit ALL supported locales and every normal user-facing surface for donor identity (AionUI,
  Butler, stale names), raw translation keys, missing translations, obsolete menu/settings entries,
  stale Autonomy/runtime/worker/lease/scope jargon, inconsistent Kel naming.
- Distinguish required legal attribution (licenses/about) from accidental donor product identity.
- Validate locale catalogs AND rendered packaged surfaces; verify the packaged app.
- Commit/review if material, then continue to Phase 5 (agent-to-model assignments).

## Sharp edges

- Chat must always delegate resolution to the existing functions; never add a parallel decision
  path (the brief's "do not create a second approval system").
- Anchor injection lives in `KelService.reconcile()`; keep it additive + idempotent (id
  `kel-approval-<kind>-<id>`; entries carry `created_at = message_at*1000+1`).
- Mirrored rows carry the DONOR conversation id — the card resolves the engine cid via
  `kelAPI.conversation()` before reading `/api/approvals`.
- System Node cannot load the repo's `better-sqlite3` (Electron ABI) — keep DB assertions in the
  Python verifier (`ux-audit/verify-approvals.py`), not in the Playwright probe.
- Packaged engine must be rebuilt (PyInstaller) AND the app re-packaged when engine sources change;
  the packaged engine hash must match `dist/runtime/KelEngine/KelEngine.exe` for evidence.
