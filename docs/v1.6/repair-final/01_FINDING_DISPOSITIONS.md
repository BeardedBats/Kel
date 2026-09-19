# 01 — FINDING DISPOSITIONS (Campaign C)

Status vocabulary: `PENDING` · `IN_PROGRESS` · `REPAIRED` · `NOT_REPRODUCIBLE` · `INVALID_FINDING` · `ACCEPTED_DEFERRED`.

## Summary

- Total Campaign B findings: **12** (AUD-BLOCK 0 · AUD-MAJOR 2 · AUD-MINOR 9 · AUD-SUG 1)
- Repaired: 2 · Not reproducible: 0 · Invalid: 0 · Deferred: 0 · Remaining: 10

## Ledger

| ID | Sev | Title (short) | Status | Repair commit | Regression test | Attack replay | Residual risk |
|---|---|---|---|---|---|---|---|
| AUD-MAJOR-001 | MAJOR | Chat-approval conversation scoping opt-in | REPAIRED | `44aee9f` | `test_v16_approvals.py` 28/28 (4 fail pre-fix) + adjacent 129/129 | probe-1 §A: omission on a foreign approval refused (was approved); A6 `main`-parity kept | `/api/state` read-only pending list + `/api/autonomy` by-id resolve (unchanged; re-audit) |
| AUD-MAJOR-002 | MAJOR | Privileged IPC sender validation not uniform | REPAIRED | `eaf7bad` | `sender-guard.test.ts` 7 + `ipc-sender-channels.test.ts` 18; desktop vitest 147/147; tsc exit 0 | pre-fix replay: feedback pair + adapter dispatcher accept spoofed frames (4 failed); guard-free anchors for credential/sendSync families | dispatcher kept (shipped donor surfaces) + now guarded; guard semantics == the 8 previously-guarded channels (re-audit note) |
| AUD-MINOR-001 | MINOR | COMMIT_LEDGER completeness failures | PENDING | — | — | — | — |
| AUD-MINOR-002 | MINOR | Budget reservations not aggregated (overcommit) | PENDING | — | — | — | — |
| AUD-MINOR-003 | MINOR | `native.child_env` strip weaker than claimed | PENDING | — | — | — | — |
| AUD-MINOR-004 | MINOR | R12 packaged-evidence integrity gaps | PENDING | — | — | — | — |
| AUD-MINOR-005 | MINOR | Corpus state drift not reconciled at RC | PENDING | — | — | — | — |
| AUD-MINOR-006 | MINOR | Delegation containment does not resolve `..` | PENDING | — | — | — | — |
| AUD-MINOR-007 | MINOR | Donor `aioncore` runtime live/shipped; no disposition | PENDING | — | — | — | — |
| AUD-MINOR-008 | MINOR | Donor desktop-pet subsystem wired | PENDING | — | — | — | — |
| AUD-MINOR-009 | MINOR | Donor builder config is the default build path | PENDING | — | — | — | — |
| AUD-SUG-001 | SUG | Capability directive docstring vs behavior | PENDING | — | — | — | — |

Per-finding detail (reproduction, root cause, repair, tests, replay, residual risk) is appended below as each finding is dispositioned.

### AUD-MAJOR-001 — detail (REPAIRED, `44aee9f`)

- **Reproduction (pre-fix):** probe-1 §A (`evidence/ma1-attack-prefix.txt`): A2 — a caller declaring no conversation resolved a convA-owned approval (`state: approved`, no error); A6 — same for a main-owned approval. Declared-foreign callers were refused (A1/A5).
- **Root cause:** the APR-02 repair made ownership an optional parameter (`resolve` ran `_require_owned` only `if conversation:`), and the legacy singular `/api/approval` route had no scope at all.
- **Repair:** `chat_approvals.require_owned` is public and unconditional; omission acts as the `main` conversation (read-path parity). Both the `/api/approvals` action and the legacy `/api/approval` route run it. No UI change (UI callers already declare the conversation).
- **Tests:** 4 new discriminating tests fail pre-fix (`ma1-newtests-prefix-fail.txt`: 4F), pass post-fix (`ma1-newtests-postfix-pass.txt`: 10/10); focused file 28/28; adjacent 129/129 (`ma1-adjacent-suite-rerun.txt`).
- **Attack replay:** `ma1-attack-replay-at-fix.txt` — A2 now `PolicyError: That request belongs to another conversation`; A6 allowed by design (omission = `main`, the record is main-owned); probe reached `PROBE-END`.
- **Sibling search:** every approval-resolution entry point was enumerated and reviewed (chat `resolve`; `/api/approvals`; `/api/approval` singular; `store.resolve_approval` callers incl. the coding-adapter expiry-deny on its own run id; `Autonomy.resolve_expansion` callers incl. `/api/autonomy` resolve). Details in `03_REGRESSION_EVIDENCE.md`.
- **Residual risk (re-audit items, unchanged):** `/api/state` unscoped read-only pending-approvals list; `/api/autonomy` by-id resolve surface. See `05_REMAINING_RISKS.md`.

### AUD-MAJOR-002 — detail (REPAIRED, `eaf7bad`)

- **Reproduction (Campaign B, static + reachability):** `07_SECURITY_AUTHORITY.md` coverage table — credential trio / feedback pair / sendSync handlers / recovery channel / generic adapter dispatcher had no sender-frame guard while 8 Kel channels enforced one; preload runs in subframes and artifact viewers render iframes/webviews. No harness reproducer existed.
- **Root cause:** security closure applied per-handler during W-sweeps instead of one shared sender-validation primitive.
- **Repair:** new `desktop/packages/desktop/src/common/senderGuard.ts` — one fail-closed rule (`senderFrame === sender.mainFrame` AND `file:`; dev `http://localhost:` only where the channel previously allowed it; missing/malformed metadata refused). Applied to every privileged registration: 11 Kel channels (8 inline checks refactored onto the helper; the credential trio registers through the new `kelCredentialIpc.ts` seam), the feedback trio (`feedbackBridge.ts`), the four sendSync handlers + `backend:recover-corrupted-database` (`backendStartupIpc.ts` seam used by `index.ts`; refused sync calls answer `null`), and the `ADAPTER_BRIDGE_EVENT_KEY` dispatcher.
- **Dispatcher decision:** retained (donor renderer + WebUI depend on it; removing it would break shipped donor surfaces) and now guarded — recorded in `05`.
- **Tests:** `sender-guard.test.ts` (7-case truth table) + `ipc-sender-channels.test.ts` (6 spoof shapes × every family + legit main-frame path per family; 18 tests). Desktop vitest 147/147; `tsc --noEmit` exit 0. No acceptance set was widened (each channel keeps its previous origin policy).
- **Pre-fix discrimination:** stash replay with tracked sources reverted → the in-place channels (feedback pair ×3, adapter dispatcher) accept spoofed senders (4 failed / 14 passed); the extracted families' pre-fix inline registrations are guard-free at HEAD (`evidence/ma2-prefix-anchors.txt`).
- **Sibling search:** every `ipcMain.*` registration across `desktop/packages` enumerated — the set above plus pet channels (`petManager.ts`, `petConfirmManager.ts`; pet-window events, MINOR-008 scope) — reviewed, unchanged; no other privileged registrations exist.
- **Residual risk (re-audit note):** guard semantics deliberately identical to the previously-guarded channels (top frame of the sending webContents + allow-listed origin schemes); a stricter window-identity check was not required by the finding and would risk breaking donor windows — carried for the final re-audit.
