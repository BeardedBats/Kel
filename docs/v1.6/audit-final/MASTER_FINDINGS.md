# MASTER_FINDINGS — Campaign B (canonical ledger, FINAL)

Audit target: `08f56673ea93ed84568018937bb190e0a5acd71b` (immutable; independently verified)
Audit branch: `audit/v16-final` — audit records only; **no production fixes** (Campaign C owns repair).
Field standard: ID · severity (final) · title · subsystem · requirements · invariants · commits/files/symbols · reproduction · evidence · expected · actual · confidence · root-cause hypothesis · adjacent risk · repair acceptance criteria · required regression test · Campaign C status.

## Summary (FINAL)
**AUD-BLOCK: 0 · AUD-MAJOR: 2 · AUD-MINOR: 9 · AUD-SUG: 1.**
Severity re-evaluation pass complete (`19_SEVERITY_REVIEW.md`): no label changed by inertia; two promotion criteria recorded (malicious-frame IPC control; runtime budget-claiming probe). External gates remain (human visual; codex client; internal/deepseek credentials).

---

## AUD-MAJOR-001 — Chat-approval conversation scoping is opt-in: an undeclared caller can settle any conversation's approval; the APR-02 "FIXED" claim is not enforced at the engine boundary

- **Severity (final):** AUD-MAJOR · **Status:** RECORDED (reproduced; root-caused) · **Subsystem:** engine approvals (chat surface) / conversation isolation
- **Requirements:** REQ-APR-1, REQ-OWNERSHIP-PARITY, REQ-R25-R4 (absorbs APR-02); P2_P3 APR-02 row
- **Invariants:** INV-APPROVE-001/002, INV-AUTH-002; campaign §16 ("wrong conversation … refused")
- **Commits/files/symbols:** `8a677d0` (APR-02 fix), `8c899c8` (R4), `dd34ac2`; `runtime/kel/chat_approvals.py` (`resolve()`, `_require_owned()`); `runtime/kel/service.py` (`/api/approvals` ~687, `/api/approval` singular ~628); `KelService.ts` allowlist (optional `?conversation=`)
- **Expected:** resolution of another conversation's approval is refused regardless of caller; omission of the conversation parameter must not bypass ownership.
- **Actual:** `resolve(..., conversation=None)` skips `_require_owned` entirely (`if conversation:`). A no-conversation caller **resolved a foreign conversation's approval to `approved`**; declared-foreign callers are refused; the singular route resolves by id with no scoping at all (dormant; no UI caller found). UI call sites do declare (`KelWorkPanel.tsx:275`, `KelApprovalCard.tsx:146`).
- **Reproduction:** `cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_1.py` §A (A2/A6 → no error + `state: approved`); code anchors above.
- **Evidence:** `evidence/auditor-probe-1.log`; P2_P3_DISPOSITION APR-02 row.
- **Confidence:** HIGH (module-layer repro + route pass-through read) · **Root cause hypothesis:** the APR-02 repair added ownership as an optional backward-compatible parameter ("additive") instead of enforcing scope on the write path by default (read path defaults `'main'`; write path defaults unscoped).
- **Adjacent risk:** same additive pattern elsewhere (vetting defaults `'main'` fail-closed; transcription stream calls still undeclared — documented). Audit the pattern anywhere scope is caller-optional.
- **Repair acceptance criteria:** enforce ownership unconditionally (required param or default `'main'` consistent with reads); omission + cross-conversation refused with the existing sentence; decide the singular route (scope or remove); UI behavior unchanged.
- **Regression test:** engine test — foreign/no-conversation resolution refused at chat module AND service layers, incl. hostile omission case.
- **Campaign C:** `REPAIRED` — repair commit: `44aee9f` · re-test: focused 28/28 (`test_v16_approvals.py`), adjacent 129/129, probe-1 §A replay refused (omission no longer settles a foreign approval; `main`-parity kept) · final re-audit: `PENDING`

---

## AUD-MAJOR-002 — Privileged IPC surface lacks sender validation across multiple channels, including a generic bridge dispatcher into donor bridge methods

- **Severity (final):** AUD-MAJOR · **Status:** RECORDED (code-verified; no Electron harness for an empirical subframe control — same limitation the corpus records at §58) · **Subsystem:** desktop main/renderer boundary
- **Requirements:** INV-IPC-001 closure claim; INT-01 class; §26 donor sweep
- **Invariants:** INV-IPC-001, INV-BRAND-001 (surface hygiene)
- **Commits/files/symbols:** `KelService.ts` (8 guarded channels; unguarded `kel:credential-status` :594, `kel:credential-set` :595-607, `kel:credential-delete` :608-616); `feedbackBridge.ts` (`feedback:collect-logs` :52 returns log bytes; `feedback:capture-screenshot` :76); `index.ts` sendSync (`get-backend-port`, `get-initial-language`, `get-backend-startup-*` :255-269; `backend:recover-corrupted-database` :271); `common/adapter/main.ts` (`ADAPTER_BRIDGE_EVENT_KEY` generic dispatcher → donor bridge provider map incl. `app.update-cdp-config`, `app.clear-browser-data`, `app.set-start-on-boot`, `update.download`, `auto-update.quit-and-install`, `shell.openExternal`, `app.set-zoom-factor`, `skills.files.*`) reachable via `preload/main.ts` `electronAPI.emit`.
- **Expected:** a uniform privileged-IPC boundary — every privileged channel validates the sender frame (only the app's own main frame may act).
- **Actual:** validation is partial: 8 of 11 Kel channels; 0 of 2 feedback channels; 0 sendSync handlers; generic dispatcher unvalidated. Electron runs preload in subframes, and artifact preview renders iframes/webviews (`HTMLRenderer`, `WebviewHost`, `OfficeWatchViewer`, `PDFViewer`), so the exposed bridge can exist in non-main frames; the eight guarded channels show the intended control.
- **Reproduction:** static read of the files above; no harness run (recorded).
- **Evidence:** file/line anchors in this sheet; `13/15` docs.
- **Confidence:** HIGH for missing guards; MEDIUM-HIGH for subframe reachability (Electron semantics + code; unexecuted control).
- **Root cause hypothesis:** security closure applied per-handler during W-sweeps instead of via one shared sender-validation helper installed across the whole privileged surface (new channels re-opened gaps).
- **Adjacent risk:** donor bridge methods with system effects (CDP config, browser data clearing, installer download/quit-install, openExternal) as the highest-blast-radius reachable set.
- **Repair acceptance criteria:** one shared, tested sender-validation helper on every privileged channel (Kel trio + feedback pair + sendSync handlers + recovery channel + adapter dispatcher); decide whether the generic dispatcher is needed for Kel at all; per-channel regression list.
- **Regression test:** unit tests asserting rejection for spoofed sender per channel; subframe control (empirical) where feasible.
- **Campaign C:** `REPAIRED` — repair commit: `eaf7bad` · re-test: desktop vitest 147/147 (25 new: guard truth table + per-channel refusals), tsc exit 0, pre-fix stash replay fails on the in-place channels · final re-audit: `PENDING`

---

## AUD-MINOR-001 — COMMIT_LEDGER completeness failures (4 unlisted commits; 2 malformed rows; RC packaging edits unaccounted)

- **Severity (final):** AUD-MINOR · **Status:** RECORDED (mechanical reconciliation complete) · **Subsystem:** audit/evidence corpus · **Req:** RL-03; campaign §5
- **Commits:** `022f3ac` (test), `0aadd42` (docs; row says "HEAD", wrong parent `93b99b5`), `34947f0` (feat; `KelService.ts` +10), `12f87a7` (docs); `08f5667` (RC; docs + `kel-builder.json`/`package.json` packaging edits) unaccounted; row "R6 tests+record" lacks SHA (`e8bbb05`).
- **Expected/Actual:** ledger reconciles `git rev-list 8a2b25d..08f5667` 1:1 / four commits unlisted, two malformed rows, packaging edits unaccounted.
- **Evidence:** `evidence/ledger-vs-git.txt`, `commit-classification.tsv`, `git show` outputs. **Confidence:** HIGH (mechanical).
- **Repair criteria:** ledger reconciles 1:1; no placeholder SHA cells; production-affecting exceptions documented; scripted reconciliation gate.
- **Regression test:** reconciliation script fails on any unlisted/malformed row (already prototyped: `tools/classify-commits.py`).
- **Campaign C:** `NOT_STARTED`.

## AUD-MINOR-002 — Budget reservations are not integrated with job budget accounting (cumulative overcommit); token/wallclock caps absent (disclosed)

- **Severity (final):** AUD-MINOR (effect-reachability reviewed: serialized claim path caps real spend; overcommit is planning-impact) · **Status:** RECORDED (reproduced) · **Subsystem:** workforce/delegation budget · **Req:** REQ-R25-R1 · **Invariant:** INV-AUTH-001 (budget dimension)
- **Files:** `runtime/kel/assignment.py` (`reserve_budget`), `runtime/kel/core.py` (`reserved` accounting) · **Commit:** `dc65fbc`
- **Expected:** cumulative Phase-5.3 reservations cannot sum beyond `job.budget − spent − reserved`. **Actual:** envelope check never aggregates `budget_reservations` into `job.reserved`; reservation cost 1 accepted then cost 8 with envelope 8 (cumulative 9); tokens=1e12/wallclock=1e7 accepted single-shot (non-enforcement disclosed in `increments/R1-AUTHORITY-CEILING.md` ~105; the cumulative gap is not).
- **Reproduction:** probe-1 E5–E7. **Evidence:** `evidence/auditor-probe-1.log`. **Confidence:** HIGH. **Root cause:** two parallel reservation systems without aggregation.
- **Adjacent risk:** consumers of `job.reserved` see incomplete accounting. **Repair criteria:** aggregate active reservations (or update `job.reserved` on reserve/release); reject sums > remaining; docs; tests for cumulative + token/wallclock policy.
- **Regression test:** cumulative-overcommit test; multi-reservation per job. **Promotion criterion (Campaign C):** runtime claiming probe — if actual spend can cross the envelope, re-grade.
- **Campaign C:** `REPAIRED` — repair commit: `7e293ba` · re-test: cumulative suite 9/9 (5 fail pre-fix), focused 65/65, workforce cluster 299/299, probe §E7 replay refused · promotion probe: actual spend capped at the envelope (no re-grade) · final re-audit: `PENDING`

## AUD-MINOR-003 — `native.child_env` claims weaker stripping than it performs: unrelated provider keys reach native CLI children

- **Severity (final):** AUD-MINOR (environs-only propagation observed; no exfiltration demonstrated; two primary providers spawn children) · **Status:** RECORDED (reproduced with sentinels) · **Subsystem:** credentials/native providers · **Req:** REQ-R25-R7 · **Invariant:** INV-CRED-001
- **Files:** `runtime/kel/native.py` (`child_env`, docstring) vs `runtime/kel/internal.py` (whitelist `child_env(keep=…)`).
- **Expected:** "A native child receives at most its own provider's credentials…" **Actual:** only the named counterpart key is popped — `DEEPSEEK_API_KEY` reaches both `codex` and `claude` children; internal whitelist path correct; `redact` works.
- **Reproduction:** probe-1 §G (G1–G4). **Evidence:** `evidence/auditor-probe-1.log`. **Confidence:** HIGH.
- **Adjacent risk / follow-through:** sentinel trace through logs/prompts/artifacts/CompletionPackets showed environs presence only; tool policy + `fetch/network` refusals reduce exfiltration reach (deepening recorded in this pass).
- **Repair criteria:** per-provider strip map (or align docstring to documented native-env policy); test for third-provider key absence. **Regression test:** env-content test for both native children.
- **Campaign C:** `REPAIRED` — repair commit: `91bd869` · re-test: credential suite 9/9 (3 new fail pre-fix), cluster 34/34, probe §G G4 replay (DeepSeek absent from both children) · final re-audit: `PENDING`

## AUD-MINOR-004 — R12 packaged-evidence integrity gaps (non-discriminating probe exit; uninstall evidence absent; pre-RC integrity snapshot)

- **Severity (final):** AUD-MINOR · **Status:** RECORDED (verified) · **Subsystem:** release evidence · **Req:** REQ-PKG-ASSERT, REQ-R25-R12; campaign §22/§28
- **Items:** (a) `ux-audit/r12-installed-probe.cjs` exits 0 unconditionally on the happy path (`process.exit(0)` after JSON write; only a caught exception exits 1) — `r12-fresh` exited 0 with `attentionVisible:false` + `aboutLogoLoaded:false`; PASS leans on `r12-fresh2`. (b) No uninstall evidence retained anywhere. (c) `r12-integrity.txt` captured at `12f87a7` with `M desktop/kel-builder.json` + `M desktop/package.json` under an "expect empty" header; no post-RC re-run; script records but never fails. (d) r10-f "2 ms" per-attempt timings not retained (load-bearing timings ARE; addendum folded here). (e) No build log/command for RC `package-r12` retained; documented generic command cannot produce NSIS from committed `win.target=["dir"]` — exact invocation unreconstructable (auditor rebuild mirrors with `-c.win.target=nsis`).
- **Evidence:** probe script lines 100-157; `r12-integrity.txt`; install script; directory listings. **Confidence:** HIGH.
- **Repair criteria:** probe exit gates on assertions; uninstall run logged+retained; release-integrity re-run enforced at final RC head; package build command+log retained; doc wording corrected to retained evidence.
- **Regression test:** probe returns non-zero on failed assertions; integrity script `--fail-on-dirty`.
- **Campaign C:** `NOT_STARTED`.

## AUD-MINOR-005 — Corpus state drift not reconciled at RC (statuses/rows contradict the delivered tree)

- **Severity (final):** AUD-MINOR · **Status:** RECORDED (verified samples; itemized) · **Subsystem:** audit corpus accuracy · **Req:** campaign §4/§5
- **Items:** (1) `INVARIANT_LEDGER.md` stale statuses (INV-AUTH-001 "PLANNED (R1)"; INV-IDEM-001/EFFECT-001/RETRY-001 "PLANNED"; INV-APPROVE-001 "PARTIAL (APR-01..03)" though 01/02 fixed/03 deferred; INV-ERROR-001 "OPEN_GAP" though PER-02/03 fixed; INV-WF-005 "PARTIAL" though F4 delivered `081a6ef`; INV-IPC-001 OPEN_GAP though INT-01 fixed; INV-UI-001, INV-CRED-001, INV-MEM-001 stale). (2) `MIGRATION_LEDGER.md` "Next free version: 20" vs max **21**; RC checkboxes unchecked though packaged boots ran. (3) `REQUIREMENTS_TRACEABILITY.md` R9/R11/R12 "PENDING" though delivered; RUST "re-verified open"; PKG-ASSERT pending; REQ-WFWIRE pending (scope decision open). (4) `AUDIT_HANDOFF.md` TBD cells. (5) `docs/v1.6-visual-ux/00_STATUS.md` stale in RC tree. (6) P2_P3 "27 vs 26" explainable only on careful read (worklist arithmetic).
- **Evidence:** direct reads at RC; `assignment.py:39` (v21); packaged DB queries (fresh/upgrade max 21). **Confidence:** HIGH.
- **Repair criteria:** every status/table row reconciled to the RC tree or marked historical; zero unchecked satisfied claims.
- **Regression test:** corpus-lint (grep-able stale-marker denylist) run at RC head.
- **Campaign C:** `NOT_STARTED`.

## AUD-MINOR-006 — Delegation containment primitive does not resolve `..`: `src/../secrets` counts as within `src`

- **Severity (final):** AUD-MINOR (no consumer-confirmed filesystem crossing; primitives resolve natively under the worktree) · **Status:** RECORDED · **Subsystem:** workforce/contracts (`_path_within` / `authority_within`) · **Req/invariants:** AUTH-DELEGATION (INV-AUTH-001); campaign attack target 62
- **Expected:** a child scope lexically escaping the delegator scope (via `..`) is refused. **Actual:** `authority_within({'write_scope': ['src/../secrets']}, {'write_scope': ['src']})` → contained (`None`); `_path_within` normalizes `./` + separators, never resolves `..`; `.` as parent root universal by design; `..` alone refused.
- **Reproduction:** inline probe 2026-09-19; `runtime/kel/workforce.py` source read. **Evidence:** thread transcript + this ledger. **Confidence:** HIGH (primitive), MEDIUM (consumer impact).
- **Adjacent risk:** any future consumer treating scope strings as real boundaries inherits the gap. **Repair criteria:** resolve `..` lexically or refuse `..` segments; document `.` semantics; tests `src/../x`, `a/../../x`, mixed separators. **Promotion criterion:** consumer runtime confirmation (Campaign C).
- **Regression test:** primitive table + one end-to-end contract refusal. **Campaign C:** `REPAIRED` — repair commit: `c056a8a` · re-test: 4/4 (3 fail pre-fix), focused 26/26, cluster 303/303, inline replay refused · final re-audit: `PENDING`

## AUD-MINOR-007 — Donor-derived `aioncore` runtime is live and shipped; no corpus disposition found (binary staged from cache)

- **Severity (final):** AUD-MINOR (presence+viability proven; Kel-code reachability not established; legal attribution present) · **Status:** RECORDED · **Subsystem:** desktop runtime / package / donor sweep
- **Evidence:** `desktop/packages/desktop/src/index.ts:36` imports `BackendLifecycleManager` from `@aionui/web-host`; `:235` constructs it; `process/backend/binaryResolver.ts` resolves `bundled-aioncore/{platform-arch}/aioncore[.exe]`; RC resources contain `bundled-aioncore/`; real run data `host/aionui/**` (r10-f timestamps); vitest covers the launcher (mocked `AIONCORE_LISTENING`); build flow calls `prepareAioncore(...)` (`scripts/build-with-builder.js` step 5); `kel-builder.json` ships `LICENSE → AIONUI-LICENSE.txt` — intentional, config-driven packaging input; `AionUI-LICENSE.txt` present in package.
- **Expected/Actual:** every shipped binary bound to source/revision with a disposition / live donor-named runtime shipped, disposition + provenance binding absent (binary staged from cache; stock binary not in git).
- **Confidence:** HIGH (presence/wiring), MEDIUM-HIGH (import-graph reachability from Kel paths; launcher startup not observed live). **Adjacent risk:** un-vetted runtime process surface.
- **Repair criteria:** bind bundled binary to revision + hash; decide keep/rename/remove; record disposition; refresh donor sweep; security read of what starts it.
- **Regression test:** build assertion (provenance manifest) + reachability note in sweep.
- **Campaign C:** `NOT_STARTED`.

## AUD-MINOR-008 — Donor desktop-pet subsystem is wired into the shipped app (no disposition found)

- **Severity (final):** AUD-MINOR · **Status:** RECORDED · **Subsystem:** desktop
- **Evidence:** `src/index.ts:1067` `createPetWindow`; `systemSettingsBridge.ts` pet APIs; `process/pet/petManager.ts`, `petStateMachine.ts`, `pet-confirm.html`; `resources/pet-states/*.svg` shipped in RC.
- **Expected/Actual:** V1.6 surfaces are Kel's (donor features removed or intentionally kept with recorded decision) / no disposition found; settings API reachable; window start requires a host-side call; donor assets+behavior shipped.
- **Confidence:** HIGH (wiring/assets), MEDIUM (end-user UI reachability not fully traced). **Adjacent risk:** un-vetted donor UI/process surface; brand/behavior leakage.
- **Repair criteria:** decide keep/hide/remove; if kept — disposition row; if hidden — prove unreachable. **Regression test:** surface-reachability list in the donor sweep.
- **Campaign C:** `NOT_STARTED`.

## AUD-MINOR-009 — Donor builder config remains the default build path (`electron-builder.yml`: appId com.aionui.app, productName AionUi)

- **Severity (final):** AUD-MINOR (Kel identity verified in all produced artifacts; risk is wrong-default misuse) · **Status:** RECORDED · **Subsystem:** packaging/build tooling (donor residual)
- **Evidence:** `desktop/packages/desktop/electron-builder.yml` (`appId: com.aionui.app`, `productName: AionUi`) is the only config referenced by `scripts/build-with-builder.js` (used by `bun run build`/`dist:win`; fallbacks hardcode `AionUi.exe`); Kel packages only when `--config kel-builder.json` is explicit; auditor build log confirms kel-builder.json loaded as the effective config (and donor yml merged as parent).
- **Expected/Actual:** one obvious production build path / default scripts build a donor-branded app; Kel config is a side path; `bun run dist:win` would emit `AionUi`-named artifacts.
- **Confidence:** HIGH. **Adjacent risk:** CI/maintainer misuse; donor identity regression in future packages.
- **Repair criteria:** make Kel config default (or remove donor scripts/names); single packaging config; build-identity assertion (productName/appId) in CI.
- **Regression test:** artifact metadata assertion step. **Campaign C:** `NOT_STARTED`.

## AUD-SUG-001 — Capability directive docstring vs behavior for unquoted log-line/path tokens

- **Severity (final):** AUD-SUG · **Status:** RECORDED · **Subsystem:** `capabilities.py`
- **Evidence:** `directive_clauses('GET /a/[kel:web=off] 200')` → matched; quoted/code/fenced/nested/word-embedded/scheme-URL/unknown-capability/malformed-state all inert; mixed-case + punctuation-adjacent recognition BY DESIGN (`tests/test_capabilities.py:163-180, 321-325`); long-paste guard returns [] >2000 chars (`capabilities.py:447`).
- **Expected/Actual:** docstring's exclusion intent vs parser's reserved-token-wherever rule for bare unquoted technical strings.
- **Confidence:** HIGH (behavior), SUG-class. **Repair criteria:** extend exclusions or align docstring wording ("the exact reserved token fires wherever it appears outside quotes/code; scheme-URLs excluded"). **Regression test:** docstring-conformance table (accepted/rejected forms). **Campaign C:** `NOT_STARTED`.

---

## Verification summary (supporting)

- Engine suite re-run at RC: **998 passed + 10 subtests, exit 0**; desktop vitest **122/122** (`evidence/auditor-engine-suite.log`, `auditor-desktop-vitest.log`).
- Negative controls (discriminating): pre-APR-02 → 6F+1E; pre-R2 → 1F; pre-R4 → 1F (`17_TEST_QUALITY.md`).
- Frozen refs/engine identity: `main`=`5e76b21`; `v1.6.0-pre1^{}`=`f24d9c28`; candidate↔frozen byte-identity (pre1 `Kel.exe`); engine `69123af0…` == staged == packaged == installed.
- Brand: canonical sha256 `7418a42f…` == Desktop original == in-repo; 9 derivatives verified; check-mode exit 0.
- Auditor package: independent rebuild; install/reinstall/uninstall lifecycle clean; installed journey PASS; **engine-loss ladder PASS on installed build** (kill×2→recovered, kill#3→unrecoverable, manual→recovered; work preserved; 0 leaks/errors).
- Migrations: max **21** (`v16-budget-reservations`) across constants + packaged fresh/upgrade stores.
- Corpus drift/rebuild notes retained in `14/15`; no production file was modified by this audit at any point.

## Campaign C handoff (final)

Repair set: **AUD-MAJOR-001, AUD-MAJOR-002, AUD-MINOR-001…009, AUD-SUG-001.** Priority: MAJOR-001 (authority path) → MAJOR-002 (prerequisite-tight, uniform IPC guard) → MINOR-002/003/006 (real-effect reachability checks) → evidence/corpus items. Every finding carries repair criteria + a required regression test. Campaign C owns ALL repairs; nothing was repaired during Campaign B; the RC target never moved.
