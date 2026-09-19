# AUDIT STATUS — Campaign B (living document)

Last updated: 2026-09-19 — checkpoint after probe-1, first findings pass, and brand/frozen/package spot verification.

## Fixed audit target
- `08f56673ea93ed84568018937bb190e0a5acd71b` — PRE_AUDIT_V1_6_HEAD (verified; immutable; re-checked clean after every operation).

## Audit branch / worktree
- Branch `audit/v16-final`; worktree `C:/Users/Nick/Desktop/Kel/kel-v16-final-audit`.
- Audit commits so far: `6efbbcb`, `4105fda`, `a03b90a`, `298ce31`, `ac8a9bb`, (+ amendment/status commits after this one; see `git log`).

## Independent runs executed by the auditor
- Engine full suite (audit worktree at RC): **998 passed, 10 subtests passed, exit 0** in 349s — reproduces the claimed counts (`evidence/auditor-engine-suite.log`).
- Desktop vitest (RC tree): **122 passed / 122, 12 files, exit 0** — matches claim (`evidence/auditor-desktop-vitest.log`).
- Probe-1 attack battery (`probes/auditor_probe_1.py`, `evidence/auditor-probe-1.log`): approvals scope + omission bypass, approval window/duplicate, effect idempotency/replay, canonical encode, delegation widening, budget envelope, capability grammar, credential sentinels, packaged DB migration receipts.
- Claude real probe: exit 0, returned `ok` (client 2.1.215) — `evidence/provider-claude-probe.txt`.
- Codex real probe: exit 1 — environment limitation re-confirmed ("'gpt-6-astra' model requires a newer version of Codex", HTTP 400) — `evidence/provider-codex-probe.txt`.
- Frozen spot hashes: pre1 + V1.5 `Kel.exe` recomputed — both exact; candidate-vs-frozen byte-identity confirmed for pre1 `Kel.exe` — `evidence/frozen-hash-spotchecks.txt`.
- Packaged DB receipts: `r12-fresh2` and `r12-upgrade` stores both max migration **21** (`v16-budget-reservations`).
- Packaged exe metadata (package-r12): ProductName=Kel / FileDescription=Kel / CompanyName=Kel / FileVersion=1.6.0.
- **Brand assets check: PASS** — `make-brand-assets.py <canonical> --check` exit 0; canonical sha256 `7418a42f...` matches BOTH `C:/Users/Nick/Desktop/Kel Logo.png` and the in-repo copy `desktop/resources/branding/kel-logo.png`; all nine generated assets verified against recorded hashes (check mode, no files written) — `evidence/auditor-brand-assets-check.log`.
- RC worktree cleanliness after all auditor runs: verified clean (no tracked/untracked residue in `kel-ux-v15`).

## Pass progress
| Pass | Status |
|---|---|
| 0 repo integrity | MOSTLY COMPLETE — identity/range/refs/ledger coverage recorded; remaining frozen-hash recomputes queued |
| 1 commit review | IN PROGRESS — classification 73/73; deep review done for R-series core + APR-02/SEC-01/TR-01 paths, delegation/contracts/chat_approvals/service; full diff archive on disk (`evidence/diffs/`) |
| 2 requirements | IN PROGRESS — REQUIREMENTS_TRACEABILITY read; both-direction sweep started; stale-row findings recorded |
| 3 invariants | IN PROGRESS — 30-family table (`05_INVARIANT_ATTACKS.md`); executed: AUTH-DELEGATION, IDEMPOTENCY, EFFECT-REPLAY, APPROVAL-EXACT, PERSIST-CANONICAL, CRED, CAPABILITY-GRAMMAR, PACKAGE/FREEZE/DB receipts. Queued: memory, live-authority, verifier, lease, IPC, WF, lineage, retry-restart, liveness stunts, restore injection |
| 4 historical P2/P3 | IN PROGRESS — docket corroborated (P2 10 / P3 16; 27 = worklist arithmetic); per-row re-verification queued |
| 5 migrations | IN PROGRESS — max 21 verified (constants + packaged DBs) |
| 6 security/isolation | IN PROGRESS — AUD-MAJOR-001; IPC handler read + memory/vetting batteries queued |
| 7 workforce | STARTED — delegation attacked; pods/verifier/flag-off attacks queued |
| 8 memory | NOT STARTED (queued) |
| 9 approvals/capabilities | IN PROGRESS — probe-1; UI call sites verified to declare conversation |
| 10 recovery/liveness | PARTIAL — suite green; live stunts queued |
| 11 transcription/vetting | NOT STARTED (queued) |
| 12 desktop/UX | NOT STARTED systematic; donor/brand residuals investigated |
| V visual | IN PROGRESS — evidence cross-check; human gate PENDING |
| P package | IN PROGRESS — metadata/frozen/migrations verified; auditor rebuild + install/uninstall queued |
| BR brand/donor/dead surface | IN PROGRESS — brand check PASS; donor findings 007/008; sweeps continuing |
| J journeys / BS blind spot | NOT STARTED (queued) |

## Findings (see MASTER_FINDINGS.md)
- AUD-BLOCK: 0 · AUD-MAJOR: **1** · AUD-MINOR: **8** · AUD-SUG: **1**
- No target/remote/frozen-ref integrity discrepancy found (binding-level).

## Tooling anomaly note (recorded for honesty)
- In this environment, two `write` calls and one oversized `bash` call were replaced/truncated in transit (placeholder text / EOF-mid-heredoc). All were detected by size/head verification; affected files were rewritten and re-verified; subsequent tool calls stay small and are verified after each write.

## Queue (next actions, in order)
1. Memory-provenance battery (targets 10-13, 32-39) + vetting session cross-scope + transcription batteries.
2. IPC handler-set read + Needs-Your-Attention derivation checks.
3. Workforce attacks: Commander spawn, verifier==builder, flag-off parity, never-gate, bound evidence, lease.
4. Package pass: auditor rebuild from RC + controlled install/uninstall + engine hash table (source -> staged -> packaged -> installed) + remaining frozen hashes.
5. Live-authority + retry-restart + liveness stunts; completion/recovery classification probes.
6. `..` consumer analysis (AUD-MINOR-006); pet reachability (008); aioncore provenance binding (007).
7. Pass 2 completion (requirements both directions + undeclared-behavior sweep).
8. Journeys A-E, blind-spot pass, MASTER_FINDINGS finalization + release assessment.
