# RESUME — exact continuation

1. Work in `C:\Users\Nick\Desktop\Kel\kel-v2` on branch `dev/v2` (shared object database lives in
   `Kel-Repo\.git`; never clone, never touch `main`).
2. Read `docs/v2/MARATHON_DIRECTIVE.md`, then `docs/v2/MARATHON_STATE.md`, then this file.
3. Reconcile git (`git status`, `git log --oneline -3`, `git worktree list`); preserve any coherent
   uncommitted work you find — do not reset, discard, stash or restart it.
4. Continue the exact `next_item` from `MARATHON_STATE.md` — currently **V2-05-send**: finish the iPhone
   Kel PWA journey work. The phone surface, the PWA contract, the gateway blocker and **mobile voice**
   (real browser → gateway → engine → Muse, the transcript landing in the composer) are done and
   evidenced in `docs/v2/evidence/v2-05/README.md`; what remains, in order:
   (a) **browser voice — done.** `KelMicButton` now uses the shared `kelRequest` transport (preload on the
       desktop, the `/kel` gateway in a browser) and never swallows a failed `stream_start`. Keep both
       properties if you touch it again. Follow-up only: multi-utterance dictation (see
       `KNOWN_LIMITATIONS.md`).
   (b) **send with a model connected** — the composer's send is gated on a connected model; connect one
       (the phone can reach Providers: 4 providers, 2 usable) and prove type/paste → send → continue.
   (c) **job-driven attention actions on the phone** — approvals, grants, resume, stop and review need
       real job state; create it honestly (no fixture providers) and exercise the phone's offers.
   (d) **conversation history from the phone** — the seeded conversation is authoritative and visible
       through `/api/state`, but the drawer that lists it was not opened in this increment.
   The Connections program (V2-01 … V2-04) is closed; two of its needs are carried as explicit
   follow-ups in `FEATURE_LEDGER.md` (V2-04a: a tool the assistant can call an action through; V2-04b: the
   OAuth sign-in flow) — pick one up deliberately, do not assume it was done.
5. Per increment: understand → narrow design → implement → self-review → focused tests → commit
   atomically → update durable state (`MARATHON_STATE.md`, `FEATURE_LEDGER.md`,
   `IMPLEMENTATION_STATUS.md`, `TEST_EVIDENCE.md`, `DECISIONS.md`, and `DOGFOOD_FINDINGS.md` when real
   feedback lands) → continue to the next dependency. Do not stop at a clean checkpoint.
6. Run the real thing the way this increment did (no CSS reasoning): engine at
   `C:\Users\Nick\KelV2Runs\prepared\engine`, renderer via `bun run package`, gateway via
   `bun run webui` with `KEL_DATA_DIR` + `AIONUI_STATIC_DIR`, then
   `bunx playwright test tests/e2e/kel-mobile.e2e.ts` with `KEL_DEV_PASSWORD` from the gateway log.
   Kill the gateway by PID when restarting it — a stopped session left the first one listening and the
   old code kept answering (that cost a full diagnosis cycle).

Guard rails: `C:\Users\Nick\KelDogfoodCandidate` and `C:\Users\Nick\KelDogfoodRuns\prepared` are
protected (never install/clean/modify them); V2 test data goes to `C:\Users\Nick\KelV2Runs\prepared`;
install `C:\Users\Nick\KelV2Candidate` only when a checkpoint genuinely needs installed-app
verification.
