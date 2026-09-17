# In-Chat Approvals — Status

V1.6 Phase 3. Work tree: `ux/v15-journeys` (Kel worktree `kel-ux-v15`). Latest candidate:
`dist/package-final16`.

## What this is

When Kel is waiting on a decision the user can make there and then — access to a folder outside
the repository it was trusted with, or a command it wants to run — the decision card appears **in
the conversation itself**: plain words, "Allow once" / "Allow for this project" / "Deny" (or
"Approve" / "Always allow for this project"), and "Details" for what/why/fallback. The card acts
on the same durable records the Work surfaces already show, and it reads live state, so chat and
Work always agree. Once settled the card stays in history as a sentence — "Allowed once — Kel is
continuing." — never as dead buttons.

## Entry points (read this first)

- Engine view + resolve — `runtime/kel/chat_approvals.py`:
  - `GET /api/approvals?conversation=<id>` lists pending + settled items of both kinds with plain
    fields (`title`, `target`, `what`, `why`, `benefit`, `fallback`, `summary`, `state`,
    `message_seq`/`message_at` for anchoring).
  - `POST /api/approvals {action:'resolve', kind:'access'|'action', id, allow, grant_kind?,
    remember?}` delegates to the EXISTING engines only:
    - access → `Autonomy.resolve_expansion` + `resume_after_grant` (grants) or the one-sentence
      `announce_denial` (denials);
    - action → `Store.resolve_approval` (+ `Context.grant(project, action)` for "Always allow").
  - `/api/approval` and `/api/autonomy` stay as they were for existing surfaces; all paths hit the
    same durable rows (no second approval system anywhere).
- Anchor index — `approval_announcements` (core schema, unversioned like `artifact_lineage`):
  maps `message_seq` to `(kind, ref_id)`. Written in the same transaction as the pause message in
  `authorize.block_job`; coding asks are announced via `chat_approvals.announce_approval` (called
  from `coding.py` right after `request_approval`), one message per distinct ask.
- Pause copy — `authorize.block_job` now posts plain language ("Kel needs your permission to
  continue: … You can decide right in this chat."), with no raw ids and no pointer to the Autonomy
  page. `core.explain_approval` points at the chat card first, the Work drawer second.
- Desktop:
  - `renderer/components/kel/KelApprovalCard.tsx` — the card (poll 3 s while pending; submit latch
    so a double-click cannot resolve twice; `data-testid`s for journeys; Details modal).
  - `common/chat/chatLib.ts` — `IMessageKelApproval` (`type:'kel_approval'`,
    `content:{kind, ref_id}`); `MessageList.tsx` renders the card for it.
  - `process/services/kel/KelService.ts` — allowlist entry `/api/approvals(?conversation=…)`;
    `reconcile()` injects one `kel_approval` entry per announcement (idempotent, additive), so
    cards live where Kel paused — including after restart.
  - `renderer/components/chat/KelWorkPanel.tsx` — "Waiting for you" list for the open conversation,
    reading the same view (plain fields; Allow once / Allow for this project / Approve / Always
    allow / Deny).

## Decisions

- ONE durable engine; the chat is a presentation/action surface. Resolution always runs through the
  same functions Work uses — the double-resolution guards (`Boundary request already resolved`,
  `Run no longer awaits this approval`) are the engine's own.
- Plain language by default: no approval ids, lease ids, scopes, or policy internals in normal
  surfaces; Details deliberately opens what/why/what-approving-allows/if-you-say-no.
- A settled card remains in conversation history as a sentence; a stale (expired/cancelled) ask
  reads "Expired — this request is no longer active." and cannot be approved as if current.
- Denials are respected: no re-ask for the same request (engine `boundary-denied`), one plain
  sentence explains the consequence, and useful state is preserved.
- Task continuation: an "Allow once" grant is consumed at most once by the engine (a spent grant
  fails closed, `grant-used`); "Allow for this project" is the reusable project-scoped grant;
  approval of a run let every surface agree and the run continues.

## Verification (this phase)

- Engine: **592 passed** (`runtime` suite, incl. 18 new tests in `runtime/tests/test_v16_approvals.py`:
  listing/scoping/plain copy, announcement linkage, once/project grants, resume-after-grant,
  denial + no re-ask + one-sentence announcement, approve/deny/expiry/cancelled states, restart
  coherence, service routes, actor-payload refusal). Two wording pins in `test_v15_authorize`
  updated to the new plain copy (behavior identical).
- Desktop: `tsc --noEmit` **0 errors**; vitest **76/76**.
- Packaged candidate `dist/package-final16` (engine rebuilt + electron-builder; packaged engine
  hash equals the fresh `dist/runtime/KelEngine`):
  - `bash ux-audit/run-approvals.sh` — **all legs green** (`ux-audit/runs/appr/out/`):
    - 4 anchored cards render in the conversation; rendered copy contains no ids; zero console errors.
    - Race: double-submit of "Allow once" → one durable resolution (`lease_scope` rows = 1), card
      settles to "Allowed once"; a second resolve attempt is refused by the engine.
    - Chat → allow once: job resumes (`READY/RUNNING`) with the "Permission granted" message; the
      card updates in place.
    - Work → approve: the drawer's "Waiting for you" item resolves the step approval; the chat card
      follows ("Approved"); run state `RUNNING`; drawer item disappears.
    - Expiry: the stale ask shows "Expired" with **no active buttons**; resolve is refused.
    - Restart: after a real app restart the pending card is intact with its buttons; Deny settles
      durably ("Denied"), the engine refuses re-asking, and one plain sentence explains the
      consequence (`deny_message_count = 1`).
  - `bash ux-audit/run-lineage-probe.sh` re-pointed to `package-final16` (mirror-pipeline
    regression): **all flags green** — Where-from modal, 2 versions, folder/copy actions, older
    version opens (shadow text `v1`), `revealOk: ok`, zero console errors.

## Known limitations / boundaries

- Pending approvals created **before** this phase have no anchor entry, so they appear only in the
  Work surfaces (the chat shows the engine's plain message). New asks always anchor.
- Coding asks announce one message per distinct action; repeated identical asks reuse the prior
  approval (existing engine dedupe), so chat does not spam.
- The approvals view returns the most recent 200 items per conversation.
- No live model provider is configured on this machine; the packaged journey drives the real
  durable paths (claim → authorize → request_approval → block_job → resolve → resume) instead of a
  live provider session. Phase 10 covers provider validation when credentials are present.
- `ux-audit/` scripts are scratch tooling outside the repository; the probe's DB checks run in
  Python (`verify-approvals.py`) because the repo's `better-sqlite3` binary is Electron-ABI and
  cannot load under system Node.
