# Kel v1.6 program — auto-resume (continuation state)

> NOTE (2026-09-18): sections are chronological. The authoritative current state is
> `docs/v1.6/status/MAIN_STATUS.md` plus the NEWEST section in this file (Campaign A, at the end).
> Older paragraphs below are historical.

State at this writing: pre-program checkpoint frozen; program Phases 0–3 complete, verified, and
committed on `ux/v15-journeys`. **Phase 4 (i18n / donor-string cleanup) is PAUSED with its work
preserved in a git stash** — do not resume it until the program says so. A P1 capability remediation
(independent audit 1.6, REVISE) was implemented, verified, and committed as the latest commit on this
branch; its full record is in `docs/session-tools/` and the sections below.

## Frozen checkpoints (never touch either)

- Pre-program checkpoint: tag `v1.6.0-pre1` (annotated, commit `f24d9c2`, artifact source `0fb095f`),
  folder `Kel Releases\Kel-V1.6.0-Pre1-Frozen`, verifier 3/3, byte-identical to `package-final11`.
  Re-verified untouched on 2026-09-17 (4/4 hashes OK).
- Older frozen releases V1–V1.5: verified 3/3, byte-untouched.

## Program progress

| Phase | State | Evidence |
| --- | --- | --- |
| -1 Safety freeze | DONE | `docs/v1.6/00_CHECKPOINT_FREEZE.md` |
| 0 Session-tools closure | CLOSED | fresh 545-suite + packaged sessiontools 24/24 identical |
| 1 Memory proposal surface | DONE — commit `a8c3511` | `docs/memory-proposals/` (engine 568 then, packaged `memoryprops` green, review CONTINUE) |
| 2 Artifact lineage | DONE — commit `ffeef73` | `docs/artifact-lineage/` (engine 574, packaged lineage probe green on `package-final15`) |
| 3 In-chat approvals | DONE — commit `85e99fb` | `docs/in-chat-approvals/` (engine 592, packaged approvals journey all-green + lineage probe re-run on `package-final16`) |
| 3.5 P1 capability remediation | DONE — commit `75d1f68` | engine 604 (+10 subtests), packaged `sessiontools` on `package-p1cap` + packaged-engine capability probe all green (`ux-audit/run-p1-capabilities.sh`) |
| 3.6 CAP2-CLAUSE remediation | DONE — commit `327e5b2` | engine 610 (+10 subtests), packaged `sessiontools` (with bracket-clause steps) + CAP2 forwarded-text probe + engine regression on `package-p1cap2` (`ux-audit/run-cap2-clause.sh`) |
| 3.7 CAP2-RESIDUAL remediation | DONE — commit `631881a` | engine 613 (+10 subtests), packaged `sessiontools` (reserved-directive + residual steps) + residual forwarded-text probe + engine regression on `package-p1cap3` (`ux-audit/run-cap2-residual.sh`) |
| 4 i18n / donor-string cleanup | DONE — commit `fd04c00` (restored safely from the stash on `267364e`, then completed) | `docs/i18n-cleanup/00_STATUS.md`; locales 12× clean (0 residuals, 247 files valid); tsc 0, vitest 76; packaged `package-final17` copy-scan + standing journeys (`ux-audit/run-phase4.sh`) |
| 5.0 Workforce schemas & registries | DONE + audit-accepted — commit `cc909b9` | `docs/v1.6/phase5/5.0_IMPLEMENTATION_RECORD.md`; engine 658 (+45); audit 8-9 (REVISE → remediation → CONTINUE) |
| 5.1 Agent-to-model assignment | DONE + audit-accepted — commits `9d6ed55` + follow-up `5b83f0e` | `docs/v1.6/phase5/5.1_IMPLEMENTATION_RECORD.md`; engine 693 (+35); audits 10-11 CONTINUE (N1-N6 + S2 closed) |
| 5.2 D1 single-specialist delegation | DONE + audit-accepted — commits `894be5b` + follow-up `f9cf3ea` | `docs/v1.6/phase5/5.2_IMPLEMENTATION_RECORD.md`; engine 724 (+31); audits 12-13 CONTINUE (F1-F8 closed/open) |
| 5.3 D2 small pod + verification | DONE + audit-accepted — commit `48dacb3` + follow-up `5747567` | `docs/v1.6/phase5/5.3_IMPLEMENTATION_RECORD.md`; engine 767 (+43); audits 14-15 CONTINUE (F14 closed) |
| 5.4 Assurance army + Sentinel + Oracle | **ACCEPTED** — `932db33` + remediations `27e3720`, `d394649`, `71122ef`, plus the acceptance patch `f25a4bf` | `docs/v1.6/phase5/5.4_IMPLEMENTATION_RECORD.md`; engine 791 → 805 (+24 phase tests, then +3 and +3 remediation tests); audits 16/17/18 **REVISE** → remediated, audit 19 **CONTINUE** (F17-1 answered clean); published `0fcd9ed..f25a4bf`; disk-backed review handoffs adopted |
| 5.5 Parallel mission teams + mission worktrees | **ACCEPTED** — `5f77f42` + remediations `b1141c4`, `2a12b77` + acceptance patch `d8880f3` | `docs/v1.6/phase5/5.5_IMPLEMENTATION_RECORD.md`; engine 842 (+37) → 851 → 853; migration 19; audits 20/21 **REVISE** → remediated, audit 22 **CONTINUE**; published `9a2965d..d8880f3` |
| 5.6 Learning loop (shadow) | **ACCEPTED** — `ba52869` + remediation `8a2b25d` | `docs/v1.6/phase5/5.6_IMPLEMENTATION_RECORD.md`; engine 853 → 876 → 878; no migration (learnings ride the memory store; history rides team_events); flag `workforce.learning.shadow` default off; audits 23 REVISE → 24 CONTINUE; 5.7/5.8 decisions deferred (`5.7_DECISION_DEFERRED.md`, `5.8_DECISION_DEFERRED.md`) |

Latest verified candidate: `dist/package-final17/win-unpacked` (Phase 4 completion evidence; copy-scan
probe over the reachable routes plus the standing approvals/lineage journeys). `dist/package-p1cap3`
remains the CAP2-RESIDUAL evidence artifact; `package-p1cap2`/`p1cap`/`final16` remain the earlier
phase evidence artifacts; `package-final13`/`final15` are the memory/lineage evidence artifacts;
`package-final12` is a superseded intermediate (UI bug); never cite it.

## P1 capability remediation + Phase 4 pause (2026-09-17)

Independent Audit 1.6 returned REVISE with three P1 findings (CAP-01/02/03) against the session-scoped
capability system. Remediation implemented and verified before Phase 4 continues.

- **Starting HEAD**: `70d68e4` (Phase 4 recon; Phase 3 = `85e99fb`).
- **Remediation commit**: `75d1f68` ("fix(capabilities): the real web effect and explicit commands honour
  the conversation controls"), on top of `70d68e4`. Phase 4 WIP is NOT part of it.
- **Files changed**: `runtime/kel/capabilities.py` (strict explicit commands; `directive_clauses`;
  Drive/Connected apps removed from the control; `_conversation_for_job` falls back to the job's own
  conversation), `runtime/kel/research.py` (the real web effect passes the conversation capability
  decision before any external request), `runtime/kel/acp_host.py` (stand-alone command answers
  inline; an explicit clause inside a larger request applies while the request is forwarded; ordinary
  talk never mutates), `runtime/tests/test_capabilities.py` (+ production-path research regressions),
  `runtime/tests/test_acp_host.py` (+ command/forwarding/ordinary-talk regressions),
  `packaging/ux-audit.cjs` (sessiontools scenario updated to the removed-capability contract + an
  ordinary-talk no-mutation step), `desktop/.../KelToolsControl.tsx` (comment only),
  `docs/session-tools/*` (03 overrides doc + subsystem AUTO_RESUME).
- **Tests**: `runtime && python -m pytest tests -q` → **604 passed (+10 subtests)**. Focused:
  `test_capabilities.py` (25), `test_acp_host.py`, `test_research.py`, `test_v15_authorize.py` all
  green. Renderer: comment-only change; no renderer test expectations moved.
- **Manual / packaged evidence**: `ux-audit/run-p1-capabilities.sh` → sessiontools journey on
  `package-p1cap` PASS (menu plain + machinery hidden, Drive/Connected apps not offered and refused,
  web off/allow-once/enable/isolation/restart/reset values correct, ordinary talk leaves the web
  override untouched, directive reply found in the transcript via the db probe, 0 errors / 0 console
  errors) and packaged-engine probe PASS (Web off → “Kel paused this research before any external
  request: Web is disabled for this conversation.”, 0 research-evidence rows, transport never called;
  Web default → the same job passes the gate and the model request is attempted and rejected (401
  with the probe's dummy key); capability ids = web,files,terminal,github). Packaged engine hash ==
  fresh `dist/runtime` build.
- **SEC-01 (P2)**: vetting `process`/`finish` look up a session by id without the conversation /
  project-ownership comparison `_memory_action` and `panel()` use. Local loopback + single-actor
  threat model; fixed NOT in this commit — recorded for later audit remediation with the other P2/P3
  items (PER-02, PER-03, sender-frame validation, `KEL_DATA_DIR` backup credentials edge).
  **DEAD-06 correction (per the CAP2 audit)**: `packaging/ux-audit.cjs` is still referenced by no
  repo `package.json` / `.ps1` / `.sh` — only ad-hoc invocation is described in docs — so DEAD-06
  remains OPEN; an earlier claim in this file that it was resolved was inaccurate. It is used as the
  gate harness by the scratch wrappers in `ux-audit/` (outside the repo), which does not resolve the
  finding. **DEAD-07 / DEAD-08**: the trailing fallback in `availability()` is back as an explicit
  fail-closed branch (the CAP2-CLAUSE removal left totality accidental; DEAD-08 asked for an explicit
  fail-closed return or exhaustive assertion). It is regression-tested with a synthetic unknown probe
  (`test_unknown_probe_fails_closed_not_open`): the capability reads as unavailable and `resolve()`
  denies it — never silently available, and no longer dead code.
- **Phase 4 preservation**: 123 tracked files + 1 untracked file stashed as
  `MAIN-PHASE4-WIP-BEFORE-P1-CAPABILITY-REMEDIATION` (`git stash list`; `stash@{0}` at capture).
  Full diff, untracked copy, and the Phase 4 audit/report scripts are preserved in
  `C:\Users\Nick\Desktop\Kel\ux-audit\PHASE4_WIP_BEFORE_P1_REMEDIATION\` (README.txt explains the
  restore procedure). The stash has NOT been dropped and has NOT been restored — Phase 4 is paused.
- **Current HEAD** (at this writing): the state commit that records this file's update on top of
  `75d1f68` (see `git log --oneline -3`: `75d1f68` remediation → this docs/state commit).
- **Next Audit 1.6 range**: `ffeef73..CURRENT_REMEDIATION_STATE_HEAD` — `ffeef73..75d1f68` covers
  `85e99fb` (Phase 3), `70d68e4` (Phase 4 recon) and the P1 remediation; the state commit on top adds
  only this AUTO_RESUME update. The stashed Phase 4 work is NOT part of that range.

## CAP2-CLAUSE remediation (2026-09-17)

Independent Audit 1.6 closed CAP-01 and CAP-03 but returned REVISE on CAP-02: the embedded-clause
parser performed a substring scan, so ordinary prose mutated capability state and text was stripped
from the message (`he said "web: off"…` reached the model as `he said ""…`).

- **Starting HEAD**: `4f6535a`. **Remediation commit**: `327e5b2` ("fix(capabilities): embedded commands
  require the explicit bracketed clause; prose is never touched"). The state commit on top records
  this file. Phase 4 WIP is NOT part of either.
- **Parser behavior now**: standalone whole-message commands are unchanged (fullmatch grammar:
  `web: off`, `web=off`, `Web: OFF`, `web: reset`, `web: use default`, `use default for the web here`,
  `set web back to default`, `reset terminal to default`, `don't use the terminal here`,
  `no terminal commands here`, `stop using the browser in this chat`). Embedded controls require the
  deliberately explicit bracketed form: `[terminal: off]`, `[web: use default]`, `[github: on]` — one
  or more, outside quotes and code. Only the exact bracketed token (plus adjacent whitespace and at
  most one adjacent separator) is removed from the forwarded request.
- **Fail-safe**: ordinary prose, quoted commands, inline code, fenced code, URLs and malformed
  brackets never mutate state and are forwarded byte-identical; an unpaired double quote, unclosed
  fence or ambiguous syntax matches nothing. The audit's full mandatory corpus (10 sentences) plus
  case/whitespace/punctuation/multi-colon/URL/code/malformed extras is a direct regression
  (`ORDINARY_PROSE` in `runtime/tests/test_capabilities.py`) with a negative-control test proving the
  4f6535a substring rule would have matched every one of them.
- **Tests**: `test_capabilities.py` (parser corpus, standalone corpus, removal exactness, negative
  control), `test_acp_host.py` (standalone inline, embedded apply+forward, leading/multiple clauses,
  byte-identical prose forwarding through the fake service); full runtime suite **610 passed
  (+10 subtests)**. Renderer unchanged.
- **Packaged evidence**: `ux-audit/run-cap2-clause.sh` on `package-p1cap2` — sessiontools journey
  with the new bracket-clause steps (terminal override after `[terminal: off]`, plain/quoted/inline
  prose leave GitHub untouched), transcript probe, CAP2 forwarded-text probe against the engine
  database (request forwarded exactly without the clause; prose byte-identical), and the packaged
  engine capability probe as the CAP-01 regression check.
- **Next Audit 1.6 range**: `4f6535a..NEW_MAIN_HEAD` — `4f6535a..327e5b2` is the CAP2 remediation
  commit; the state commit on top adds only this AUTO_RESUME update. CAP-02 must receive independent
  CONTINUE before Phase 4 resumes; CAP-01/CAP-03 closure stands (regression-checked here).

## CAP2-RESIDUAL remediation (2026-09-17)

Independent Audit 1.6 closed the original CAP2-CLAUSE defect but returned REVISE on a residual: the
`[capability: state]` embedded form still plausibly matched technical strings (`Use C:/projects/[web: off]
as the path.`, API/log lines, `[[web: off]]`) and silent text removal followed.

- **Starting HEAD**: `85cf0f1`. **Remediation commit**: `631881a` ("fix(capabilities): embedded commands use
  the reserved [kel:...] namespace; technical text is never touched"), on top of `85cf0f1`. Phase 4
  WIP is NOT part of it.
- **Embedded grammar now**: the RESERVED Kel namespace, canonical only —
  `[kel:web=off]`, `[kel:web=on]`, `[kel:web=default]`, `[kel:terminal=off]`, `[kel:github=on]`,
  `[kel:files=default]` (capabilities web/files/terminal/github; states on/off/default; case-
  insensitive, e.g. `[Kel:Web=OFF]`). No aliases, no whitespace variants, no extra fields. The old
  generic bracket forms (`[web: off]`, `[Web: OFF]`) are ordinary text now — an intentional
  compatibility break inside an unreleased feature. Standalone whole-message grammar is unchanged
  (11-item corpus incl. `web=off`, `Web: OFF`, `web: reset`, `set web back to default`).
- **Boundary rules**: quoted/code spans excluded (incl. unpaired-opener fail-safe); nested brackets
  inert (`[[kel:web=off]]`, `[ [kel:web=off] ]`); word-embedded inert (`prefix[kel:web=off]suffix`);
  URL segments inert; malformed/unknown inert (`[kel:web]`, `[kel:web=sideways]`, `[kel:unknown=off]`,
  `[kel:web=off:now]`, `[kel::web=off]`, `[kel:web==off]`, unclosed); exact forwarding byte-for-byte
  whenever no valid directive is recognized — no normalization of any kind.
- **Exact removal**: the reserved token plus adjacent whitespace and at most one adjacent separator
  per side; `A,[kel:web=off],B` keeps one comma (`A,B`); `A ([kel:web=off]) B` drops the empty paren
  pair (`A B`); words are never joined; nothing else is deleted. Multiple directives apply in source
  order; a repeated capability ends on its last value.
- **Tests**: residual corpus (9 mandated strings) + reserved boundary corpus + prior prose/quote/
  code/malformed/URL corpora, all with byte-identity asserts; a NEGATIVE CONTROL that executes the
  actual 85cf0f1 parser from git (`git show 85cf0f1:runtime/kel/capabilities.py` in an isolated module)
  and proves it recognized the residual technical cases and rewrote the text (`Use C:/projects/as the
  path.`, `log: GET /api/v1/HTTP/1.1`, `[]`) while the new grammar recognizes none; ACP end-to-end
  cases A–G incl. byte-identical forwarding with zero capability calls; DEAD-08 regression. Full
  runtime suite: **613 passed (+10 subtests)**.
- **Packaged evidence**: `ux-audit/run-cap2-residual.sh` on `package-p1cap3` — sessiontools journey
  with the reserved-directive step (Terminal off) and residual steps (path, nested), transcript
  probe, residual forwarded-text probe against the engine database (reserved token never forwarded;
  residual lines and prose byte-identical) and the packaged engine probe as the CAP-01 regression.
- **Next Audit 1.6 range**: `85cf0f1..NEW_MAIN_HEAD` — `85cf0f1..631881a` is this remediation; the
  state commit on top records this AUTO_RESUME update. CAP-02/CAP2-RESIDUAL must receive independent
  CONTINUE before Phase 4 resumes.

## Phase 4 completion (autonomous Main increment, 2026-09-17)

Phase 4 (i18n / donor-string cleanup) was restarted from the preserved stash and completed.
**Independent Audit 1.6 accepted it (increment 7: CONTINUE for `267364e..fd04c00`, no production
writes, Main worktree untouched).** Dependency-watch cadence for autonomous Main is documented in
`docs/v1.6/AUTONOMOUS_OPERATION.md` (30-second re-read of the authoritative status file when blocked
on another thread, stop immediately on change, never hot-loop, commit truth over status prose).
The Visual checkpoint is published under the orthogonal schema (`visual_state: READY_FOR_VISUAL`,
`visual_clean_head: 60b2322` — verified: exists, ancestor of the branch, remote-contained) so the Visual
thread may begin while Main stays `IMPLEMENTING`; the schema and the race-avoidance ownership protocol
(consult `VISUAL_STATUS.active_owned_files` before touching user-facing Workforce files) are documented
in `docs/v1.6/AUTONOMOUS_OPERATION.md`. The mandatory Phase 5 reading is
complete (coverage recorded in `docs/v1.6/phase5/READING_RECORD.md`: 17/17 `workforce-os` docs +
31/31 role-charter files); the next increment is **Phase 5.0 — Foundations** per
`15_PHASE5_IMPLEMENTATION_SPEC.md`.

- **Safe restoration**: stash `MAIN-PHASE4-WIP-BEFORE-P1-CAPABILITY-REMEDIATION` (base `70d68e4`,
  object `992ab31c…`, 123 tracked files + 1 untracked) was inspected against the recovery artifact
  and applied onto clean `267364e` with **zero file overlap** with the P1/CAP2 remediation; the
  restored file set matched the stash exactly, the restored `SettingsCreateMenu.tsx` hash matched the
  artifact copy (`2838b3c3…`), and `git diff HEAD -- runtime packaging` stayed empty (no CAP fix was
  overwritten). The stash was kept until restoration was proven, then dropped after `fd04c00`
  committed (stash object `992ab31c…`; the recovery artifact remains at
  `C:\Users\Nick\Desktop\Kel\ux-audit\PHASE4_WIP_BEFORE_P1_REMEDIATION\`).
- **Completion**: the remaining reachable donor literals were finished (About modal donor
  links replaced with the product repository, boot-dialog/update links → Kel releases, donor wiki
  guide links removed from Model/Tools/channels, DingTalk credential links → `open.dingtalk.com`,
  guid GitHub action → Kel repo, unreferenced donor Skills-Market banner deleted, channel-conflict
  literals, `i18n-keys.d.ts` Butler keys removed, theme markers renamed with a legacy matcher).
  Full inventory, keep-list (license headers, internal identifiers, dormant/hidden boundaries) and
  evidence live in `docs/i18n-cleanup/00_STATUS.md`. The permanent GitHub sync policy is now tracked
  at `docs/v1.6/GITHUB_SYNC_POLICY.md`.
- **Verification**: locale transform replay = 0 changes / 0 residual donor values; 247 locale files
  valid; no removed keys remain; desktop `tsc` 0 errors and vitest 76/76; engine suite 613 passed
  (+10 subtests); packaged `package-final17` with `ux-audit/run-phase4.sh` (copy-scan over reachable
  routes + approvals + lineage journeys).
- **Next Audit 1.6 range**: `267364e..NEW_MAIN_HEAD` (this Phase 4 increment plus the state commit
  that records it).

## Phase 5.0 — workforce schemas & registries (autonomous Main increment, 2026-09-17)

Phase 5.0 (Workforce OS schemas & registries) is implemented on `ux/v15-journeys` (commit `9085335`, remediated `cc909b9`) and
audit-accepted through `cc909b9` (increment 8 REVISE → increment 9 CONTINUE). Migration 16 (`v16-workforce-schemas`,
applied at Service startup) creates `task_contracts`, `workforce_messages`, `findings`,
`evidence_records` and `skill_packs` — append-only triggers on the three ledgers. The
TaskContract/CompletionPacket/message/finding v1 validators, the evidence writer, the 15-lens
registry and the R1–R10 staffing rule table ship as pure modules with no consumers yet.
Documented deviations: `task_contracts` named distinctly from the core `contracts` table;
interim static role→authority ceilings until role registry v2 (5.1); first append-only SQLite
triggers in the repo. Evidence: `docs/v1.6/phase5/5.0_IMPLEMENTATION_RECORD.md` (+ audit
addendum); engine `658 passed (+45)` on Windows; packaged verification deferred to the next
packaged battery (assert `schema_migrations` 16 on a packaged boot). **Audit: increment 8
REVISE → remediation `cc909b9` → increment 9 CONTINUE (F1-F3 closed); accepted through
`cc909b9`.** Carry-forward: partial-coverage test for the lens check; echo-vs-issued-contract
reconciliation for D1/D2. Next: Phase 5.1 — agent-to-model assignment
(`test_workforce_assignment.py`).

## Phase 5.1 — agent-to-model assignment (autonomous Main increment, 2026-09-17)

Phase 5.1 (Workforce OS agent-to-model assignment) is implemented on `ux/v15-journeys` as
commit `9d6ed55`, audit-requested for `cc909b9..9d6ed55`. `kel/assignment.py` seeds the
8-archetype registry v2 (7 spawnable templates; Commander never a template) into the existing
V1.4 role storage with the doc-03 §7 fields; AUTO/PREFERRED/FIXED resolution binds roles to
(provider, model, runtime) over the existing deterministic router with per-role requirement
profiles; capability grants are fail-closed against the authority ceiling; migration 17 adds
`budget_reservations`; overlays v1 ship as a graceful no-op registry; assignment snapshots
freeze mode/binding/grants/reservation/flags via `create_assignment(extra=)`; the contract
validator now accepts versioned registry ceilings. Nothing live calls the new API (explicit
path only) and `workforce.enabled` defaults off — B-config parity by construction. Evidence:
`docs/v1.6/phase5/5.1_IMPLEMENTATION_RECORD.md`; engine `689 passed (+31)` on Windows; same-role
demo across all three modes snapshotted. **Audit: increment 10 CONTINUE — Phase 5.1 accepted
for `cc909b9..9d6ed55`; minors N1-N7 recorded (latent FIXED model-check gap, reservation
milestone/atomicity, record fidelity, cross-mode arguments, extras sanitization, per-project
ceilings).** The follow-up patch `5b83f0e` closed N1-N6 + S2; audit increment 11 returned
**CONTINUE** (all closures verified; carry-forward integrity confirmed; new suggestion-level
items ride the 5.2 wiring review). Next: publish this checkpoint, then Phase 5.2 — D1
single-specialist delegation (`test_workforce_d1.py`).

## Phase 5.2 — D1 single-specialist delegation (autonomous Main increment, 2026-09-17)

Phase 5.2 (Workforce OS single-specialist delegation) is implemented on `ux/v15-journeys` as
commit `894be5b`, audit-requested for `5b83f0e..894be5b`. `staffing.decide()` turns the doc-05
feature vector into a recorded tier decision (bands, R1 cap, mission-flag floors, tier_max);
`delegation.delegate()` issues the frozen TaskContract for exactly one specialist (migration
18 links it to the milestone) and records staffing.decided/contract.issued;
`close_d1()` refuses completed closes on stale, unbound or missing evidence and on missing
criterion coverage (uncertain/failed close honestly); `run_d1()` enforces worker tools against
the frozen grants and never spawns nested workers; `task_ledger()`/`progress_ledger()` project
the trail read-only; flag off performs zero writes. Carry-forward closed: N7 + Sug1-5 + S3.
Evidence: `docs/v1.6/phase5/5.2_IMPLEMENTATION_RECORD.md`; engine `717 passed (+24)` on
Windows; full D1 demo trail in the record. **Audit: increment 12 CONTINUE — Phase 5.2 accepted
for `5b83f0e..894be5b`; findings F1-F8 recorded (F4 rides the 5.3 real-worker wiring).** The
follow-up patch landed as `f9cf3ea` (focused 31; full 724) and its delta re-audit
(increment 13) returned **CONTINUE** — F1-F8 closed or correctly open (F4 remains for 5.3;
N1 hardening noted for the 5.3 wiring). Next: publish, then Phase 5.3 — D2 small pod +
verification (`test_workforce_d2.py`).

## Phase 5.3 — D2 small pod + verification (autonomous Main increment, 2026-09-17)

Phase 5.3 (Workforce OS small pod + verification) is implemented on `ux/v15-journeys` as
commit `48dacb3`, audit-requested for `f9cf3ea..48dacb3`. `kel/pods.py: run_d2` runs the
hands-off Builder→Verifier flow: two frozen contracts (verifier depends on the builder task,
carries functional-testing + maintainability lenses), one assignment each (Builder ≠ Verifier;
family-diverse verifier binding with recorded fallback), an evidence-bound builder close, a
HANDOFF message, the verifier's findings + verdict (VERIFIED refused while blockers/criticals
are open), evidence-bound closes throughout, stall probes (`check_stall`) and interruption
accounting. `kel/messages.py` gained dispatch enforcement (pair ≤6 with cmd exempt, task ≤12,
fingerprint dedupe, receiver-state guard); `kel/assurance.py` gained the findings pipeline
(multi-lens confirmation, arbitration ladder v1). `kel/evaluation.py` is the A-vs-C pilot
harness on classes 2/6/8 — **gates green: escaped_C < escaped_A on every class; interruptions
0 ≤ budget**. No new migration; flag off performs zero writes; F4/N1 wiring landed with the
real-worker path. Evidence: `docs/v1.6/phase5/5.3_IMPLEMENTATION_RECORD.md`; engine
`765 passed (+41)` on Windows. **Audit: increment 14 CONTINUE — Phase 5.3 accepted for
`f9cf3ea..48dacb3`; F14-1/F14-2/N14-1 queued for the opening follow-up patch; F4 remains open
for the real-worker increment.** The follow-up patch landed as `5747567` (focused 43; full 767)
and its delta re-audit (increment 15) returned **CONTINUE** (all closures verified; two low
suggestions carried). Next: publish, then Phase 5.4 — assurance army + Sentinel + Oracle
(`test_workforce_assurance.py`).

## Phase 5.4 — assurance army + Sentinel + Oracle (autonomous Main increment, 2026-09-17)

Phase 5.4 is implemented on `ux/v15-journeys` as commit `932db33`, audit-requested for
`5747567..932db33`. `kel/assurance.py` gained deterministic scope gating (`lenses_for`: tier
floors + flag triggers + never-gate at D4; every skipped lens reasoned), anti-anchored
`dispatch_assurance` (artifact + lens + requirement payloads only; coverage statements
required; the Sentinel security-lens rule), the deterministic `gate` (blockers always;
criticals while open; never-gate findings unwaivable by Kel), `waive_gate` (user-only for
never-gate, recorded), the `oracle_check` harness (family-diverse, coverage-required) and
`lens_stats` (FP rates). Audit-15 suggestions closed: `messages.ESCALATION_TYPES` is the
single source; the boundary test enumerates the three escalation types and refuses HANDOFF at
cap. Evidence: `docs/v1.6/phase5/5.4_IMPLEMENTATION_RECORD.md`; engine `791 passed (+24)` on
Windows. Next after audit CONTINUE: publish, then Phase 5.5 — parallel mission teams.

## Phase 5.6 — learning loop (shadow) (autonomous Main increment, 2026-09-18)

Phase 5.6 (Workforce OS learning loop, shadow) is implemented on `ux/v15-journeys` as commit
`ba52869`, audit-requested for `2236881..ba52869`. New `kel/learning.py` — learnings are
**memory records** with workforce source types (`workforce_observed`/`workforce_cross_model`/
`workforce_inferred`; user-stated rides the existing `user_confirmation` level 2), so
provenance, the trust ladder, supersede chains, conflict queueing and forget semantics all apply
unchanged; **no new storage surface, no migration** (learnings ride the memory store, history
rides `team_events`, stats/metrics are derived views). Dedup never forks a key; decay is
computed at read time (observed/inferred/cross-model −1 point / 30 days; user-stated never
decays); preferences only from explicit user confirmation; confidence above the auto cap (5) is
stored capped and queued for promotion (nothing promotes automatically); corrections ride
`Memory.correct` and become user-stated. The curator (post-mission, bounded, deterministic)
records candidate learnings from findings/corrections/mission conflicts, drafts the retro
(`retro.v1`) and records shadow staffing proposals with predictions; performance stats and
validation metrics (gating precision, false-skip by recomputed gating plans) are derived views
with small-sample honesty. Additive wiring: `team.py` EVENT_KINDS +
`Team.record_mission_activity`; `memory.py` workforce `SOURCE_TRUST`; `assignment.py`
`flags_snapshot` carries `workforce.learning.shadow` (`KEL_WORKFORCE_LEARNING_SHADOW`, default
off — flag off performs zero writes on every path; nothing calls the module yet).
Evidence: `docs/v1.6/phase5/5.6_IMPLEMENTATION_RECORD.md`; focused **23 passed**; full runtime
suite **876 passed (+10 subtests; baseline 853)** on Windows; 876 collected. Next: audit
increment 23 (`2236881..ba52869`); on CONTINUE publish, then the Phase 5.7 decision (adaptive
staffing enablement stays deferred unless the doc-13 campaign metrics and user sign-off exist).

Update (audit 23 → 24): the delta re-audit returned **REVISE** (`36_PHASE5_6_AUDIT.md`;
F23-1..F23-10 — an ungated writer, store-wide lens scope claiming project scope, decay/hygiene).
Remediated in `8a2b25d` (focused 25; full 878; zero regressions; see the record's follow-up
section). Delta re-audit (24): **CONTINUE** — all closed; **Phase 5.6 accepted through
`8a2b25d`**. Phase 5.7 DEFERRED (entry unmet: doc-13 campaign + user sign-off) and Phase 5.8
DEFERRED (product decision) — decision records in `docs/v1.6/phase5/`. Next: publish, Visual
screenshot-index refresh, then Phase 6 (memory reality audit).

## Verify quickly (any resume)

1. `cd runtime && python -m pytest tests -q` → **878 passed** (+10 subtests; zero regressions).
2. `cd desktop && bunx tsc --noEmit` → 0; `bun run test` → 76.
3. Packaged journeys (edit `APP` inside each to the current candidate first):
   `bash ux-audit/run-cap2-residual.sh` (needs `package-p1cap3`; sessiontools reserved + residual
   steps, residual db probe, engine regression), `bash ux-audit/run-cap2-clause.sh` (needs
   `package-p1cap2`; sessiontools + CAP2 clause probes + engine regression), `bash
   ux-audit/run-p1-capabilities.sh` (needs `package-p1cap`; sessiontools + packaged engine capability
   probe), `bash ux-audit/run-approvals.sh` (needs final16), `bash ux-audit/run-lineage-probe.sh`
   (now final16), `bash ux-audit/run-memoryprops.sh` (needs final13).

## Sharp edges learned so far

- Packaged UI probes: the chat header pills (model/tools/review) render only on
  `#/conversation/<id>` pages; the report/detail text lives in an **open shadow root**
  (`.markdown-shadow` → `host.shadowRoot.textContent`).
- The sessiontools DOM scan for the directive reply is best-effort under the virtualized list; the
  subsystem's authoritative evidence is the transcript db probe (`ux-audit/sessiontools-db-probe.py`)
  — its `naturalLanguageReplySeen` in `ux-sessiontools.json` was already false in the original gate
  run while the directive applied and the reply was recorded.
- A standalone packaged engine registers its model adapters (including `research`) only when
  `ANTHROPIC_API_KEY` is present; probes set a dummy key (deny path never reaches the network).
- `/api/memory` `proposals` returns `{proposals:[...]}`; `/api/lineage` returns `{versions:[...]}`.
- Migration 15 = memory proposals (registered). `artifact_lineage` is deliberately unversioned (core
  schema, like `runs`). Upgrade-test version pins in `test_v13_memory.py` / `test_v14_upgrade.py`
  were updated for 15 by design.
- Freeze tooling nests an inert runtime duplicate (`resources/kel-engine/kel-engine/`); the V1.6.0-pre1
  freeze removed it after assembly for exact candidate↔frozen identity — do the same at the final
  release (or fix `freeze-release.ps1` first).
- `bunx electron-builder --config kel-builder.json --win --x64 --config.directories.output=../dist/package-NAME`
  is the packaging command used (run from `desktop/`); builds take ~5–8 min (NSIS inside).
- In-chat approvals: anchors live in `approval_announcements` (core schema, unversioned); chat
  resolution must always delegate to `Autonomy.resolve_expansion` / `Store.resolve_approval`.
- The repo's `better-sqlite3` binary is Electron-ABI; system Node cannot load it — keep journey DB
  assertions in Python (`ux-audit/verify-approvals.py`), not in Playwright probes.
- Conversation capability commands: standalone human-friendly forms (`web: use default`,
  "don't use the browser here") or the RESERVED embedded namespace `[kel:<capability>=<state>]`
  (`[kel:terminal=off]`, `[kel:web=default]`) — canonical names and states only, the clause applies
  and the rest of the message is forwarded without only the reserved token. Generic brackets
  (`[web: off]`), quoted commands, code samples, URLs, nested brackets and malformed tokens never
  change state and are forwarded byte-identical; exact forwarding when no directive is recognized.

## CAMPAIGN A — full-speed implementation sprint (2026-09-18)

The operating strategy changed (user directive, 2026-09-18T~15:40Z). From now until a
PRE-AUDIT V1.6 RELEASE CANDIDATE exists: **implement → self-review → test → package → verify →
record → commit → integrate → continue.** Independent Audit cycles are **paused** (Campaign B
consumes the breadcrumb corpus afterwards; Campaign C repairs). Quality control is NOT deferred:
focused tests, regression, packaged verification, atomic commits and records continue per change.

- **Entry state**: Main `ux/v15-journeys` @ `fd98cc4` (published; clean; frozen refs verified).
- **Last independently audited production point**: `8a2b25d` (increment 24 CONTINUE). Docs-only
  commits above it: `c4ae724`, `5127bac`, `fd98cc4`.
- **First intentionally unaudited production commit**: opens with the first Campaign A production
  change (recorded in `docs/v1.6/pre-audit/COMMIT_LEDGER.md`).
- **Breadcrumb corpus**: `docs/v1.6/pre-audit/` — README, AUDIT_SCOPE, ledgers (commit/change/
  requirement/invariant), evidence indexes (test/packaged/migration/provider/visual), P2/P3
  disposition, risk register, deferrals, limitations, audit targets, repair hints, final-state
  matrix, increment records, evidence bundles. Maintained per increment, not at the end.
- **Audit thread**: parked (`audit_required: false`; `audit_mode: PAUSED_UNTIL_PRE_AUDIT_RC`).
- **Visual lane**: batches 1–5 are delivered on `ux/v16-visual-fix` (`ac85eb3`) with automated +
  packaged acceptance; they are NOT independently audited; remaining batches 6–8 and the
  integration into Main are Campaign A goals.
- **Rust**: NO_MIGRATION_NEEDED_NOW (`kel-rust-audit` @ `9c1e7d0`); freshness rechecked in Phase 11.
- **Baseline evidence**: engine `878 passed (+10 subtests)` at `fd98cc4` (2026-09-18, 251.55s) —
  `docs/v1.6/pre-audit/evidence/campaign-a-baseline/`.
- **Phases 10-11 done** 2026-09-18: provider validation (claude PASS, codex CLI-version blocked,
  internal/deepseek unavailable) and the Rust freshness recheck (verdict upheld; Phase 12 closed).
  **Next**: F4 real-artifact binding + resolution-kind; see `MAIN_STATUS.next_autonomous_action` for
  the full Campaign A queue.

## Phase 6 — memory reality audit + bounded fixes (2026-09-18)

Completed as one increment (`docs/v1.6/pre-audit/increments/PHASE6-MEMORY-REALITY.md`; audit:
`docs/v1.6/phase6/MEMORY_REALITY_AUDIT.md`). Reality inventory (store, write paths, read paths,
UI surfaces, explicit non-existents), isolation/persistence/provenance verification, dispositions
MEMR-1..MEMR-7. Bounded fixes in `22f4a3e` — the **first intentionally unaudited production
commit** of Campaign A: Work-panel knowledge actions follow record state (`memoryRecordActions`,
7 unit tests), forget asks for confirmation, tombstones read "Content removed.". Re-verified
carry: SEC-01/APR-01/APR-02 (isolation class) documented; APR-03 reviewed → stays with the P2/P3
sweep (durable-drain direction recorded); stale-detection wiring (DEF-012/LIM-13) and new-surface
localization (DEF-013/LIM-12) deferred with records. Tests: engine focused 68 (engine untouched);
tsc 0; vitest 83 (76→83).

Reports: `docs/v1.6/pre-audit/` corpus updated (COMMIT_LEDGER, CHANGE_LEDGER CHG-001/002,
TEST_EVIDENCE_INDEX, REQUIREMENTS_TRACEABILITY, KNOWN_LIMITATIONS, DEFERRED_ITEMS, AUDIT_TARGETS,
P2_P3_DISPOSITION, REPAIR_HINTS, VISUAL_EVIDENCE_INDEX).

## Phase 7 — capability recommendations (2026-09-18)

Completed as one increment (`docs/v1.6/pre-audit/increments/PHASE7-CAPABILITY-RECOMMENDATIONS.md`;
record: `docs/v1.6/phase7/CAPABILITY_RECOMMENDATIONS.md`). The engine now emits a structured,
real-only recommendation when a capability refusal happens (`capabilities.recommendation`;
research + coding blocked outcomes; retained on the job milestone so `/api/state` carries it), and
the desktop renders it in the Work panel (`KelCapabilityCard`: Allow once / Enable for this chat /
Keep it off — fail-closed rendering, real endpoints, dismissal without state change). Invariant
INV-CAPREC-001 added; audit targets 40–45 added. Tests: engine focused 83; **full 885 passed**
(+10 subtests; was 878); tsc 0; vitest **90** (was 83). Packaged card evidence deferred — no
provider in this environment (LIM-14); transcript-inline placement = DEF-014. Next: Phase 8/5.8
decision.

## Phase 8/5.8 — Advanced Worker View: decision (2026-09-18)

**DECIDED — deferred beyond V1.6.** Final record: `docs/v1.6/phase8/ADVANCED_WORKER_VIEW_DECISION.md`
(supersedes the pending-state 5.8 record). Rationale: North Star ONE assistant; design doc 12's own
success bar is zero visits; the spec's exit gate (product decision + usability review) has not
occurred and no user need is recorded; sprint directive §33 says not to block the sprint on the
optional panel. No UI/endpoints added; existing engine-side data stays available. Re-entry
conditions recorded (post-V1.6 decision → bounded Advanced/Details-only increment, zero-visit
default). Phase 5.7 confirmed deferred per §34 (no fabrication; activation criteria already
recorded). Corpus updated: DEF-002, REQ-AWV-8, REQ-WF-5.8, CHANGE_LEDGER mapping. Next: Phase 9 —
Profiles vs Projects.

## Phase 9 — Profiles vs Projects: decision (2026-09-18)

**DECIDED — no Profiles concept in V1.6; Projects remain the single isolation concept.** Record:
`docs/v1.6/phase9/PROFILES_VS_PROJECTS_DECISION.md`. Evidence: donor matrix item 21 (REJECT —
Projects already scope conversations/files/knowledge/artifacts/recipes), donor remediation §4, and
current-repo verification (no `/profiles` route/nav/locale surface; donor AssistantSettings hidden
by `HIDE_DONOR_AGENT_SURFACES = true`; remaining "profile" strings are unrelated donor auth labels
and engine internals). No code change required; held visual batch 3 keeps "Projects" language. New
audit target 46 (AgentBadge assistantId path is donor-dead for Kel conversations). Corpus updated:
REQ-PP-9, mapping row 9. Next: Phase 10 — real provider validation.

## Phases 10-11 — provider validation + Rust freshness (2026-09-18)

**Phase 10 (sprint §36):** real calls where access allows — `claude -p` minimal call **PASSED**
(returned `ok`; client 2.1.215, authenticated); `codex exec` reached the real service but was
refused by CLI model-version logic (`gpt-6-astra` requires a newer Codex — recorded as an
environment limitation, never a pass); `internal`/`deepseek` have **no credentials anywhere on this
machine** (presence-only checks; nothing leaked). Fixture refresh: 55 passed (providers +
assignment). Record: `docs/v1.6/phase10/PROVIDER_VALIDATION.md`; matrix rewritten.

**Phase 11 (sprint §37):** `NO_MIGRATION_NEEDED_NOW` **upheld** against the current tree — process
model/transports/ownership unchanged by Campaign A work; A1 (`engine_version` reuse check),
PER-02 (`apply_pending_restore` swallow) and REL-01 (freeze staging) re-verified still open (docket
P2s); no re-open trigger fired. **Phase 12 CLOSED** (no Rust migration in V1.6). Record:
`docs/v1.6/phase11/RUST_FRESHNESS_RECHECK.md`. Next: F4 real-artifact binding + resolution-kind.

## Canonical logo (Nick directive, 2026-09-18)

**DONE — REQ-LOGO-1.** The exact Nick-supplied folded-ribbon K (`Kel Logo.png`, sha256 `7418a42f…`)
is now the canonical Kel logo on every production-reachable branding surface: exe/installer/shortcut
icon, taskbar/tray/notifications, dev window/dock, linux/mac icons, favicon/apple-touch/PWA, the login
mark, and a new About-screen mark. The canonical source is preserved byte-identical
(`desktop/resources/branding/kel-logo.png`); every size is a derivative generated by
`scripts/make-brand-assets.py` (sha256-guarded, premultiplied alpha, no crop/recolour/redraw).
Enabling `signAndEditExecutable` also fixed a real shipped defect: the previous package's exe carried
Electron's own identity and icon (`ProductName=Electron`, `CompanyName=GitHub, Inc.`). Record:
`docs/v1.6/branding/CANONICAL_LOGO.md`; increment `pre-audit/increments/LOGO-CANONICAL.md`; evidence
`docs/v1.6/branding/evidence/`. Verification: tsc 0, vitest 90, packaged build exit 0 with exe **and**
installer icons pixel-identical to the shipped frame (mad 0.0), packaged UI harness `errors: []`, and
the packaged About capture matching the canonical artwork at 0.960 masked NCC. Known residuals:
`CompanyName=AionUi` in exe metadata, dead donor `logo.svg`, donor `.nsh` installer text (not included
by the builder) — audit targets 47–49. The human pixel gate (16 px legibility, About placement) stays
open. Next: F4 real-artifact binding + resolution-kind.

## REQ-RK — record-bound resolution kinds (2026-09-18)

**DONE — REQ-RK / audit carry-forward F18-5 (N18-5).** `_is_acceptance` inferred an acceptance from a
prefix on the free-text `dismissal_reason`; how a finding was resolved is now recorded data.
`findings.resolution_kind` (vocabulary `fixed|risk-accepted|gate-waived|false-positive`) is written by
the guarded paths (`resolve_finding`, `waive_gate`), validated when present, and read by `lens_stats`,
which derives the kind once for rows written before v17. The additive migration **v17**
(`v17-finding-resolution-kind`) adds the column in place with a PRAGMA guard — no row rewritten, no
contract change, idempotent across reopens. The F17-2 anti-impersonation guarantee (guarded reason
markers) is preserved. Commit `a547936`; record `increments/REQ-RK-RESOLUTION-KIND.md`; tests
`tests/test_v16_resolution_kind.py` (6); focused 136 passed; **full engine suite 891 passed**
(+10 subtests, was 885). No desktop change required (no desktop code reads reasons or lens stats).
Next: **F4 real-artifact binding wiring**.

## REQ-F4 / WF-12 — real-artifact binding (2026-09-18)

**DONE — REQ-F4 / audit carry-forward F4 (audit scope WF-12).** Closure verification compared the
evidence's artifact digest against the *packet's own* artifact list, and `assignment_artifacts` —
the table recording what an assignment really delivered — had a writer (`Team.add_artifact`) and no
reader. Now: `Store._record_assignment_artifact` binds each landed milestone artifact to its
assignment in the same transaction as `artifact_lineage` (idempotent), and
`_artifact_violations` refuses a content-bound close whose claimed digest was never recorded for
that assignment — plus, when a caller supplies `artifact_root`, a missing file or a digest that
does not match what is on disk. The gate immediately found 8 failures + 5 errors in fixture
harnesses (D2 builder/verifier workers, pilot specialists) which now record their deliveries the
way the real worker wiring must. Commit `081a6ef`; record
`increments/REQ-F4-REAL-ARTIFACT-BINDING.md`; tests `tests/test_workforce_d1.py` (4 new); focused
126 passed; **full engine suite 895 passed** (+10 subtests, was 891). Residuals: `run_d1` does not
yet pass an `artifact_root` (audit target 56); non-content-bound contracts keep their previous
scope. Next: **P2/P3 sweep**.

## PER-02 — restore failures are recorded and surfaced (2026-09-18)

**FIXED (engine half) — audit P2 PER-02 (Rust-corroborated).** `service.py` used to wrap
`apply_pending_restore` in `try/except: pass` and discard the boolean, so a restore that could not
start, or failed halfway, left no trace. Now `backup._record_outcome` writes
`restore-outcome.json` **beside** the data (the database is what a restore replaces, so the record
cannot live inside it) on both decisive paths — success `ok=True`; failure `ok=False` with the
exception *type name* and `restore-pending.json` left in place — and `service.state()` carries
`restore: {ok, detail, at} | null` next to `connected`/`engine_version` (additive payload, no
contract break). Boot never aborts on a restore failure. Commit `df1997a`; record
`increments/PER-02-RESTORE-VISIBILITY.md`; tests `tests/test_v16_restore_visibility.py` (5 new);
focused 14 passed; **full engine suite 900 passed** (+10 subtests, was 895). The renderer surface
that would *show* the outcome belongs to REQ-ELOSS (audit target 57) and was deliberately not
invented here. Sweep status after this increment: **7/27 rows dispositioned** (P2 1/10, P3 6/17).
Next: continue the sweep (P2 rows need their source records read; A1 and REL-01 remain the
release-relevant ones).

## Sweep batch 2 — INT-01, SEC-01-multipart, PER-04 fixed (2026-09-18)

**Three audit P3s fixed (`0596211`), each verified live in the tree first, each small enough to fix
correctly now.** (1) **INT-01** — `kel:artifact-reveal` was the only privileged IPC handler without
the sender-frame guard its four siblings carry; it now requires the main frame and a `file:` URL
before touching the OS. (2) **SEC-01-multipart** — `_multipart` interpolated the caller's filename
raw into `Content-Disposition`; every parameter now passes `_header_safe`, so a crafted name cannot
start a header line while clean names stay byte-identical. (3) **PER-04** — a `KEL_DATA_DIR`
override can put `kel-credentials.json` inside the backup root; `Backup.create` now skips and
reports `NEVER_BACKUP`. Also recorded: **DEAD-05** → `DEFERRED_NON_RELEASE` (internal coupling only),
and **TR-01** stays OPEN (still module-level `_STREAMS`; the lifecycle review the finding asks for
has not been done — the row explicitly says it is not cleared). Tests: 5 new + 41 focused passed;
desktop `tsc` 0; **full engine suite 905 passed** (+10 subtests, was 900). The IPC guard has no
automated test (no Electron/IPC harness here) — recorded as audit target §58 rather than claimed.
Sweep status: **11/27 rows dispositioned** (P2 1/10, P3 10/17). Next: the remaining P2s, starting
with A1 and REL-01.
