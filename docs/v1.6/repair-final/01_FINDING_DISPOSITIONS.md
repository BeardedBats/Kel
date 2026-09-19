# 01 — FINDING DISPOSITIONS (Campaign C)

Status vocabulary: `PENDING` · `IN_PROGRESS` · `REPAIRED` · `NOT_REPRODUCIBLE` · `INVALID_FINDING` · `ACCEPTED_DEFERRED`.

## Summary

- Total Campaign B findings: **12** (AUD-BLOCK 0 · AUD-MAJOR 2 · AUD-MINOR 9 · AUD-SUG 1)
- Repaired: 12 · Not reproducible: 0 · Invalid: 0 · Deferred: 0 · Remaining: 0

## Ledger

| ID | Sev | Title (short) | Status | Repair commit | Regression test | Attack replay | Residual risk |
|---|---|---|---|---|---|---|---|
| AUD-MAJOR-001 | MAJOR | Chat-approval conversation scoping opt-in | REPAIRED | `44aee9f` | `test_v16_approvals.py` 28/28 (4 fail pre-fix) + adjacent 129/129 | probe-1 §A: omission on a foreign approval refused (was approved); A6 `main`-parity kept | `/api/state` read-only pending list + `/api/autonomy` by-id resolve (unchanged; re-audit) |
| AUD-MAJOR-002 | MAJOR | Privileged IPC sender validation not uniform | REPAIRED | `eaf7bad` | `sender-guard.test.ts` 7 + `ipc-sender-channels.test.ts` 18; desktop vitest 147/147; tsc exit 0 | pre-fix replay: feedback pair + adapter dispatcher accept spoofed frames (4 failed); guard-free anchors for credential/sendSync families | dispatcher kept (shipped donor surfaces) + now guarded; guard semantics == the 8 previously-guarded channels (re-audit note) |
| AUD-MINOR-001 | MINOR | COMMIT_LEDGER completeness failures | REPAIRED | `960e023` | ledger gate: 12 unlisted + 2 malformed → PASS 1:1 (73 commits) | pre/post gate runs (`mi1-ledger-check-*`) | gate keeps the ledger honest; keep it green |
| AUD-MINOR-002 | MINOR | Budget reservations not aggregated (overcommit) | REPAIRED | `7e293ba` | `ReservationAccountingTests` + delegation cumulative test (9; 5 fail pre-fix); focused 65/65; cluster 299/299 | probe §E7: cost 8 after cost 1 refused (remaining 7.0); E5 unchanged; E6 disclosed | token/wallclock unchanged by design (pinned); run-slot vs planning accounting separation (re-audit note) |
| AUD-MINOR-003 | MINOR | `native.child_env` strip weaker than claimed | REPAIRED | `91bd869` | `ChildEnvironmentTests` 5 (3 fail pre-fix) + spawned-process boundary; cluster 34/34 | probe §G: DeepSeek absent from codex+claude children; G1–G3 unchanged | sibling launchers reviewed (appserver whitelist, test-command strip, coding bridge); system tools inherit by design (re-audit note) |
| AUD-MINOR-004 | MINOR | R12 packaged-evidence integrity gaps | REPAIRED | `89ab6ad` | gate FAIL (r12-fresh) / PASS (r12-fresh2); integrity --fail-on-dirty PASS at repair head | `mi4-gate-discrimination.txt`; `mi4-integrity-repair-head.txt`; hashes `mi4-script-hashes.txt` | §17/18 executions (build log, gated probe, uninstall log, final integrity re-run) tracked in `04_PACKAGE_EVIDENCE.md` |
| AUD-MINOR-005 | MINOR | Corpus state drift not reconciled at RC | REPAIRED | `8ca6231` | corpus lint FAIL at HEAD (25 markers) → PASS (6 files); ledger gate re-run 1:1 | pre/post lint runs (`mi5-*`) | none; both gates keep the corpus honest |
| AUD-MINOR-006 | MINOR | Delegation containment does not resolve `..` | REPAIRED | `c056a8a` | r1 containment table + e2e issuance refusal (4; 3 fail pre-fix); focused 26/26; cluster 303/303 | inline replay: `src/../secrets` refused (was contained); traversal matrix in `mi6-*` | `parallel._clean_path` safe by construction; guardrails deny-list normalization recorded (re-audit) |
| AUD-MINOR-007 | MINOR | Donor `aioncore` runtime live/shipped; no disposition | REPAIRED | `197dbff` | provenance wiring pins (fail pre-fix) + build-side assertion; reference sha256 bound | staged vs packaged `aioncore.exe` byte-identical; `provenance.json` recorded (`mi7-*`) | KEEP (live backend) + provenance-bound; exe metadata donor-named by design (re-audit note) |
| AUD-MINOR-008 | MINOR | Donor desktop-pet subsystem wired | REPAIRED | `197dbff` | donor tests 5/5 (3 fail pre-fix); gates at 3 entry points | reachability list in `06_DONOR_DISPOSITIONS.md`; settings toggle no-op | modules/assets retained inert; removal deferred post-V1.6 (recorded) |
| AUD-MINOR-009 | MINOR | Donor builder config is the default build path | REPAIRED | `197dbff` | build-identity pins (fail pre-fix); desktop vitest 152/152; tsc 0 | both builder invocations use `kel-builder.json`; identity assertion pre-build | artifact metadata re-asserted at §17/18 package evidence |
| AUD-SUG-001 | SUG | Capability directive docstring vs behavior | REPAIRED | `6d665b2` | docstring-conformance table (accepted/rejected) + docstring pin (fails pre-fix); focused 39/39 | replay: `GET /a/[kel:web=off] 200` matched by design; docstring now states it; quoted/code/embedded/URL inert | behavior deliberately unchanged (documentation alignment); no parser risk |

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

### AUD-MINOR-002 — detail (REPAIRED, `7e293ba`)

- **Reproduction (pre-fix):** probe §E (`evidence/mi2-prefix-attack.txt`): E7 — after a cost-1 reservation, a second cost-8 reservation was accepted on an envelope of 8 (cumulative 9); E5 (single far-beyond) was already refused.
- **Root cause:** two parallel reservation systems — run-slot accounting (`job['reserved']`, maintained by the core run lifecycle) vs the Phase-5.3 `budget_reservations` table; `reserve_budget`'s envelope check read only `budget − spent − reserved` and never aggregated its own table.
- **Repair:** `reserve_budget` now subtracts every un-released reservation (`state != 'released'`; `consumed` still narrows) from the envelope before accepting a commitment. Narrow: the existing check extended, the existing table aggregated — no new subsystem; token/wallclock semantics untouched.
- **Tests:** `ReservationAccountingTests` (8) + delegation-path cumulative test (1): second-sees-first, cumulative fill/exceed, release frees, consumed narrows, zero/exact values, disjoint jobs, retry-after-release, disclosure pin. 9/9 post-fix (`mi2-newtests-postfix-pass.txt`), 5 fail pre-fix (`mi2-newtests-prefix-fail.txt`); focused files 65/65 (`mi2-focused-suite.txt`); cluster 299/299 (`mi2-adjacent-suite.txt`).
- **Attack replay:** `mi2-postfix-attack.txt` — E7 now `PolicyError: Reserved cost 8.0 exceeds the remaining job budget 7.0`; E5 unchanged; E6 (tokens=1e12/wallclock=1e7) unchanged and disclosed.
- **Promotion probe:** `mi2-claiming-probe.txt` — with a cost-4 planning reservation standing on a budget-4 job, execution claims cap actual spend at the envelope (m1+m2 spend 4; m3 refused "Execution and verification budget exhausted"); `spent + reserved ≤ budget` holds. No re-grade; remains MINOR.
- **Adjacent assessment (re-audit note):** consumers of `job['reserved']` (claim gate, engine dispatch, runner) govern run slots and are intentionally not fed by planning reservations — merging the two dimensions would change execution behaviour beyond this finding; recorded for the final re-audit.

### AUD-MINOR-003 — detail (REPAIRED, `91bd869`)

- **Reproduction (pre-fix):** probe §G (`evidence/mi3-prefix-attack.txt`): G4 — `DEEPSEEK_API_KEY` present in both the `codex` and `claude` child environments; G1–G3 (internal whitelist, redact) already correct.
- **Root cause:** `native.child_env` popped only the named counterpart key (`if provider == 'codex': pop ANTHROPIC else: pop OPENAI`), so third-provider keys (DeepSeek) and any future Kel-managed keys were forwarded even though the docstring already promised the stronger property.
- **Repair:** the canonical set is now `internal.SECRET_ENV_KEYS` (promoted from a private name); `native.child_env` removes every key not in the provider's allow map (`codex`→OPENAI, `claude`→ANTHROPIC, unknown→none). The native `--version` probe runs under the same contained environment. Fail-closed for unknown providers; no acceptance widening.
- **Tests:** `ChildEnvironmentTests` — updated cross-provider pin, third-provider absence for both children, unknown-provider fail-closed, a real spawned-process boundary check (the child process observes only its own key), test-command strip pinned including DeepSeek. 9/9 post-fix (`mi3-newtests-postfix-pass.txt`), 3 new tests fail pre-fix (`mi3-newtests-prefix-fail.txt`); cluster 34/34 (`mi3-adjacent-suite.txt`).
- **Attack replay:** `mi3-postfix-attack.txt` — G4 now `DEEPSEEK_API_KEY: False` for both children; G1–G3 unchanged.
- **Sibling search (spawn inventory):** `appserver.py` codex app-server child (internal whitelist `keep=('OPENAI_API_KEY',)`) OK; `host_runtime.test_command_env` strips all three (now pinned with DeepSeek); `coding.py:240` nulls all three for its subprocess; `runner.py`/`coding_transport.py` children are Kel's own engine processes (trusted, need keys); `git`/`powershell.exe`/`wsl.exe` system tools inherit the environment — reviewed, unchanged (local tools with no provider-key semantics; git hooks disabled for the repo calls).

### AUD-MINOR-006 — detail (REPAIRED, `c056a8a`)

- **Reproduction (pre-fix):** inline replay (`evidence/mi6-prefix-attack.txt`): `authority_within({'write_scope': ['src/../secrets']}, {'write_scope': ['src']})` → contained (None); `src/../secrets` counted as within `src`.
- **Root cause:** `_path_within` normalized `./` and separators but never resolved `..` — the containment decision was lexical on unresolved text, so any `..` segment that string-prefixed correctly passed.
- **Repair:** canonical lexical resolution inside the primitive with no filesystem access: separators normalized (both directions), `.` dropped, `..` pops the previous segment; absolute, drive-relative, and self-escaping entries can never be contained in a relative scope (fail-closed); case-exact comparison documented as conservative; `.`-as-root stays universal by design (docstring + pinned test). No authority widened: entries that resolve inside the scope keep passing; entries that resolve outside are now refused.
- **Tests:** `test_dotdot_entries_resolve_lexically_before_containment`, `test_the_containment_normalization_table` (contained: exact root/trailing slash/repeated separators/mixed separators/`./`/interior `..`; refused: `src/../secrets`, `a/../../x`, `..`, `../src`, absolute, drive-relative, sibling-prefix `src2`, case variant, `.`), `test_a_dot_root_stays_universal_by_design`, `test_a_write_scope_that_escapes_via_dotdot_is_refused_end_to_end` (issuance refuses against both the boundaries dimension and the delegator dimension). 4/4 post-fix (`mi6-newtests-postfix-pass.txt`), 3 fail pre-fix (`mi6-newtests-prefix-fail.txt`); focused file 26/26 (`mi6-focused-file.txt`); cluster 303/303 (`mi6-adjacent-suite.txt`).
- **Attack replay:** `mi6-postfix-attack.txt` — `src/../secrets` refused; full traversal matrix behaves as documented; legitimate nested/interior-`..` paths stay contained.
- **Sibling search:** `parallel.py` compares declared paths with the same string-shape logic but validates every declared path at entry (`_clean_path` refuses absolute and any `.`/`..` segment; pinned by `test_workforce_parallel.py::test_absolute_and_escaping_paths_are_refused`) — safe by construction, unchanged. `guardrails._norm` deny-list normalization does not resolve `..`; inputs at the effect points observed (apply_changes passes `resolve(strict=True)` roots; project-create resolves before use) — recorded as a re-audit item (see `05`), unchanged as outside this finding's primitive. Filesystem-backed checks (`core.py` artifacts, `coding.py` untracked, `runner.py` attachments) already use `resolve()`.

### AUD-MINOR-001 — detail (REPAIRED, `960e023`)

- **Reproduction (pre-fix):** the new gate (`evidence/mi1-ledger-check-prefix-fail.txt`) reported 12 unlisted commits (022f3ac, 0aadd42, 34947f0, 12f87a7, 08f5667, e8bbb05, eea6503, 4440a90, 756218e, ae4c5b0, 820ee3e, edd50de) and 2 malformed cells against `git rev-list 8a2b25d..08f5667` (73 commits).
- **Root cause:** the ledger was maintained by hand during Campaign A; four commits landed without rows, two rows kept placeholder cells (`HEAD`, prose `R6 tests+record`), and the RC commit (with packaging edits) was never added.
- **Repair:** all missing rows added (including a clearly marked reconciliation table), the two malformed cells corrected to `0aadd42`/`022f3ac` and `e8bbb05`, headers filled with the RC end value, and a gate script added — `docs/v1.6/audit-final/tools/reconcile-commit-ledger.py` exits 1 on any unlisted commit, placeholder SHA cell, or wrong parent.
- **Verification:** FAIL before → PASS after (`mi1-ledger-check-postfix-pass.txt`: 73 commits, every row well-formed, 1:1).
- **Residual risk:** the gate must stay green as commits land (documented in the ledger's maintenance rules).

### AUD-MINOR-004 — detail (REPAIRED, `89ab6ad`)

- **Reproduction (pre-fix):** the RC probe exited 0 with `attentionVisible:false` + `aboutLogoLoaded:false` (r12-fresh); no uninstall evidence; `r12-integrity.txt` captured with modified packaging files under an "expect empty" header and a script that never fails; unretained per-attempt timings asserted in the R10 doc; no build command/log for `package-r12`.
- **Repair (items a/c/d):** the probe now runs through `r12-assert-gate.cjs` (hard assertions: healthyBoot, engineVersion, attentionVisible, aboutLogoLoaded, consoleErrors, rawLeaks, overflow) and exits non-zero on failure, recording `out.gate`; the integrity script gains `--fail-on-dirty` + repo/out overrides; the r10-f row no longer asserts unretained timings.
- **Verification:** `mi4-gate-discrimination.txt` — r12-fresh FAIL/exit 1 vs r12-fresh2 PASS/exit 0 vs repo evidence copy PASS; `mi4-integrity-repair-head.txt` — `INTEGRITY: PASS dirty=0 actionable_hits=0` at the repair head; script hashes in `mi4-script-hashes.txt`.
- **Items b/e:** the uninstall log and the repaired-package build command/log are produced + retained at §17/18; `04_PACKAGE_EVIDENCE.md` carries the checklist and links the artifacts.
- **Residual risk:** §17/18 executions are required to keep this finding's evidence set complete (tracked in `04`).

### AUD-MINOR-005 — detail (REPAIRED, `8ca6231`)

- **Reproduction (pre-fix):** `evidence/mi5-lint-prefix-fail.txt` — the new gate run against HEAD lists 25 stale/absent markers across `INVARIANT_LEDGER.md` (signature rows in PLANNED/OPEN_GAP/PARTIAL states), `MIGRATION_LEDGER.md` (next-free 20, unchecked RC checklist, "planned"/"assertion pending" cells), `REQUIREMENTS_TRACEABILITY.md` (R9/R11/R12/WFWIRE/PKG-ASSERT/RC PENDING; "re-verified open"), `AUDIT_HANDOFF.md` (TBD bindings), `P2_P3_DISPOSITION.md` and `docs/v1.6-visual-ux/00_STATUS.md` (missing reconciliation markers).
- **Root cause:** the corpus was maintained through the marathon but never reconciled at RC; several tables kept their pre-delivery states and two version tables disagreed with the code constants.
- **Repair:** every itemized row/status reconciled to the delivered tree with commit/test anchors — INVARIANT_LEDGER 22 rows; MIGRATION_LEDGER version truth from code constants + packaged DB dumps (16 unclaimed; 17 = v17-finding-resolution-kind; 20 = chat_approval_announcements; 21 = v16-budget-reservations; next free 22; RC checklist asserted with run anchors); REQUIREMENTS R9/R11/R12/WFWIRE/PKG-ASSERT/RC delivered; AUDIT_HANDOFF bindings filled (HEAD `08f5667`, range `8a2b25d..08f5667` = 73 commits); P2_P3 TL;DR; 00_STATUS marked as the historical audit-stop record. No historical evidence fabricated — Campaign C evidence is labeled as such; cells that were never true are corrected, not re-recorded.
- **Verification:** `mi5-lint-postfix-pass.txt` — `CORPUS LINT: PASS (6 files checked)`; the ledger gate re-run still `PASS — 73 commits … 1:1`.
- **Gate:** `docs/v1.6/audit-final/tools/check-corpus-staleness.py` (denylist + required markers; `--source <rev>` is the pre/post discriminator).
- **Residual risk:** none beyond keeping both gates green as the RC finalizes.

### AUD-MINOR-007 — detail (REPAIRED, `197dbff`)

- **Reproduction (Campaign B, static):** `bundled-aioncore/win32-x64/aioncore.exe` shipped and spawned (backend launcher) with no corpus disposition; the binary was staged from a download cache (donor manifest: v0.2.2, iOfficeAI/AionCore release) with no content hash.
- **Decision:** KEEP — it is the live app backend (`BackendLifecycleManager` → launcher spawn), not dead code; removal or rename would reshape the architecture beyond this finding.
- **Repair:** `prepare-aioncore.js` now writes a Kel-side `provenance.json` next to the donor manifest (sha256, bytes, donor repo, version, source) in both staging branches, and `build-with-builder.js` fails the build when it is missing. Reference hash (staged and packaged copies byte-identical): `67eb02774bab3855b759ec9756c2e540cd17b64b850407fa4b8bad07fd8a0892` (`mi7-aioncore-provenance.txt`).
- **Security read:** spawn via backend-launcher with `{...process.env}` inheritance (same containment policy as AUD-MINOR-003); `AIONUI_BACKEND_BIN` developer override; dynamic local port; exe metadata stays donor-named by design (packaged under `resources/bundled-aioncore/`, not user-visible) — re-audit note in `06`.
- **Tests/pins:** `donor-policy.test.ts` provenance wiring checks (fail pre-fix); build-side provenance assertion.

### AUD-MINOR-008 — detail (REPAIRED, `197dbff`)

- **Reproduction (Campaign B, static):** the pet subsystem was wired (`createPetWindow`, settings APIs, shipped assets) with no disposition; end-user reachability exists via the settings surface.
- **Decision:** DISABLED (hidden) — modules/assets retained (no risky deletion); every activation path is gated by `petPolicy.KEL_PET_SUBSYSTEM_ENABLED = false`: `petManager.createPetWindow` refuses; the settings setter refuses enabling (persists `false`); the `src/index.ts` startup path requires `pet.enabled === true && KEL_PET_SUBSYSTEM_ENABLED`.
- **Unreachability proof:** `donor-policy.test.ts` (3 pins; fail pre-fix) + the reachability list in `06_DONOR_DISPOSITIONS.md`; the toggle is a no-op, so no pet window can be created and no donor behavior/brand is reachable.
- **Residual risk:** inert assets remain shipped (recorded for post-V1.6 cleanup); removal deferred deliberately.

### AUD-MINOR-009 — detail (REPAIRED, `197dbff`)

- **Reproduction (Campaign B):** `scripts/build-with-builder.js` defaulted both electron-builder invocations to the donor `electron-builder.yml` (appId com.aionui.app / productName AionUi); Kel packaging required an explicit `--config kel-builder.json`.
- **Repair:** the script now uses `KEL_BUILDER_CONFIG = 'kel-builder.json'` for both invocations (main + mac prepackaged DMG) and calls `assertKelBuildIdentity()` before the vite build — refusing to build unless `kel-builder.json` carries `productName: Kel` and `appId: com.kel.desktop`; the donor yml remains only as the `extends` base. All package scripts (`dist`, `dist:win`, …) flow through the Kel default.
- **Tests:** `donor-policy.test.ts` build-identity pins (fail pre-fix); artifact metadata re-asserted at §17/18 package evidence (exe metadata / installer hash / ARP).
- **Residual risk:** none beyond the §17/18 artifact binding.

### AUD-SUG-001 — detail (REPAIRED, `6d665b2`)

- **Reproduction (Campaign B):** the `directive_clauses` docstring described exclusions imprecisely — a bare unquoted technical token (`GET /a/[kel:web=off] 200`) fires by design, while the docstring implied broader inertness.
- **Disposition:** documentation alignment (narrow) — the parser is deliberately unchanged; "do not turn a suggestion into architecture work".
- **Repair:** the docstring now states the exact rule (token FIRES WHEREVER IT APPEARS OUTSIDE QUOTES / INLINE CODE / FENCES — log lines, punctuation-adjacent, mixed case; scheme-URL segments and quoted/coded forms inert).
- **Tests:** `test_sug_001_docstring_matches_behavior` — accepted/rejected conformance table (incl. the suggestion's exact probe) + a docstring pin that fails pre-fix (`ms1-conformance-prefix-fail.txt`); focused suite 39/39 (`ms1-conformance-postfix.txt`).
- **Replay:** `ms1-sug-replay.txt` — behavior unchanged and now documented; quoted/code/word-embedded/scheme-URL stay inert.
- **Residual risk:** none (no parser change).

### C-DISC-001 — installer registration aborted by donor-hardcoded `AionUi.exe` (REPAIRED, `05a076b`)

- **Discovered by Campaign C §18** (not a Campaign B item; recorded durably, repaired in the same release scope, preserved for the final independent re-audit): the script-built installer aborted registration with `event=extract result=fail method=7z missing=AionUi.exe` (E1010, exit 2), skipping uninstaller/ARP/shortcuts, because `resources/windows/installer-observability.nsh` hardcoded the donor executable name as the required payload file while the product ships `Kel.exe` (the auditor's direct-CLI build used the stock installer and never exercised this path).
- **Repair:** `AIONUI_APP_EXECUTABLE_FILENAME -> "Kel.exe"` (single source) + the literal checks/messages now use the define; `installer-update-verify.nsh` verify likewise.
- **Verified:** rebuilt v3 → silent install EXIT=0; `Uninstall Kel.exe`, ARP (`Kel 1.6.0`, `/currentuser`), `Kel.lnk` (start menu + desktop) created; fresh + continuity probes GATE PASS; reinstall OK; uninstall exit 0 with data retained.
- **Evidence:** `cdisc001-installer-e1010-prefix.txt`, `installed-battery.txt`, `installed-probe-fresh/`, `installed-probe-upgrade/`, `final-package-build-log-v3.txt`, `final-package-artifacts.txt`.
