# 11 — RECOVERY / LIVENESS

Audit target `08f56673…`. Sources: probe-3 (§D/E), packaged R10/R12 evidence review, suite re-run, auditor r10 run on the auditor-built package (result appended when complete).

## Executed stunts (engine level)

- **Expired run → classification:** claims a run, forces `expires` into the past → `Store.recover_expired()` moves the run to **ORPHANED**, issues a **fresh epoch**, sets the milestone **UNCERTAIN** ("Expired run; native state requires reconciliation"), verdict UNCERTAIN; `assess()` stays UNCERTAIN. PASS.
- **Stale delivery never applies:** enqueues a result under the OLD epoch; `consume()` marks it handled but the run remains ORPHANED — no fabricated completion. PASS. (Mirrors `test_v16_r2/r6` families, which also pass in the re-run suite.)
- **Retry durability across restart:** see 08/06 — attempts persisted; third claim refused once the max-2 budget was spent. No counter reset on a fresh `Store` instance. PASS.
- **Uncertain stays uncertain / no blind replay (effect side):** contradictory effect receipts refused, evidence kept; `prepare_effect` refuses identity reuse for a different action. PASS. (probe-1 §C.)

## Packaged evidence (reviewed; not re-run for lane package)

- R10 journeys `r10-f`/`r10-g` evidence review: `[KEL-LINK]` transitions (connected → reconnecting → recovered ×2 → unrecoverable → manual retry → recovered); durable folder + conversations preserved; `rawLeaks: []`, `consoleErrors: []`; 7 screenshots; fail-fast timing story consistent with the retained timestamps (reconnect#1 00:09:35.236 → unrecoverable 00:09:40.249 ≈ 5.01 s; manual recovery 0.53 s). Per-attempt "2 ms" detail not retained (**AUD-MINOR-004 addendum d**).
- R12 installed probes (Campaign A) plus **the auditor's own installed-package probe on the auditor-built RC package**: healthy boot, engine 1.6.0, attention section present, About K renders, 0 console errors, 0 raw leaks, 0 overflow (evidence: `evidence/auditor-installed-probe*`).
- **Engine-loss journey re-run on the auditor-built INSTALLED package — PASS** (evidence: `evidence/auditor-r10/` + `auditor-r10.log`): healthy boot (engine 1.6.0) → kill #1 → reconnecting → recovered (fresh pid 29640) → kill #2 → reconnecting → recovered (fresh pid 15940, attempts=2) → kill #3 → **unrecoverable** (attempts=2; no third blind restart) → manual retry → reconnecting → **recovered** (fresh pid 44980). Conversations (`main` + uuid), project, and the seeded durable folder survived; honest-state notices matched the corpus copy; `consoleErrors: []`, `rawLeaks: []`; 4 screenshots (reconnecting / recovered / could-not-recover / after-manual-retry). This independently reproduces the packaged R10 story on a separately built package.

## Limits recorded

- No independent broker/provider/verifier-interruption harness was built beyond the suite and the probes above; the engine-loss variants that need in-flight approvals/effects are not constructible in the isolated profile (same limitation the corpus records).
- Recovery paths were observed not to widen authority (fresh epochs fence stale ownership; no grant path involved) — stated as observed behavior, not a proof.
