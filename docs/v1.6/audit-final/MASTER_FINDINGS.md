# MASTER_FINDINGS — Campaign B (canonical ledger)

Audit target: `08f56673ea93ed84568018937bb190e0a5acd71b` (immutable; independently verified)
Audit branch: `audit/v16-final` — audit records only; no production fixes (Campaign C owns repair).
Severities: `AUD-BLOCK` / `AUD-MAJOR` / `AUD-MINOR` / `AUD-SUG`. Status: `RECORDED` → `UNDER_VERIFICATION` → `CONFIRMED` / `DISMISSED`.
Campaign C fields start `NOT_STARTED`/blank. Findings are recorded, never repaired here.

## Summary (as of this revision)
- AUD-BLOCK: 0 · AUD-MAJOR: 1 · AUD-MINOR: 8 · AUD-SUG: 1
- In verification (NOT findings yet): `_path_within` `..`-escape & case/prefix tricks; capability technical-string recognition (bare path/log-line); r10 timing-precision wording; donor-residual classification (AionUI description/email, bundled-aioncore, web-host `aioncore` launcher reachability); visual screenshot-count arithmetic; mail `docs/v1.6-visual-ux/00_STATUS.md` staleness; `next free version` drift (folded into AUD-MINOR-005 items).

---

## AUD-MAJOR-001 — Chat-approval conversation scoping is opt-in: an undeclared caller can settle any conversation's approval; the APR-02 "FIXED" claim is not enforced at the engine boundary

- **Severity:** AUD-MAJOR (cross-conversation authority path; repair before release)
- **Status:** RECORDED (reproduced; mechanism root-caused)
- **Subsystem:** engine approvals (chat surface) / conversation isolation
- **Requirement IDs:** REQ-APR-1, REQ-OWNERSHIP-PARITY, REQ-R25-R4 (absorbs APR-02); P2_P3 APR-02 row
- **Invariant IDs:** INV-APPROVE-001/002, INV-AUTH-002 (live authority), campaign §16 ("wrong conversation … refused")
- **Affected commits:** `8a677d0` (APR-02 fix), `8c899c8` (R4), `dd34ac2` (v20 marker); RC range generally
- **Affected files/symbols:** `runtime/kel/chat_approvals.py` (`resolve()`, `_require_owned()`); `runtime/kel/service.py` (`_action` `/api/approvals`, `_action` `/api/approval` singular); `desktop/.../KelService.ts` route allowlist (optional `?conversation=`)
- **Claim challenged:** "The chat approval surface now refuses a resolution whose record belongs to a different conversation — a stale or crafted id cannot settle work the caller is not looking at" (APR-02 disposition / P2_P3; chat_approvals docstring "uses the same ownership set").
- **Expected:** resolution of another conversation's approval is refused regardless of caller; at minimum, omitting the conversation parameter must not bypass ownership.
- **Actual:** `resolve(..., conversation=None)` skips `_require_owned` entirely (`if conversation:`). Reproduced: a no-conversation caller **resolved a foreign conversation's approval to `approved`** (probe `evidence/auditor-probe-1.log` A2/A6; ids in log). Declared-foreign callers ARE refused (A1/A5). The engine route passes `conversation=data.get('conversation')` through verbatim (`service.py` ~687). Desktop UI call sites do declare (`KelWorkPanel.tsx:275`, `KelApprovalCard.tsx:146`) — but the bridge allowlist accepts `/api/approvals` without `conversation`, and the singular `/api/approval` route resolves by id with **no scoping at all** (`service.py` ~628; no current UI caller found = dormant), so the enforcement is caller-opt-in, not engine-enforced.
- **Reproduction:** `cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_1.py` §A (A2/A6 show NO ERROR + `state: approved`); code anchors above.
- **Evidence:** `evidence/auditor-probe-1.log`; code quotes in this sheet; P2_P3_DISPOSITION APR-02 row; probe source in `probes/auditor_probe_1.py`.
- **Environment:** audit worktree @ `08f56673`; Python 3.14.3 (system), Windows.
- **Root cause:** the APR-02 repair added the ownership check as an optional, backward-compatible path parameter ("additive") instead of enforcing scope on the write path by default (read path defaults to `'main'`; write path defaults to unscoped).
- **Confidence:** HIGH (reproduced at module layer; route pass-through read directly).
- **Adjacent risk:** same additive pattern used for transcription/vetting (REQ-OWNERSHIP-PARITY row itself notes "desktop stream calls do not declare a conversation yet"). Vetting defaults to `'main'` on omission (fail-closed) — chat approvals do not. Audit the same pattern anywhere else.
- **Repair acceptance criteria:** resolve must enforce ownership unconditionally (require the parameter, or default it to `'main'` consistently with the read path); omission + cross-conversation is refused with the existing sentence; decide `/api/approval` singular (scope it or remove it as dead surface); keep UI behavior unchanged.
- **Regression test required:** engine test: foreign/no-conversation resolution refused at both the chat module and service layers; omission case in the hostile suite.
- **Campaign C:** repair status `NOT_STARTED` — repair commit: — · re-test: — · final re-audit: —

---

## AUD-MINOR-001 — COMMIT_LEDGER completeness failures (4 unlisted commits; 2 malformed rows; RC packaging edits unaccounted)

- **Severity:** AUD-MINOR · **Status:** RECORDED (mechanical reconciliation complete)
- **Subsystem:** audit/evidence corpus · **Req:** RL-03; campaign §5
- **Commits:** `022f3ac` (test), `0aadd42` (docs; ledger row says "HEAD" with wrong parent `93b99b5`), `34947f0` (feat; production — `KelService.ts` +10), `12f87a7` (docs); `08f5667` (RC) is docs-plus-packaging (`desktop/kel-builder.json` output dir; `desktop/package.json` companyName/author) and is not accounted anywhere; row "R6 tests+record" lacks its SHA (`e8bbb05`).
- **Evidence:** `evidence/ledger-vs-git.txt`; `commit-classification.tsv`; `git show` outputs.
- **Repair criteria:** ledger reconciles `git rev-list 8a2b25d..08f5667` 1:1; no placeholder SHA cells; production-affecting exceptions documented; keep a scripted reconciliation gate.
- **Campaign C:** `NOT_STARTED` — — · — · —

---

## AUD-MINOR-002 — Budget reservations are not integrated with job budget accounting (cumulative overcommit); token/wallclock caps absent (disclosed)

- **Severity:** AUD-MINOR (resource-accounting invariant, partially disclosed)
- **Status:** RECORDED (reproduced)
- **Subsystem:** workforce/delegation budget · **Req:** REQ-R25-R1; campaign targets 61–66 ("budget")
- **Invariants:** INV-AUTH-DELEGATION (budget dimension)
- **Commits/files:** `dc65fbc`; `runtime/kel/assignment.py` (`reserve_budget`), `runtime/kel/core.py` (`reserved` accounting)
- **Claim challenged:** "the job envelope is the delegator's budget authority, so a delegated reservation may narrow it, never create more" (in-code comment) / R1 row "reserve_budget envelope check".
- **Expected:** cumulative Phase-5.3 reservations cannot sum beyond `job.budget − spent − reserved`.
- **Actual:** `reserve_budget` checks `job.budget − spent − reserved` but **never updates `job.reserved`** from the `budget_reservations` table, so each call sees the same remaining and multiple reservations exceed the envelope. Reproduced: reservation cost 1 accepted, then cost 8 accepted with envelope 8 (cumulative 9); tokens=1e12, wallclock=1e7 accepted in a single reservation (probe E6/E7). Token/wallclock non-enforcement is **explicitly disclosed** in `increments/R1-AUTHORITY-CEILING.md` (~line 105); the cumulative non-accounting is not.
- **Evidence:** `evidence/auditor-probe-1.log` E5–E7; `assignment.py` `reserve_budget` body.
- **Root cause:** two parallel reservation systems (`core` run-cycle reserved counter vs Phase-5.3 `budget_reservations`) with no aggregation between them.
- **Confidence:** HIGH. **Adjacent risk:** milestone-boundary enforcement still caps actual spend on the core cycle — practical impact is planning overcommit (recheck consumers in Campaign C).
- **Repair criteria:** aggregate active reservations into the envelope check (or update `job.reserved` on reserve/release); reject reservation sums > remaining; update docs; tests for cumulative + token/wallclock policy.
- **Regression test:** cumulative-overcommit test; multi-reservation per job.
- **Campaign C:** `NOT_STARTED` — — · — · —

---

## AUD-MINOR-003 — `native.child_env` claims weaker-stripping than it performs: unrelated provider keys reach native CLI children

- **Severity:** AUD-MINOR · **Status:** RECORDED (reproduced)
- **Subsystem:** credentials/native providers · **Req:** REQ-R25-R7; campaign target 82
- **Invariants:** INV-CRED-001 · **Files:** `runtime/kel/native.py` (`child_env`, docstring), vs `runtime/kel/internal.py` (`child_env(keep=…)`, whitelist)
- **Claim:** "A native child receives at most its own provider's credentials; Kel-managed keys for other providers are never forwarded into it."
- **Actual:** only the named counterpart key is popped; other provider credentials pass through — `DEEPSEEK_API_KEY` reaches both `codex` and `claude` children (probe G4). `internal.child_env` (Kel-managed keys) correctly strips with a whitelist (G1/G2); `redact` works (G3).
- **Evidence:** `evidence/auditor-probe-1.log` §G. **Confidence:** HIGH (env content printed; sentinels used). The R7 row discloses generic env inheritance for engine-local helpers — the native-CLI case is narrower and contradicts the docstring.
- **Repair criteria:** strip per-provider map (or explicitly document native children keep the user env except other providers' keys, and align the docstring); add test for third-provider key absence.
- **Campaign C:** `NOT_STARTED` — — · — · —

---

## AUD-MINOR-004 — R12 packaged-evidence integrity gaps (non-discriminating probe exit; uninstall evidence absent; pre-RC integrity snapshot)

- **Severity:** AUD-MINOR · **Status:** RECORDED (verified)
- **Subsystem:** release evidence · **Req:** REQ-PKG-ASSERT, REQ-R25-R12; campaign §22/§28
- **Items:** (a) `ux-audit/r12-installed-probe.cjs` exits `0` unconditionally on the happy path (`process.exit(0)` after writing the JSON; only a caught exception exits 1) — `runs/r12-fresh` exited 0 with `attentionVisible:false` + `aboutLogoLoaded:false`; the PASS disposition leans on `r12-fresh2` (booleans true). (b) No uninstall evidence is retained anywhere; the install script only comments that cleanup is "cleaned up with the uninstaller afterwards"; `runs/r12-installed` is empty after removal. (c) `runs/r12-integrity.txt` was captured at `12f87a7` with `M desktop/kel-builder.json` + `M desktop/package.json` present under a header that says "expect empty"; the script records but never fails on unexpected state, and no post-RC (08f5667) re-run is retained.
- **Evidence:** probe script lines 100–157; `r12-integrity.txt`; install script; directory listings.
- **Repair criteria:** probe exit code gates on its assertions; uninstall run logged (registry/shortcuts/dir) and retained; release-integrity re-run at the final RC head with enforcement.
- **Campaign C:** `NOT_STARTED` — — · — · —

---

## AUD-MINOR-005 — Corpus state drift not reconciled at RC (statuses/rows contradict the delivered tree)

- **Severity:** AUD-MINOR · **Status:** RECORDED (verified samples; itemized)
- **Subsystem:** audit corpus accuracy · **Req:** campaign §4/§5 (claims vs reality)
- **Items (verified):** (1) `INVARIANT_LEDGER.md` status column stale for delivered work: INV-AUTH-001 "PLANNED (R1)", INV-IDEM-001/ EFFECT-001/ RETRY-001 "PLANNED", INV-APPROVE-001 "PARTIAL (open APR-01..03)" (APR-01/02 fixed; APR-03 deferred), INV-ERROR-001 "OPEN_GAP (PER-02/PER-03)" (both fixed), INV-WF-005 "PARTIAL (F4 open)" (F4 delivered `081a6ef`), INV-IPC-001 "OPEN_GAP (INT-01)" (fixed), INV-UI-001 "OPEN_GAP" (closed), INV-CRED-001, INV-MEM-001. (2) `MIGRATION_LEDGER.md`: table ends at 19 with "Next free version: 20" while max is **21** (verified from constants + packaged DBs max 21); RC checklist checkboxes remain unchecked though packaged boots ran. (3) `REQUIREMENTS_TRACEABILITY.md` stale rows: R9/R11/R12 "PENDING" though delivered; RUST row says "re-verified open" post-fixes; PKG-ASSERT PENDING though R12 battery ran; REQ-WFWIRE PENDING with no later row (needs a scope decision). (4) `AUDIT_HANDOFF.md` TBD cells remain. (5) `docs/v1.6-visual-ux/00_STATUS.md` stale copy in the RC tree. (6) P2_P3 §reconciliation explains "27" as worklist arithmetic while other prose insists "26 canonical" — consistent only if read carefully; see AUD doc for line-level notes.
- **Evidence:** direct file reads at RC; constants grep (`assignment.py:39` v21); packaged DB queries (`r12-fresh2`/`r12-upgrade` max 21).
- **Repair criteria:** every status/table row reconciled to the RC tree or explicitly marked historical; no unchecked claim remains that the tree satisfies.
- **Campaign C:** `NOT_STARTED` — — · — · —

---

## Campaign C handoff (running)
Repair set so far: `AUD-MAJOR-001`, `AUD-MINOR-001` … `AUD-MINOR-008`, `AUD-SUG-001`. Nothing repaired in Campaign B; the RC target is unchanged.

### AUD-MINOR-006 — Delegation containment primitive does not resolve `..`: `src/../secrets` counts as within `src`

- **Severity:** AUD-MINOR · **Status:** RECORDED · **Subsystem:** workforce/contracts (`_path_within` / `authority_within`)
- **Req/invariants:** AUTH-DELEGATION (INV-AUTH-001); campaign attack target 62 (path tricks).
- **Claim challenged:** "delegation may narrow authority, never create it" — the executable primitive itself.
- **Expected:** a child scope/boundary that lexically escapes the delegator scope (via `..`) is refused.
- **Actual:** `authority_within({'write_scope': ['src/../secrets']}, {'write_scope': ['src']})` -> `None` (contained). `_path_within` normalizes `./` and separators but never resolves `..` (runtime/kel/workforce.py). `.` as a parent root is universal by design (open question (4) in the R1 increment); `..` alone IS refused.
- **Repro:** inline probe 2026-09-19 (thread transcript); `_path_within` source read.
- **Impact:** any consumer treating `write_scope`/`write_boundaries` as a real boundary inherits a normalization gap; no consumer-confirmed filesystem effect established yet (consumer analysis queued).
- **Repair criteria:** resolve `..` lexically or refuse segments containing `..`; document `.` semantics; tests for `src/../x`, `a/../../x`, mixed separators.
- **Campaign C:** `NOT_STARTED` — — · — · —

### AUD-MINOR-007 — Donor-derived `aioncore` runtime is live and shipped; no corpus disposition found (binary staged from cache)

- **Severity:** AUD-MINOR · **Status:** RECORDED · **Subsystem:** desktop runtime / package / donor sweep
- **Evidence:** `desktop/packages/desktop/src/index.ts:36` imports `BackendLifecycleManager` from `@aionui/web-host`; `:235` constructs it; `process/backend/binaryResolver.ts` resolves `bundled-aioncore/{platform-arch}/aioncore[.exe]`; RC resources contain `bundled-aioncore/`; real run data contains `host/aionui/**` (skills + node runtime caches; r10-f timestamps during the journey); vitest covers the launcher (mocked `AIONCORE_LISTENING`).
- **Claim challenged:** §26 donor sweep completeness; INV-PACKAGE-001 provenance ("bundled-aioncore staged from cache (stock binary not in git)") — no revision/hash binding of the shipped binary found in the read corpus.
- **Expected:** every shipped binary has source/revision binding; donor-named runtime surfaces carry a disposition (keep/rename/remove).
- **Actual:** live donor-named runtime shipped; `AionUI-LICENSE.txt` present (legal attribution — allowed).
- **Repair criteria:** bind the bundled binary to a revision + hash; decide keep/rename/remove; record disposition; refresh donor sweep.
- **Campaign C:** `NOT_STARTED` — — · — · —

### AUD-MINOR-008 — Donor desktop-pet subsystem is wired into the shipped app (no disposition found)

- **Severity:** AUD-MINOR · **Status:** RECORDED · **Subsystem:** desktop
- **Evidence:** `src/index.ts:1067` `createPetWindow`; `systemSettingsBridge.ts` pet APIs; `process/pet/petManager.ts`, `petStateMachine.ts`, `pet-confirm.html`; `resources/pet-states/*.svg` shipped in the RC.
- **Expected:** V1.6 surfaces are Kel's; donor features removed or intentionally kept with a recorded decision.
- **Actual:** no disposition found in the read corpus; UI reachability not yet established (queue).
- **Repair criteria:** decide keep/hide/remove; if kept, a disposition row; if hidden, prove unreachable.
- **Campaign C:** `NOT_STARTED` — — · — · —

### AUD-SUG-001 — Capability directive docstring vs behavior for unquoted log-line/path tokens

- **Severity:** AUD-SUG · **Status:** RECORDED · **Subsystem:** `capabilities.py`
- **Evidence:** `directive_clauses('GET /a/[kel:web=off] 200')` → matched; quoted/code/fenced/nested/word-embedded/scheme-URL/unknown tokens all inert; punctuation-adjacent and mixed-case recognition are BY DESIGN (`tests/test_capabilities.py:163-180, 321-325`).
- **Suggestion:** extend exclusions or align the docstring wording ("the exact reserved token fires wherever it appears outside quotes/code; scheme-URLs excluded"). Wording/design-intent only; no failure count inflation.
- **Campaign C:** `NOT_STARTED` — — · — · —

### Addendum to AUD-MINOR-004 (item d)

- r10-f row claims per-attempt failure timings ("attempt 1 fails (2 ms) → attempt 2 fails (2 ms)") that are NOT retained in `ux-audit/runs/r10-f/**`; the load-bearing timings ARE retained (reconnect#1 00:09:35.236 → unrecoverable 00:09:40.249 ≈ 5.01 s; manual retry → recovered in 0.53 s).

