# Kel v1.6 program — auto-resume (continuation state)

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
| 4 i18n / donor-string cleanup | DONE — restoration restored from stash on `267364e`, completed + committed in this increment | `docs/i18n-cleanup/00_STATUS.md`; locales 12× clean (0 residuals, 247 files valid); tsc 0, vitest 76; packaged `package-final17` copy-scan + standing journeys (`ux-audit/run-phase4.sh`) |
| 5–15 | pending | see the program brief; autonomous Main continues per the charter (Workforce OS research packages must be read before Phase 5 implementation) |

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

- **Safe restoration**: stash `MAIN-PHASE4-WIP-BEFORE-P1-CAPABILITY-REMEDIATION` (base `70d68e4`,
  object `992ab31c…`, 123 tracked files + 1 untracked) was inspected against the recovery artifact
  and applied onto clean `267364e` with **zero file overlap** with the P1/CAP2 remediation; the
  restored file set matched the stash exactly, the restored `SettingsCreateMenu.tsx` hash matched the
  artifact copy (`2838b3c3…`), and `git diff HEAD -- runtime packaging` stayed empty (no CAP fix was
  overwritten). The stash was kept until restoration was proven, then dropped after this increment
  committed.
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

## Verify quickly (any resume)

1. `cd runtime && python -m pytest tests -q` → 613 passed (+10 subtests).
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
