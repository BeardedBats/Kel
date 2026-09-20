# IMPLEMENTATION STATUS — `dev/daily-driver`

Updated: 2026-09-20 (D0–D3 complete; entering D4)

## Lane

- Worktree: `C:\Users\Nick\Desktop\Kel\kel-daily-driver` — branch `dev/daily-driver`.
- Base: `37b1f27faf02dfa5feb96449fc3768c0ec4e9692`; lane open `3f83be7` (`1.7.0-dev` identity + durable records).
- Protected refs untouched; no release tag; no publish.

## FINAL_V16_RESIDUAL_CLEANUP

Source audit: `audit/v16-human-visual-final` @ `554f79987399dae10e3b03ecf2a9b2c975c33961`
(production target `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda`; 0 BLOCK / 0 MAJOR / 2 MINOR / 2 SUG).

| Audit ID | Item | Repair commit | Evidence |
| --- | --- | --- | --- |
| HVRA-MINOR-001 | Permissions Work column: raw engine job id shown | `9bdf338` | new `jobLabels.ts` + `job-labels.test.ts` (5 tests incl. page wiring pin); raw id moved to tooltip + Advanced "Work references" |
| HVRA-MINOR-002 | Installer/uninstaller FileDescription donor phrase | `777fefe` | `desktop/package.json` description → `Kel` (builder source of FileDescription); `donor-policy.test.ts` pin. Packaged Properties re-check deferred to package phase (PACKAGE_EVIDENCE checklist) |
| HVRA-SUG-001 | ACP setup help link → donor wiki | `cce55d0` | donor constant + "Setup guide" button removed from `LocalAgents.tsx`; no Kel help destination exists to retarget (repo home is not a setup guide) |
| HVRA-SUG-002 | Duplicate pet-refusal toast | `f594282` | Root cause: audit probe double-count artifact — `.arco-message, .arco-message-content` both match ONE toast (Arco Notice renders both nodes; campaign harness saw a single message). Refusal toast made idempotent via stable message id; truthful OFF-state sync untouched. Pin in `donor-policy.test.ts` |

## Environment notes

- External provider credentials: probed in D1 (recorded in KNOWN_LIMITATIONS.md when known).
- No public DNS / no external notification delivery assumed; fixtures + local validation where honest.

## Completed lanes since (summary)

- **D1** `0279a1d` — truthful provider states (Available / Needs setup / Temporarily unavailable /
  Unavailable), Set up → Save + Verify.
- **D2** `7c9df63` — donor update CDN severed; manual Kel GitHub check fails closed.
- **D3** (this commit) — Remote/WebUI: the shipped surface had no session enforcement on business APIs
  (anonymous LAN reads + anonymous `POST /api/webui/reset-password`); the web-host gateway now
  validate-gates everything against aioncore's `/api/auth/user` (allowlist: login/logout/qr-login/
  api-auth), proxies `/qr-login`, and gates WS upgrades. Verified with the real stack (raw boundary
  matrix + Playwright browser, `evidence/d3/`). Wrong first attempt reverted (`b13301a`).

## Next item

- **D4 — Transcription first-class workflow** (§11): record/upload/drag-drop, folders, recent
  transcripts, detail/rename/copy/download (transcript + audio), progress/cancel/retry, API-key
  setup, conversation/Project integration; keep the "no spacebar start/stop" rule; no second
  document database.
