# 02 — SECURITY AUTHORITY (final re-audit)

Independent replay of AUD-MAJOR-001 and AUD-MAJOR-002 against the fixed production tree
(`7cf6030`; production tree == `05a076b`). All attacks are first-party reproducers written for
this audit (`probes/ra_attack_engine.py` plus a desktop mutation replay), not Campaign C's pass
claims. Raw output: `evidence/ra-attack-major1.txt`, `evidence/ra-negctl-desktop-mutation.txt`.

## AUD-MAJOR-001 — approval conversation ownership

Original defect (Campaign B): the resolution path was conversation-scoped only when the caller
declared a conversation; an omission settled any conversation's approval, and the legacy
`/api/approval` route had no ownership check at all.

Repair reviewed (`44aee9f`): `chat_approvals.require_owned` made unconditional with omission ->
`'main'` (read-path parity); the legacy singular route calls the same predicate first.

### Attack battery (all first-party, fresh temp stores; 24 checks, 0 failed)

| # | Attack | Expected | Observed |
|---|---|---|---|
| A1 | foreign record, conversation omitted | refuse | refused: "That request belongs to another conversation" |
| A2 | foreign record, `conversation='main'` declared | refuse | refused (same sentence) |
| A3 | owner declares its own conversation | settle | `approved` (feature intact) |
| A4 | main-owned record, omitted | settle (parity) | `approved` |
| A5 | malformed spellings: dict / list / `123` / `'MAIN'` / `' main'` / `''` / `0` / NUL / trailing-space on a foreign record | all refuse | all refused; record untouched |
| A5b | same record after the attacks, owner declares | settle | `approved` |
| A6 | unknown `kind` | refuse | "Approval request missing" |
| A7 | missing id | refuse | "Approval request missing" |
| A8 | duplicate resolve | refuse, record intact | "Approval does not match this action"; status stays `APPROVED` |
| A9 | sibling job in the SAME conversation | settle (conversation is the boundary; by design) | `approved` |
| A10 | expired approval resolved `allow=True` | never approve | recorded `expired` (not approved; run cancelled) |
| A11 | approval row with `job_id NULL` | refuse | "Approval request missing" |
| A12a/b/c | boundary grant (access kind): foreign omission / declared-main / owner | refuse / refuse / settle | refused / refused / `allowed_once` |
| B1–B4 | `/api/approvals`: owner; wrong conversation; omission on foreign; omission on main | settle; refuse; refuse; settle | `approved`; refused; refused; `approved` |
| B5a/b/c | legacy `/api/approval`: omission on foreign; declared-main; owner | refuse; refuse; settle | refused; refused; `{'status': 'APPROVED'}` |

**Verdict: VERIFIED_CLOSED.** The same scenarios fail on the pre-fix base (negative control:
4 `CrossScopeResolutionTests` + the legacy-route test fail at `a349009` —
`evidence/ra-negctl-engine-prefix.txt`).

### Recorded adjacent surfaces (determination, not assumption)

- `/api/state` read list (B6): returns **all** PENDING step approvals regardless of the requested
  conversation (id + action + job_id reachable from any conversation's state call). Read-only;
  every settlement route now demands declared ownership. Determination: acceptable information
  exposure within the single-user local trust domain; **no mutation/ownership bypass**. Risk noted.
- `/api/autonomy` by-id resolution (B7): reproduced — a boundary request can be settled by id with
  no conversation parameter at all (`{'action':'resolve','request_id':...}` -> `GRANTED`; the ids
  come from the unscoped `requests` listing). Determination: this is the Work surface's deliberate
  by-id API, not a hole in the repaired chat-path invariant. A caller able to reach the service can
  already settle via the chat route by *declaring* the owning conversation — the declaration is a
  scope assertion, not an authenticated identity — so the autonomy path adds no capability beyond
  the documented declared-scope model. Recorded as an observation + documentation recommendation
  (name the Work-surface exception in the invariant). Not a regression; not release-blocking.
- Legacy reader path (`approval_actions` join) cannot reach access-kind grants or null-job rows
  (A11/B5) — fail-closed.
- `store.resolve_approval` primitive caller map: chat resolve (guarded), legacy route (guarded),
  coding-adapter expiry deny (its own run, deny direction) — no unguarded external path.

## AUD-MAJOR-002 — privileged IPC sender validation

Original defect (Campaign B): guard coverage was non-uniform; only 8 Kel channels validated the
sender; the credential trio, the feedback pair, the backend-startup sync handlers, the recovery
channel and the generic donor-bridge dispatcher accepted any sender; subframes inherit the preload.

Repair reviewed (`eaf7bad`): one shared fail-closed primitive (`common/senderGuard.ts`) applied to
every privileged registration; per-channel semantics match the previously guarded ones
(`file:` only, or `file:` + `http://localhost:` only where the channel previously allowed dev).

### Independent enumeration (HEAD) — every `ipcMain.*` registration in the shipped tree

| Module | Channels | Guard |
|---|---|---|
| `common/adapter/main.ts` | `ADAPTER_BRIDGE_EVENT_KEY` (carries ALL donor-bridge provider calls) | `assertTrustedSender` (allowDevServer) |
| `process/bridge/feedbackBridge.ts` | `feedback:renderer-log`, `feedback:collect-logs`, `feedback:capture-screenshot` | soft / assert guard |
| `process/services/kel/kelCredentialIpc.ts` | `kel:credential-status|set|delete` | `assertTrustedSender` (allowDevServer) |
| `process/services/kel/KelService.ts` | `kel:conversation|history-search|history|request|engine-state|engine-retry|diagnostics|artifact-reveal` | `assertTrustedSender` (policy parity per channel) |
| `process/startup/backendStartupIpc.ts` | 4 sendSync handlers + `backend:recover-corrupted-database` | refuse -> `null` / `assertTrustedSender` |
| `process/pet/*` | 9 pet channels | **not registered** while `KEL_PET_SUBSYSTEM_ENABLED === false`: `registerIpcHandlers()` is called only inside `createPetWindow`, which returns early; `setPetEnabled` refuses; the startup gate is doubly off — unreachable |

No other `ipcMain` registration exists anywhere in the shipped tree (whole-tree scan). The donor
provider surface is transported by the single dispatcher channel — one guard covers it. The WS/CDP
bridges are separate transports with their own documented trust model (noted in `06_ADJACENT_RISK.md`).

### Attack replay and discriminating proof

- The suite's channel-level test (`tests/unit/ipc-sender-channels.test.ts`, 18 tests) exercises:
  untrusted subframe, foreign origin, missing `senderFrame`, missing `sender.mainFrame`, a frame
  without url, alternate renderer, and the legitimate main frame — for the credential trio, the
  feedback trio, the sendSync set, the recovery channel and the generic dispatcher. All present in
  the passing 152/152 desktop run (this audit re-ran the full suite in the audit worktree).
- Independent **mutation replay** (this audit): in a disposable worktree at HEAD,
  `isTrustedSender` was replaced with `return true` (pre-repair acceptance) and
  `KEL_PET_SUBSYSTEM_ENABLED` flipped to `true`. Result: **19 failed / 11 passed** across the
  three test files — refusals stop throwing exactly where the tests watch, and the pet-policy
  assertions catch the flip. A pre-fix checkout cannot run the channel test directly (the guarded
  modules did not exist), so this mutation is the discriminating equivalent —
  `evidence/ra-negctl-desktop-mutation.txt`.
- Pet channels: even if the constant were flipped, their handlers act on a pet window that cannot
  be created; the missing guard there is recorded as a conditional note (one constant away), not
  a reachable gap today.

**Verdict: VERIFIED_CLOSED.** Guard coverage proven systematic by enumeration + suite + mutation
replay. Two carried, pre-existing semantics are recorded (not new defects):

1. `allowDevServer` accepts `http://localhost:*` for the channels that previously allowed it. In a
   packaged build the window loads `file:`; the shipped main process registers no
   `will-navigate`/`setWindowOpenHandler` handlers and the renderer routes external links through
   the shell bridge (`openExternalUrl`). The dev-origin acceptance is therefore a dev-mode
   convenience whose abuse requires the top frame to be navigated to a localhost URL by some other
   means. Carried as risk (see `06_ADJACENT_RISK.md`), unchanged from the pre-repair policy the
   finding required to keep.
2. The pet channels are outside the guard set only because the subsystem is disabled at
   registration time; a future enablement must add the shared guard to `registerIpcHandlers`.
