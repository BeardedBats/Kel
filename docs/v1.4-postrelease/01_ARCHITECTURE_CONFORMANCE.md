# 01 — Kel V1.4 Post-Release Architecture Conformance

Audit date: 2026-09-15 · Auditor: Kun (independent post-release audit)
Release under audit: `main @ 926e346` · tag `v1.4.0` (peels to `0a4fd21`) · frozen at `Kel Releases/Kel-V1.4-Frozen`
Audit discipline: no code changes, no modifications to the frozen release, diagnosis only.

## Primary question

> Did Kel V1.4 actually ship the architecture we designed, or did the gate process allow any core
> skeleton bones to remain structurally incomplete despite the release passing?

**Answer: partially. V1.4 ships the majority of the intended V1 architecture with real implementation
and runtime evidence, but one core skeleton bone — permission/capability-lease enforcement (Bone 19) —
is structurally incomplete: it exists as a tested checker and data model that nothing on the execution
path calls, while the V1.4 policy documents assert that it is enforced. Two further bones (25, 26) are
partial, and two shell bones (23, 24) carry donor-identity leakage. This is exactly the failure class
the audit was asked to look for: the gate process passed a release whose enforcement layer is not
wired to the behavior it governs, and whose documentation overstates that layer.**

## Method and independent reproduction

Evidence was required to converge from three sides: existing gate evidence, source inspection, and
fresh runtime verification. What was independently reproduced in this audit:

| Claim in the release record | Reproduction | Result |
|---|---|---|
| Engine suite 363 + 10 subtests in the working tree | `python -m pytest -q` from `runtime/` | **363 passed + 10 subtests** (76.75 s) |
| Clean clone of the tag re-runs the suite | `git clone` → `checkout v1.4.0` → pytest | **363 passed + 10 subtests** (75.82 s, exit 0) at `0a4fd21` |
| `verify-release.ps1` 3/3 OK on the frozen folder | Ran the official script against a copy at `Kel Releases/Kel-V1.4-Frozen` | **3/3 OK — "Release verification passed."** (also re-verified by independent `sha256sum`) |
| Frozen hashes `e048632e… / 53a34f62… / 5c093e32…` | `sha256sum` on frozen + `dist/release` | All match; frozen == assembled release, byte-for-byte for all three hashed artifacts |
| Engine bundle is current | `packaging/verify_engine_pyz.py` against frozen `KelEngine.exe` | **33/33 modules structurally identical** to `runtime/kel` source, MISMATCH `[]` |
| Adversarial sweep clean | `python packaging/adversarial-review.py` | 5 findings, **0 blocking**; ledger statuses read 58/85/29/28 |
| 0 renderer errors across captures | Parsed all 18 capture manifests under `docs/v1.4/screenshots/` | **0 total console errors**, 2 pet windows (all from the G9-pets candidate run) |
| Upgrade path | `runtime/tests/test_v14_upgrade.py` (UPG-*) in both runs | Passed — migrations 5–9 additive with pre-migration backup |

Frozen-folder provenance cross-checks: `resources/app.asar` and `resources/kel-engine/KelEngine.exe`
in the frozen folder are byte-identical to the candidate build in `dev-tools/runs/v14/candidate`, and
the released documentation set (13 `KEL_V1.4_*.md` files) hashes equal to the tagged docs for the
files checked (`KEL_V1.4_STATUS.md` identical to `0a4fd21:docs/v1.4/…`).

## What is genuinely present (with evidence)

- **Commander / executive ownership (Bone 1)** — `runtime/kel/commander.py` (plan/validate/review),
  `runtime/kel/engine.py` (claims milestones, schedules independent review, composes a combined-result
  milestone for multi-part jobs), `runtime/kel/core.py` (`consume` → `verify` → `assess` → `publish`).
  Worker text never reaches the user directly; publishing is engine-only.
- **Completion authority and verification (Bones 10–13)** — worker results are reduced into the inbox;
  a worker "SUCCESS" is never a verdict. `core.verify()` re-checks artifact digests and coding
  evidence; `core.assess()` alone creates completion; `core.record_review()` refuses an executor as
  reviewer; the coding adapter runs the contract's test command itself, requires existing tests
  preserved, source stability during tests, and a non-empty patch (verdict FAILED otherwise).
- **Durable work (Bones 8–9)** — append-only event log with revision-unique writes and rebuildable
  job projection; detached per-run brokers (`runtime/kel/runner.py`); restart adoption; ORPHANED
  fencing with no blind replay; native process registry; WAL; `native_processes` deadline rows.
- **Routing, providers, recovery (Bones 2–3, 15–18)** — deterministic `router.classify()` is now wired
  (`runtime/kel/service.py:139`); `router.select()` hard-gates on capability/health and orders by cost;
  the provider registry implements the declared state model including `quota_not_reported`
  (`runtime/kel/providers.py:50,142`); readiness returns a recorded reason and fallback chain;
  review outcomes feed provider quality samples (closing the old D-14/D-15 gap); retry excludes the
  previous provider, circuits are 60 s/24 h, and jobs surface honest WAITING_RESOURCE/UNCERTAIN states.
- **Sessions, continuation, contracts (Bones 6–7)** — stored `native_session` is passed on retry and
  resume (`resume <id>` / `--resume` argv in `runtime/kel/native.py`); `continuation.plan_resume()`
  preserves accepted milestones, reopens only eligible ones, revalidates when source digests changed.
- **Memory, recipes, one-voice synthesis (Bones 20–22)** — trust-laddered, provenance-aware,
  project-scoped memory with correction/retraction/conflicts; validated deterministic recipes with
  preview/dry-run; engine-side synthesis with verification summaries.

## The structural gap (headline finding)

**Bone 19 — capability-lease / guardrail enforcement is not on the execution path.**

- Only caller of the enforcement module in the entire engine is the service API itself:
  `runtime/kel/service.py:582-583` (`/api/autonomy`). No runner, coding, apply, or native module
  imports or calls `Autonomy.check`.
- The coding worker path launches the native host with `sandbox_mode="danger-full-access"`,
  `approval_policy="never"` (`runtime/kel/host_runtime.py:37,45,49`; the module docstring itself says
  "This runtime is not a sandbox"), and coding contracts declare `runtime:'native-host'`
  (`runtime/kel/coding.py:33`). Practical containment is the isolated git snapshot + the user-gated
  apply step — not the lease/guardrail layer.
- `role_tool_policies` data exists (`runtime/kel/team.py`) but is never enforced against a worker.
- `guardrail_decisions` exists only in the architecture document; there is no such table or record.
- `emergency_stop` revokes active leases only (`runtime/kel/autonomy.py:326-338`); it does not pause
  or cancel running work.
- Meanwhile `docs/v1.4/KEL_V1.4_SECURITY_MODEL.md:71-72` states "No registry writes, no active-screen
  control, no OS-critical changes, no covert persistence — enforced by the locked guardrail module and
  verified by tests", and `docs/v1.4/KEL_V1.4_AUTONOMY_POLICY.md:34-36,65` promises "tool layer
  refuses before execution; recorded decision". The AUTO-* tests exercise `Autonomy.check()` directly
  (`runtime/tests/test_v14_autonomy.py:20,76-90`) — checker-level proof, not execution-path proof.

Severity: **P1 architectural drift** (documented enforcement that does not exist at runtime). Fix
options and version targeting are in `06_V1_4_1_DEFECTS.md` (D-01/D-02).

## Secondary findings

- **Donor-identity leakage (Bones 23–25, P3):** tray tooltip `'AionUi'`
  (`desktop/packages/desktop/src/process/utils/tray.ts:265`), web notification title `'AionUi'`
  (`useBrowserNotification.ts:66`), donor pages still shipped/reachable (`pages/team`, `pages/cron`,
  `pages/conversation`, `pages/login`, `TestShowcase`), donor copy in
  `ChannelConflictWarning.tsx`, and the bundled donor runtime
  (`resources/bundled-aioncore/win32-x64/aioncore.exe`, not stored in git — `desktop/KEL-FORK-NOTES.md`).
  Kel mode itself is clean where it matters most: the default chat shows "Automatic" instead of a
  model selector for the Kel assistant (`pages/guid/GuidPage.tsx:585-587`).
- **Version labeling (P3):** `ENGINE_VERSION='0.5.0'` (`service.py:24`) and `desktop/package.json`
  `"version": "0.5.0"` while the product is V1.4.0; the diagnostics page surfaces "Engine 0.5.0"
  (`pages/kel/diagnostics/index.tsx:106`).
- **Packaging hygiene (P3):** `debug.log` (288 B, ICU messages dated 2026-09-13) is copied into the
  frozen folder from the frame; `SHA256Sums.txt.txt` lists bare hashes without filenames; the donor
  `aioncore.exe` in the release is not covered by the sums file.

## Evidence convergence statement

Gate evidence, source inspection, and fresh runtime reproduction converged for every bone except:
(1) Bone 19, where the gate evidence claims enforcement and the source shows there is none — the
disagreement is real and is this audit's central finding; (2) the pet-capture limitation, where the
frozen artifacts are byte-identical to the candidate that captured 2 pet windows, so the assembled
run's 0-pet result is a capture-harness/environment variance, not packaging drift (see
`05_RELEASE_LIMITATIONS_REVIEW.md`); (3) the consistent `close-timeout` in every capture run, which is
the recorded bounded-kill limitation and is state-safe by design.

Detailed per-bone statuses and citations: `02_SKELETON_MATRIX.md`.
Ledger classification: `03_LEDGER_TRIAGE.md`. Adversarial scenarios: `04_ADVERSARIAL_RESULTS.md`.
