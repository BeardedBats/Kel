# RESUME — exact continuation

1. Work in `C:\Users\Nick\Desktop\Kel\kel-v2` on branch `dev/v2` (shared object database lives in
   `Kel-Repo\.git`; never clone, never touch `main`).
2. Read `docs/v2/MARATHON_DIRECTIVE.md`, then `docs/v2/MARATHON_STATE.md`, then this file.
3. Reconcile git (`git status`, `git log --oneline -3`, `git worktree list`); preserve any coherent
   uncommitted work you find — do not reset, discard, stash or restart it.
4. Continue the exact `next_item` from `MARATHON_STATE.md` — now **V2-18 synthetic V2 acceptance
   journeys** (backend-safe): synthetic journeys over the V2 backend surfaces on the real paths (the
   engine at `C:\Users\Nick\KelV2Runs\prepared\engine`, no fixtures where a real path exists),
   bounded and grouped so they run one stack at a time. Read `ROADMAP.md`'s V2-18 line and the
   directive before designing; do not build Astra-owned presentation. **The carried priority queue
   (3-10) is exhausted**: V2-15 needs Nick's real dogfood batches, V2-16 is largely renderer/Shell,
   V2-19 (full regression) and V2-20 (release candidate) are whole-system phases, and V2-20's
   promotion gate is Nick's. **V2-17 upgrade reliability, V2-14 network permissions, V2-13 isolation,
   V2-12 staffing, V2-11 long-running work, V2-10 learning, V2-09 routing, V2-04b and the V2-04
   execution hardening are BUILT** (D-34…D-45; `docs/v2/evidence/v2-17/README.md`,
   `docs/v2/evidence/v2-14/README.md`, `docs/v2/evidence/v2-13/README.md`,
   `docs/v2/evidence/v2-12/README.md`, `docs/v2/evidence/v2-11/README.md`,
   `docs/v2/evidence/v2-10/README.md`, `docs/v2/evidence/v2-09/README.md`,
   `docs/v2/evidence/v2-04b/README.md`) — do not rebuild them. **Priority 9's Kibble dev-mission/
   candidate-model definition stays DEFERRED pending Nick's definition** (D-44).
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
