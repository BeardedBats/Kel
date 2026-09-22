# RESUME — exact continuation

1. Work in `C:\Users\Nick\Desktop\Kel\kel-v2` on branch `dev/v2` (shared object database lives in
   `Kel-Repo\.git`; never clone, never touch `main`).
2. Read `docs/v2/MARATHON_DIRECTIVE.md`, then `docs/v2/MARATHON_STATE.md`, then this file.
3. Reconcile git (`git status`, `git log --oneline -3`, `git worktree list`); preserve any coherent
   uncommitted work you find — do not reset, discard, stash or restart it.
4. Continue the exact `next_item` from `MARATHON_STATE.md` — now **V2-18 synthetic V2 acceptance
   journeys, IN PROGRESS**: the checklist is `docs/v2/evidence/v2-18/ACCEPTANCE_MATRIX.md` and the
   executable journeys are `runtime/tools/acceptance_journeys.py` (it attaches to an engine only after
   proving the recorded pid is alive, its command line names the data root, and the recorded port is
   owned by that pid — `desktop-session.json` is a file, not a fact). Start one owned engine with the
   desktop's protection set:
   `KEL_PROTECTED_PATHS='C:\Users\Nick\KelDogfoodCandidate;C:\Users\Nick\KelDogfoodRuns\prepared'
   python -m kel.service --data C:/Users/Nick/KelV2Runs/prepared/engine` (from `runtime/`), then
   `python tools/acceptance_journeys.py --root <root> --journeys <ids> --out <evidence json>`.
   **State at this checkpoint (2026-09-22, `dev/v2` @ `492b9a0` + `7b18618`):** V2-06, V2-07 and
   V2-08 are BUILT (D-50) — attention rows, the recipe library's own surfaces (migration 30
   `v2-recipe-library`) and `/api/activity` — and the journeys J-FIX, J-UPGRADE, J-SEC, J-KBU
   (C1–C4 + negatives), J-PROJ, J-MEM, J-NET, J-CONN, J-TRANS, J-CONV, J-MODEL, J-RECIPE and
   J-ACTIVITY have all PASSED on the real root (evidence under `docs/v2/evidence/v2-18/runs/`).
   **Remaining unchecked journeys: J-WORK, J-RECOV, J-ATTN (backend) and J-REMOTE (gateway), then the
   Shell/phone ones.** The web-host deep-link cause is fixed and pinned
   (`packages/web-host/src/static-server.unit.test.ts`, 15 tests on the merged line). The integration
   line `integration/v2` @ `fe5e6b7` in `C:\Users\Nick\Desktop\Kel\kel-v2-integration` merges Astra's
   committed Shell baseline `ux/v2-shell` @ `0052075` (verified from the merge's second parent; the rest
   of this file's line list is unchanged); its renderer suites (`desktop/tests/**`, `tsc`)
   and a packaged candidate are **not** verified yet — `desktop/node_modules` there is a junction and
   needs a real `bun install`. See `docs/v2/evidence/integration/README.md`.
   **NEXT ACTION, in order:** (1) the three remaining backend journeys on a fresh owned engine;
   (2) `bun install` in the integration worktree, then its bounded renderer suites; (3) package a
   candidate at `C:\Users\Nick\KelV2Candidate` — the path does not exist yet, so nothing has to be
   preserved or rolled back, and installation stays behind Nick's explicit decision.
   **DONE on the integration line this turn (`integration/v2` @ `3f8e1de`):** `bun install
   --frozen-lockfile` + the production renderer build ran *there*; **J-WORK, J-RECOV and J-ATTN all
   PASSED** on an engine started from that worktree's `runtime/` (evidence
   `docs/v2/evidence/v2-18/runs/2026-09-22-slice5|6|7.json`); the gateway's local password recovery
   was repaired (loopback-only, 17 web-host tests pass) and browser-verified (deep link → 302 →
   `#/conversation/<id>`, sign-in loads the shell, refresh keeps the session).
   **THE EXACT CONTINUATION:**
   (a) the candidate pack was still running when the turn ended:
   `cd C:\Users\Nick\Desktop\Kel\kel-v2-integration\desktop` then
   `AIONUI_BACKEND_LOCAL_BUNDLE_DIR="C:/Users/Nick/KelDogfoodCandidate/resources/bundled-aioncore/win32-x64"
   NODE_OPTIONS="--max-old-space-size=8192" node scripts/build-with-builder.js auto --skip-native`
   → the app lands in `kel-v2-integration\dist\package-r12\win-unpacked` (this was the second
   attempt; `--pack-only` skips the distributable entirely — that mistake is recorded). When it
   finishes: copy the unpacked app to `C:\Users\Nick\KelV2Candidate` (absent at the time of
   writing; preserve anything unknown) and launch `Kel.exe` with isolated V2 data to verify the
   packaged runtime, then record the exe path;
   (b) rebuild the renderer (`bun run package`) and re-check the **destination retention** fix in the
   browser (sign-in should now return to the deep link; measured NOT retained before the fix, root
   cause = `ProtectedLayout`'s guard dropping the location);
   (c) then the remaining verification: `desktop/tests/**`, a browser phone-viewport pass, V2-19
   bounded regression, V2-16 timings.
   **PROCESSES LEFT RUNNING (recorded):** the V2 engine on `C:/Users/Nick/KelV2Runs/prepared/engine`
   (owned; identity proven) and the candidate pack (background session `9a8bpdrh`). The gateway on
   port 33100 was stopped with its aioncore child.
   **PASSED (2026-09-22):** J-FIX, J-UPGRADE, J-SEC, J-KBU (claims C1–C4, including a real codex-code
   repair inside the isolated `repositories/<job_id>` copy and a candidate whose revision has the
   baseline as an ancestor), and the negatives (a cancelled mission claims nothing; a mission whose
   tests can never pass never claims a verified build — D-49). **THE NEXT UNCHECKED JOURNEY IS
   J-MODEL** (drive one real turn, then read the stored route back through `/api/model {action:'why'}`
   and assert the sentence matches the stored decision), then in order J-WORK, J-MEM, J-RECIPE,
   J-ATTN, J-RECOV, J-NET, then the labelled fixtures J-CONN and J-TRANS. Phone/renderer journeys stay
   PENDING for Shell integration. Read `ROADMAP.md`'s V2-18 line and the directive before designing;
   do not build Astra-owned presentation. **Kibble Build Update is BUILT**
   (D-46 corrected D-44; D-47; `docs/v2/evidence/kibble-build-update/README.md`): the mission and
   candidate contract on the existing machinery, `promote()` always refusing, the UI contract recorded
   in `PARALLEL_SHELL_TOUCHES.md`. **V2-17 upgrade reliability, V2-14 network permissions, V2-13
   isolation, V2-12 staffing, V2-11 long-running work, V2-10 learning, V2-09 routing, V2-04b and the
   V2-04 execution hardening are BUILT** (D-34…D-49; evidence under `docs/v2/evidence/`) — do not
   rebuild them. V2-15 needs Nick's real dogfood batches (his Kibble feedback arrives only after
   integrated V2 testing — never block synthetic acceptance on it); V2-16 is largely renderer/Shell;
   V2-19/V2-20 are whole-system phases whose promotion gate is Nick's.
   **V2-05-history is temporarily DEFERRED
   FOR SHELL INTEGRATION** — Astra owns the
   phone drawer/history presentation on `ux/v2-shell`, and implementing it now would overlap; V2-05
   stays PARTIAL and items (c)/(d) below remain requirements, not removed. The phone surface, the PWA
   contract, the gateway blocker, **mobile voice** (real browser → gateway → engine → Muse, the
   transcript landing in the composer) and **send** are done and evidenced in
   `docs/v2/evidence/v2-05/README.md`; what remains, in order:
   (a) **browser voice — done.** `KelMicButton` now uses the shared `kelRequest` transport (preload on the
       desktop, the `/kel` gateway in a browser) and never swallows a failed `stream_start`. Keep both
       properties if you touch it again. Follow-up only: multi-utterance dictation (see
       `KNOWN_LIMITATIONS.md`).
   (b) **send with a model connected — done.** The real blocker was the profile, not the composer: the
       `kel` assistant was seeded only by Electron main (`initializeKel`), so the standalone `bun run
       webui` profile had no assistant the guid page could select and send could never enable (measured:
       zero pills while `/api/assistants` answered). `bun run webui` now performs the same bootstrap
       (`packages/web-host/src/kel-integration.ts`), and the ACP agent registers in module form
       (`-m kel.acp_host` — the script-path form cannot resolve the host's relative imports during
       `initialize`; the desktop source branch got the same fix; packed engines never hit it). Journey H
       proves the round trip: one `kel` pill (auto-selected) → send enables → real reply → settle →
       second turn → second reply ("still here"), post-auth watch clean. Keep both properties if you
       touch either.
   (c) **job-driven attention actions on the phone** — approvals, grants, resume, stop and review need
       real job state; create it honestly (no fixture providers) and exercise the phone's offers.
   (d) **conversation history from the phone — DEFERRED for shell integration (Astra owns the phone
       drawer/history presentation).** The drawer that lists history was not opened in this increment,
       and a full-page load of `/conversation/<id>` rendered a blank body in one authed probe (measured).
       Tapping the home's recent entry text timed out once — try the drawer path first. Pick this up only
       after the Shell integration lands (see `MARATHON_STATE.md`, parallel-ownership section); the
       requirement is kept, not dropped.
   The Connections program (V2-01 … V2-04) is closed; V2-04a (the assistant bridge) and V2-04b (the
   OAuth sign-in flow) are both built and evidenced (`docs/v2/evidence/v2-04a/README.md`,
   `docs/v2/evidence/v2-04b/README.md`) — do not rebuild them; a real Google sign-in still needs
   Nick's own client ID and a browser visit.
5. Per increment: understand → narrow design → implement → self-review → focused tests → commit
   atomically → update durable state (`MARATHON_STATE.md`, `FEATURE_LEDGER.md`,
   `IMPLEMENTATION_STATUS.md`, `TEST_EVIDENCE.md`, `DECISIONS.md`, and `DOGFOOD_FINDINGS.md` when real
   feedback lands) → continue to the next dependency. Do not stop at a clean checkpoint.
6. Run the real thing the way this increment did (no CSS reasoning): engine at
   `C:\Users\Nick\KelV2Runs\prepared\engine`, renderer via `bun run package`, gateway via
   `bun run webui` with `KEL_DATA_DIR` + `AIONUI_STATIC_DIR`, then
   `bunx playwright test tests/e2e/kel-mobile.e2e.ts` with `KEL_DEV_PASSWORD` (mint one with a direct
   loopback POST to `/api/webui/reset-password` on the backend port — `bun run resetpass`'s fast path
   goes through the session gate and 401s, measured).
   Kill the gateway by PID when restarting it — a stopped session left the first one listening and the
   old code kept answering (that cost a full diagnosis cycle).
   Verify with **bounded groups**, never the monolithic run, and record exactly which groups passed on
   the final code (the groups V2-09 used are listed in `docs/v2/evidence/v2-09/README.md`). Inspect
   listener and process ownership before stopping anything — the engine's pid is in the data root's
   `desktop-session.json` — and stop only this run's stack; Astra's worktree processes stay untouched.

Guard rails: `C:\Users\Nick\KelDogfoodCandidate` and `C:\Users\Nick\KelDogfoodRuns\prepared` are
protected (never install/clean/modify them); V2 test data goes to `C:\Users\Nick\KelV2Runs\prepared`;
install `C:\Users\Nick\KelV2Candidate` only when a checkpoint genuinely needs installed-app
verification.
