# 06 — ADJACENT RISK (final re-audit)

§29 pass: for each repaired root-cause family, at least one sibling path was inspected for a
bypass of the same invariant. This is deliberately smaller than Campaign B's blind-spot audit and
is independent of it. Findings raised here are recorded in `07_FINAL_FINDINGS.md` (nothing fixed).

## 1. Ownership (AUD-MAJOR-001)

- Siblings inspected: `/api/state` read list; `/api/autonomy` by-id resolve; legacy route reader
  join; `store.resolve_approval` caller map; coding-adapter expiry deny.
- Determination: no unguarded external mutation path. Two recorded surfaces (state read list;
  autonomy by-id resolve) are documented in `02_SECURITY_AUTHORITY.md` as observations, not
  bypasses. The autonomy path adds no capability beyond the declared-scope model
  (declaration is a scope assertion, not authentication) but is un-scoped by design; the claim
  "the resolution authority boundary is the scoped write path" is therefore imprecise — see
  `07_FINAL_FINDINGS.md` RA-SUG-003 (documentation recommendation).

## 2. IPC trust (AUD-MAJOR-002)

- Siblings inspected: the single donor-bridge dispatcher channel (covers ALL provider methods —
  one guard suffices); pet channel family (unreachable while disabled; conditional note in `02`);
  CDP bridge (`process/resources/builtinMcp/cdpBridge.ts`): user-gated builtin-MCP capability,
  binds 127.0.0.1, token-guarded with a documented same-user assumption, single-target (the
  in-app browser webview) — out of the repaired surface, unchanged.
- Donor WebUI mode (`--webui` switch / `webui.desktop.enabled` preference; password-gated via
  `ensureAdminUser`): a donor surface serving the app to a browser. The shipped tree registers no
  WebSocket broadcaster (the registry has no callers outside the adapter re-export) and the Kel
  engine channels are preload-only, so the Kel authority surface is not bridged to a browser; the
  mode was not exercised live in this audit and is outside the repaired findings. Observation only.
- Determinization: no other `ipcMain` registration exists (whole-tree scan, `02` table).

## 3. Budget accounting (AUD-MINOR-002)

- Siblings inspected: `release_budget(consumed=True)` semantics (pinned); pre-fix defect class
  (sequential aggregation) re-attacked — closed (`ra-attack-major2.txt` C1–C7).
- **New finding (RA-MINOR-001 candidate): the aggregation is not atomic.** Five concurrent
  `reserve_budget` calls on the same job all passed the check (each read `committed=0`) and
  committed 15.0 against an envelope of 8 — reproduced in 15/15 storm rounds (5/5 or 4/5 threads
  winning; `evidence/ra-attack-major2.txt` C8). The service is a `ThreadingHTTPServer`, so
  concurrent callers are architecturally possible; today the only callers are the dormant
  delegation/pods helpers (`KEL_WORKFORCE` flag default off; "nothing live calls these functions
  yet"), so this is latent, not production-reachable in V1.6 as shipped. Recorded as RA-MINOR-001
  with an explicit escalation note: the feature must not be wired without a transactional
  (single-writer / conditional-insert) reservation.
- Related observation: no automated close path calls `release_budget` (fail-closed narrowing; any
  future wiring must add settle/release on completion and failure — recorded in the finding).

## 4. Path canonicalization (AUD-MINOR-006)

- Siblings inspected: `parallel._clean_path` (refuses `..`, `.`, absolute, drive-relative, `~` —
  verified empirically, stricter than required); `guardrails._norm` deny-list (lexical only — a
  `C:/Users/Nick/../Windows/...` spelling is not matched by the string check, but the observed
  effect points resolve before the check: `apply_changes` uses `resolve(strict=True)` and the
  project-create path resolves before its root check; recorded residual, no effect bypass found);
  `coding.py` untracked-file loop resolves and re-checks containment (the tracked-file loop
  copies git-listed files without a symlink re-check — noted, git-governed input).
- New observation (RA-SUG-001 candidate): under the universal root `.`, `_path_within` reports
  escape and absolute spellings as contained (`..`, `../x`, `C:/x`, `/x` -> True;
  `authority_within({'write_scope':['..']}, {'write_scope':['.']})` -> None). The campaign
  documented this as "universal by design" and pinned relative-path behavior, but the same
  docstring says such paths "can never be contained in a relative scope" — the sentence is false
  for the universal root, and the delegation validator therefore does NOT constrain `..`/absolute
  scope entries when the delegator's scope is `.` (the intended safety net is an effect-time
  filesystem boundary that does not exist yet because the feature is dormant). Recorded as
  RA-SUG-001 (wording + explicit pin + effect-time requirement), not a regression: concrete-root
  escapes are fully closed and pinned.

## 5. Credential filtering (AUD-MINOR-003)

- Siblings inspected: `SECRET_ENV_KEYS` is the canonical 3-key set used by every containment
  helper (native child env, internal child env, test-command env, redaction) — verified; codex
  app-server child (`appserver.py`) keeps only `OPENAI_API_KEY` (its own credential); native
  `execute`/`probe` spawn with the filtered env (real-subprocess verification); no provider key
  travels in argv or logs; durable text passes `redact()` (sentinel-verified).
- No adjacent leak found. Full battery: `evidence/ra-attack-major2.txt` D1–D6.

## 6. Installer executable identity (C-DISC-001)

- Fix reviewed (`05a076b`): the payload/registration checks now use
  `${AIONUI_APP_EXECUTABLE_FILENAME}` (defined `Kel.exe`), including the verify macro; the
  process-control logic was already path-based (rename-proof) and shortcut/registration/
  uninstall paths use electron-builder `productName` (Kel).
- Neighboring donor-executable assumptions found in the same file set (recorded, NOT fixed):
  `installer-messages.nsh` carries ~47 donor-branded user-visible strings shown in failure and
  lock dialogs (including a "send this report to the AionUi team?" consent prompt whose report
  script is inert while `SENTRY_DSN` is empty — `support/report-installer-failure.ps1` skips with
  no network call); `support/query-lockers.ps1` keeps `AionUi.exe` / `Uninstall AionUi.exe` in a
  fallback known-files list (the same script enumerates all top-level files anyway, so behavior
  is unaffected); several internal temp/log names remain donor-named. Recorded as RA-MINOR-002
  (user-visible) and RA-SUG-002 (internal/fallback). Evidence:
  `evidence/ra-installer-donor-strings.txt`; C-DISC-001 pre/post logic:
  `evidence/ra-cdisc001.txt`.
- The definitive verification is the fresh package built and installed by THIS audit (single
  campaign: clean install exit 0, `Uninstall Kel.exe`, ARP `Kel 1.6.0`, shortcuts `Kel.lnk`) —
  see `04_PACKAGE_IDENTITY.md` / `05_INSTALLED_PRODUCT.md`.

## Carried risks (accepted for release gate, recorded for the record)

| Risk | Where recorded | Status |
|---|---|---|
| `allowDevServer` origin policy on some channels (pre-existing; unchanged semantics) | `02` §carried | risk carried |
| Pet channels unguarded *if* the subsystem is ever enabled | `02` conditional note | dormant; conditional |
| Guardrails deny-list is lexical (effect points resolve) | this file §4 | residual, no bypass found |
| `/api/state` lists all pending approvals (read-only) | `02` observations | risk carried |
| `/api/autonomy` resolve un-scoped by design (Work surface) | `02` + RA-SUG-003 | documented exception recommended |
| Donor WebUI mode exists (user-gated, password-auth; not exercised) | this file §2 | observation |
