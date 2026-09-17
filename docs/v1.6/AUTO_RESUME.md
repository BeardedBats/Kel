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
| 4 i18n / donor-string cleanup | **PAUSED — WIP preserved in git stash** `MAIN-PHASE4-WIP-BEFORE-P1-CAPABILITY-REMEDIATION` (do not drop) | recovery artifact `C:\Users\Nick\Desktop\Kel\ux-audit\PHASE4_WIP_BEFORE_P1_REMEDIATION\` |
| 4–15 | pending | see the program brief (Phase 4 resumes only on explicit instruction; the stashed WIP must be restored first) |

Latest verified candidate: `dist/package-p1cap/win-unpacked` (P1 capability remediation evidence;
packaged engine hash matches the fresh `dist/runtime` build). `dist/package-final16` remains the
Phase 3 evidence artifact; `package-final13`/`final15` are the memory/lineage evidence artifacts;
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
  items (PER-02, PER-03, stale `_OFF`/`_ON` — now replaced by the strict command patterns as a side
  effect, sender-frame validation, `KEL_DATA_DIR` backup credentials edge, `packaging/ux-audit.cjs`
  (now actively used as the gate harness)).
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

## Verify quickly (any resume)

1. `cd runtime && python -m pytest tests -q` → 604 passed (+10 subtests).
2. `cd desktop && bunx tsc --noEmit` → 0; `bun run test` → 76.
3. Packaged journeys (edit `APP` inside each to the current candidate first):
   `bash ux-audit/run-p1-capabilities.sh` (needs `package-p1cap`; sessiontools + packaged engine
   capability probe), `bash ux-audit/run-approvals.sh` (needs final16), `bash
   ux-audit/run-lineage-probe.sh` (now final16), `bash ux-audit/run-memoryprops.sh` (needs final13).

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
- Conversation capability commands are strict and explicit (`web: use default`, "don't use the
  browser here"); an explicit `capability: state` clause inside a longer message applies and the rest
  of the message is forwarded. Ordinary sentences never change capability state.
