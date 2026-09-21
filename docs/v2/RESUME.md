# RESUME — exact continuation

1. Work in `C:\Users\Nick\Desktop\Kel\kel-v2` on branch `dev/v2` (shared object database lives in
   `Kel-Repo\.git`; never clone, never touch `main`).
2. Read `docs/v2/MARATHON_DIRECTIVE.md`, then `docs/v2/MARATHON_STATE.md`, then this file.
3. Reconcile git (`git status`, `git log --oneline -3`, `git worktree list`); preserve any coherent
   uncommitted work you find — do not reset, discard, stash or restart it.
4. Continue the exact `next_item` from `MARATHON_STATE.md` — currently **V2-04, continuing: actions/tools**
   (`status: partial`). The `V2-04 notes for the next run` block says what is built and exactly what is
   not; do not mark V2-04 done or move past it while actions/tools and the OAuth sign-in step are missing.
5. Per increment: understand → narrow design → implement → self-review → focused tests → commit
   atomically → update durable state (`MARATHON_STATE.md`, `FEATURE_LEDGER.md`,
   `IMPLEMENTATION_STATUS.md`, `TEST_EVIDENCE.md`, `DECISIONS.md`, and `DOGFOOD_FINDINGS.md` when real
   feedback lands) → continue to the next dependency. Do not stop at a clean checkpoint.

Guard rails: `C:\Users\Nick\KelDogfoodCandidate` and `C:\Users\Nick\KelDogfoodRuns\prepared` are
protected (never install/clean/modify them); V2 test data goes to `C:\Users\Nick\KelV2Runs\prepared`;
install `C:\Users\Nick\KelV2Candidate` only when a checkpoint genuinely needs installed-app
verification.
