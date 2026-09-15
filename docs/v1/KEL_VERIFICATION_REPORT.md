# KEL V1 — VERIFICATION REPORT

Date: 2026-09-14. Scope: the repackaged `Kel-Windows-0.5.0-complete-fixed` workspace (new app.asar + rebuilt KelEngine 0.5.0) and the engine source changes behind it.

## 1. Automated test suites

| Suite | Result |
|---|---|
| Engine unit/integration (`Kel-Prototype/tests`, pytest) | **150 passed** (release baseline was 143; +7 new) |
| New: `test_service_routing.py` (classify wiring, status fast path, template compile, client-kind precedence) | 4 passed |
| New: `test_acp_host.py::test_side_question_during_active_prompt_keeps_job_and_resumes_conversation` | passed |
| New: `test_acp_host.py::test_awaiting_user_emits_permission_guidance_with_action_summary` | passed |
| New: `test_core.py::test_cancel_racing_launch_finalizes_with_terminal_receipt` | passed |
| Electron app bundle (electron-vite build, aion-donor source) | builds clean; renderer chunk hashes unchanged from shipped set |

## 2. Live verification against the packaged artifacts

### 2.1 Packaged engine boots and serves

- Launched `resources/kel-engine/KelEngine.exe --data <fresh-dir>` from the workspace package.
- `desktop-session.json` reported `engine_version: 0.5.0`; `/api/state` returned providers (codex, claude, codex-code, claude-code) and healthy status.

### 2.2 Deterministic routing live (no model keys required)

- `POST /api/send {text: "status"}` → submission DISPATCHED, assistant replied "No work is running." — proves `router.classify` wiring + status fast path through the real HTTP surface.
- `POST /api/send {text: "Write a short plan for a weekend hike"}` → kind `document` (classification), job created with `compiler: document-template-v1` and the three template milestones — proves the untyped-request → deterministic contract path.

### 2.3 Adversarial: cancel racing worker launch (the D-17 bug)

- First reproduction (pre-fix build): cancel during claim/broker-launch left run `CANCEL_REQUESTED`, job `CANCELLING`, inbox receipt discarded — permanent stranding confirmed in the live DB.
- After fix, same scenario on the rebuilt shipped exe: job settled **CANCELLED**, run `('CANCELLED', reservation 0)`. PASS.

### 2.4 Shutdown drain semantics

- `/api/shutdown-idle` (POST) with an open job → 400 "Work is still open…". PASS.
- After the job settled → `{'ok': True, 'draining': True}` and the listening port closed. PASS.

### 2.5 Kel web UI (bundled in the engine)

- Opened `http://127.0.0.1:<engine>/#token=…` with Playwright against the live engine: title "Kel", body shows New chat / Search / Project & Conversations nav / Saved context / "Running on this computer" status / Files & Work details buttons; screenshots captured (`_kel-work/ui-main.png`, `_kel-work/ui-menu.png`).

### 2.6 Packaged asar integrity

- `@electron/asar list` diff vs the original: identical `node_modules` (10,298 files, 0 missing); the only removed entries are stale orphan renderer chunks from an older build generation that `index.html` no longer references.
- New main bundle contains: `before-quit` → POST `/api/shutdown-idle`; no `aion-host.json` write; stale-mapping deletion on 404.
- Control experiment: launching the packaged app with the ORIGINAL asar restored reproduced the exact same second-instance behavior as the new asar — the repack introduces no new startup behavior.

## 3. What was exercised and how

- Worker routing: engine tick claim path traced in source + 150-test suite + live provider detection.
- Background jobs: live document job dispatch/cancel through the durable store.
- Failure recovery: cancel-race settlement (fixed), provider failover paths (source-verified: `wait_for_route`/`retry_route` + circuit/quota filters).
- Approval interruptions: ACP host guidance text (unit-tested), approval state machine (engine tests).
- Restart recovery: existing engine tests cover broker adoption, orphan fencing, pending-check recovery (test_broker_recovery, test_coding_recovery, test_review_recovery, test_isolated_recovery).
- Native-session continuity: existing tests + source (`native_session` persistence, `--resume`, ACP `thread/resume`).
- Deterministic workflows: document/coding/research compilers (existing + new tests).
- Single-voice synthesis: existing `combined-result` milestone tests.

## 4. Launch verification of the exact packaged release (completed after the P0 fix)

1. **Full packaged GUI launch** — the exact workspace `Kel.exe` (fixed asar) was launched as the only instance: the window opens (title AionUi), the process stays alive, `aioncore` and a freshly spawned `KelEngine` stay alive, and the renderer loads. `[KEL-BOOT]` boot sequence captured from the daily log.
2. **Agent registration** — AionCore reports the Kel agent `online`, command = the space-free staged engine path, `last_check_error_message: null`.
3. **Status query over ACP** — `initialize → session/new → session/prompt("status")` against the staged engine returns "No work is running.".
4. **Graceful shutdown** — closing the window removes ALL of Kel.exe / KelEngine.exe / aioncore.exe (blocking drain hook). Zero orphans.
5. **Relaunch** — a second clean launch succeeds and re-registers the agent.

Remaining deliberate exclusions: **real external-agent runs** (Codex/Claude CLI with live quota) are still not exercised against the user's paid subscriptions — the cancel-race test spawned and immediately cancelled one `claude` worker (no meaningful cost).

## 5. Adversarial checklist from the audit brief

| Scenario | Result |
|---|---|
| Worker falsely claims completion | PASS (existing tests: worker success ≠ completion; `assess` is the only completion producer) |
| Worker performs only part of a multi-step job | PASS (milestone checks + `assess` require all ACCEPTED) |
| Cheap worker fails verification | PASS (NEEDS_REPAIR → bounded retry, accepted work preserved) |
| Side question while job active | PASS (engine: durable jobs; ACP: supersede semantics added + tested) |
| Kel restarts during a job | PASS (broker adoption/orphan fencing — existing tests) |
| External agent requests permission | PASS (approval machinery + ACP guidance text added + tested) |
| Provider becomes unavailable | PASS (circuit break, quota, failover — source + tests) |
| Reviewer disagrees with creator | PASS (independent review boundary; executor≠reviewer enforced in store) |
| Subjective task | PASS (manual_review rubric checks → UNCERTAIN, never silently VERIFIED) |
| Parallel worker failure | PASS (per-milestone isolation; failed branch does not touch accepted milestones) |

## 6. Conclusion

All P0/P1 drift items from `KEL_V1_DRIFT_AUDIT.md` are resolved in the shipped artifacts, and the release-blocking launch P0 (D-19) is fixed and verified live on the exact packaged `Kel.exe`. Remaining open items are documented limitations (reviewer model-diversity under a single API key; donor-UI settings surfaces; no user-defined workflow recipes; no quality-signal producer). Every required skeleton bone is PASS or documented-UNVERIFIED with a concrete reason in `KEL_V1_SKELETON_MATRIX.md`.

## 7. Greenfield coding acceptance — live packaged-app run (2026-09-14, run 2)

Exact request submitted through the packaged UI: "I want to create a little app that allows me to control my microphone's mute button, to turn it on and off from my keyboard".

### 7.1 Root causes fixed by this run

1. **Wrong kind routing.** `router.classify` returned `conversation`; `Service._plan` only special-cased `chat`/`None`, so "I want to create …" fell into the document template → `CLOSED / UNCERTAIN` with no artifact. Fix: greenfield-intent regex (`GREENFIELD_RE`) classifies build/create + deliverable-noun requests as `coding`, and `_plan` treats `conversation` like `chat`.
2. **No greenfield path.** Coding required an existing project root + stored test command. Fix: greenfield flow creates `Documents/Kel Projects/<slug>-<hex>`, `git init` + empty initial commit (HEAD must exist for the snapshot diff), `.gitignore`, a stored test command `['python','smoke_test.py']`, and instructs the worker to create the app AND a passing smoke test. Greenfield intent overrides even a rooted active project (desktop temp workspace).
3. **Reviewer impossible without ANTHROPIC_API_KEY.** `manual_review` can never be judged when the internal reviewer is unconfigured → every document job ends UNCERTAIN with "Independent rubric review not recorded". Fix: when no internal key exists, the Commander falls back to an installed native CLI (claude) for planning/review (`KEL_REVIEWER=none` opts out in tests).
4. **Opaque failure message.** `publish()` now appends the specific blocker ("Blocker: <reason>") instead of only "I could not verify the complete result.", and VERIFIED greenfield coding publishes the project location.
5. **Duplicate work card.** `getMessageMergeKey` keyed ACP tool calls by row id/msg_id, which differ between the live ACP stream frame and the persisted AionCore row for the SAME job → both rows survived the history-prepend dedupe → two "View Steps · 1" cards. Fix: ACP tool calls now merge by the stable `content.update.tool_call_id`. (AionCore rows and the Kel history mirror each hold exactly one row per job — duplication was renderer merge keying, not persistence.)

### 7.2 Live trace (submission `acp-d47b8845…`, job `23a41dd3-5bea-4d8d-8dfe-870326db22af`)

- Classification: `kind=coding`, `greenfield=True` (submission_packets).
- Contract: `coding-contract-v2`, root `C:\Users\<user>\Documents\Kel Projects\i-want-to-create-a-little-app-that-a-121b` (git repo, HEAD present), `test_command ['python','smoke_test.py']`.
- One submission, one job for the conversation (counts = 1).
- Provider route: `claude-code` (coding via the Codex ACP transport; codex-cli 0.142.5, ChatGPT login; `codex-code` excluded by quota in the same route decision).
- Worker created `mic_mute.py` (pycaw Core Audio + tkinter hotkey UI, Ctrl+Shift+M toggle / Ctrl+Shift+Q quit, demo-mode fallback), `requirements.txt`, `smoke_test.py` (14 tests).
- Deterministic verification executed: test run exit 0 ("Ran 14 tests OK"), `existing_tests_preserved=true`, `source_stable_during_tests=true` → `repository_evidence` VERIFIED.
- Independent review recorded VERIFIED by native-claude reviewer `d61164ea…` (7 findings; honest limit: real hardware mute not exercisable headlessly).
- Job CLOSED / **VERIFIED**; publication: "Your new project is ready at C:\Users\<user>\Documents\Kel Projects\i-want-to-create-a-little-app-that-a-121b. The code passed its tests and a separate review. …"
- Apply checked changes → 3 files written to the project folder (backup saved). `python smoke_test.py` re-run in the final location: 14/14 OK. GUI launched and stayed alive (demo mode — this machine exposes no microphone capture endpoint, the documented fallback; logic verified via patched controller round-trip).
- UI: exactly one "View Steps · 1" work card in the conversation (AionCore holds one `acp_tool_call` row: id=tool_call_id=job id, status completed, title "Kel work: CLOSED / VERIFIED").
- Clean shutdown: closing the window removes all Kel.exe / aioncore.exe / KelEngine.exe; relaunch with the patched asar opens the window and respawns both backends.

### 7.3 Packaging parity (rebuilt KelEngine)

- PYZ module inventory identical to the previous engine (218 modules); only the five edited `kel.*` modules differ (+~1.9KB compressed).
- `_internal` inventory identical except 43 UCRT redistribution DLLs (`api-ms-win-*`, `ucrtbase.dll`) that the previous PyInstaller bundled and 6.19.0 no longer ships — OS-provided on Windows 10/11, no functional impact. SQLite (`_sqlite3.pyd`+`sqlite3.dll`), SSL (`_ssl.pyd`+libcrypto/libssl), ctypes, multiprocessing, queue all present and runtime-loaded (verified via the live process module table). Bundled `kel/` data assets byte-identical.
- Exe size 2,785,984 vs 2,783,442 bytes — the delta is exactly the source edits. (An intermediate broken build weighed 2.07MB; it was discarded, not deployed.)
- app.asar: rebuilt from the known-good extracted tree (`aion-runtime-stage`, the deployed 68,058,703-byte package base) with EXACTLY ONE file changed — `out/renderer/assets/MessageList-cBYU-mto.js` (+113 bytes, the `acp_tool_call_id` merge key). Verified by `diff -rq` against the base before packing (diff count = 1).

### 7.4 Environment limits (honestly reported)

- This machine exposes no microphone capture endpoint (pycaw property queries fail), so the acceptance "toggle the real mic" step runs in the app's demo mode — the same limit the independent reviewer recorded. Hardware round-trip requires a machine with a mic; logic, hotkeys, GUI launch, and the test suite are all exercised.
