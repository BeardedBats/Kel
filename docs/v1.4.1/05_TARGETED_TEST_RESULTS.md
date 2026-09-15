# 05 — Targeted Test Results (V1.4.1)

All results below are from runs executed for this patch (local time 2026-09-15 evening, Windows,
Python 3.14.3, PyInstaller 6.19.0). Commands are reproducible from the repository root.

## 1. Full engine suite

```
cd runtime && python -m pytest -q
→ 375 passed, 10 subtests passed in 75.60s
```

363 pre-existing tests + **12 new** (`test_v141_boundaries.py`: 10, `test_v141_claims.py`: 2). No
regressions. (One transient Windows temp-cleanup flake was observed once on a pre-existing
service-routing test and did not reproduce on re-run — the same flake recorded during V1.4.)

## 2. New targeted tests

| Test | What it proves |
|---|---|
| `GuardrailTamperTests::test_guardrails_detect_runtime_modification` | `guardrails.assert_intact` and `Autonomy.assert_intact` both refuse a weakened rule set |
| `GuardrailTamperTests::test_engine_refuses_new_work_while_rules_are_modified` | End-to-end: with the rule set modified, `Engine.tick` claims **zero** runs and leaves the job READY; after restore, work is claimed again |
| `ProtectedPathTests::test_predicates_and_apply_refusal` | Frozen/system predicates; a fully verified coding job whose project root sits under `…/Kel Releases/…-Frozen/…` is refused by `apply_checked` **and the filesystem is left untouched** |
| `EmergencyStopTests::test_scope_covers_leases_and_active_and_queued_work` | One call revokes leases, pauses a RUNNING job (run → CANCEL_REQUESTED, job PAUSING), pauses a READY job (PAUSED, resumable), leaves a CANCELLED job untouched; the revoked lease can no longer authorize a write |
| `EmergencyStopTests::test_only_the_user_can_trigger_it` | `worker`/`system`/`reviewer`/`kel`/`admin` actors all refused |
| `ActorBoundaryTests::test_service_rejects_caller_supplied_actor_identity` | `/api/autonomy` rejects payload `actor` for `worker`, `system`, `reviewer`, and even `user`; `/api/approval` rejects it too — identity is derived from the session, never supplied |
| `ActorBoundaryTests::test_emergency_stop_through_the_service_pauses_work` | Through the real `Service`: revokes the lease, pauses the running job, returns `paused_jobs` |
| `ActorBoundaryTests::test_state_reports_engine_version_and_guardrails` | `/api/state` reports `engine_version = 1.4.1` and `guardrails_ok = true` |
| `CredentialCustodyTests::test_engine_stores_a_reference_not_a_value` | Engine DB contains the `credential_ref` and **no** value-shaped secret; empty refs refused |
| `CredentialCustodyTests::test_export_refuses_secret_shaped_provider_values` | A secret-shaped string planted in provider data makes `Diagnostics.export()` raise (allowlist + marker refusal) |
| `ClaimDisciplineTests::test_no_overclaim_phrases_remain` | Pins the eight removed overclaim phrases out of the corrected documents |
| `ClaimDisciplineTests::test_corrected_claims_are_present` | Pins the corrected statements (deferral wording, danger-full-access reality, UI copy) into place |

## 3. Adversarial sweep

```
python packaging/adversarial-review.py
→ findings: 5 | blocking (high+medium): 0
```

Unchanged from V1.4 (no new silent catches; do-not-ship list clean; allowlist intact).

## 4. Engine bundle verification

```
python packaging/verify_engine_pyz.py dist/runtime/KelEngine/KelEngine.exe runtime/kel
→ kel modules in PYZ: 33 · matched: 33 · MISMATCH: [] · RESULT: OK
```

The packaged engine is structurally identical to the patched source.

## 5. Build + packaged smoke (assembled candidate)

- Desktop renderer rebuilt: electron-vite build ✓ (32.9 s) → `desktop/out/{main,preload,renderer}`.
- Engine rebuilt: PyInstaller ✓ → `dist/runtime/KelEngine/{KelEngine.exe,_internal}`.
- `app.asar` repacked from the frozen V1.4 archive + new overlay: **9,556 files, 7,435 unique,
  77,317,093 B → 10,220,315 B deduplicated** (identical dedup savings to the V1.4 build; +4 files
  vs the frozen archive — same delta as the V1.4 candidate).
- Candidate assembled at `dev-tools/runs/v141/candidate` (frozen frame + new asar + new engine +
  corrected docs).

Packaged smoke (Playwright harness, fresh data dir, two widths, four Kel routes):

```
{"ok": true, "shots": 31, "errors": [], "blankSuspect": [],
 "shutdown": {"engineStopped": true, "engineKilled": false, "appExitCode": 0}}
→ closeOutcome: "closed"  (graceful; no bounded kill needed on an idle close)
```

**0 renderer errors, 0 blank-suspect frames, appExitCode 0.** The captured page text proves the
patched shell is what ran: Autonomy shows *“This checker is not yet called on the worker execution
path — enforcement there is deferred (see docs/v1.4.1)”*, the guardrail table header now reads
*“Covered by test”*, the emergency-stop note is present, Providers shows *“not yet injected into
provider runs”*, and Diagnostics renders *“Engine 1.4.1”*.

Note: this run closed **gracefully** (`engineStopped:true`) because no work was open — confirming the
V1.4 “bounded kill” behavior only occurs when the engine refuses to drain open work (recorded
limitation, unchanged).

## 6. Release verification

| Target | Command | Result |
|---|---|---|
| V1.4 frozen (untouched) | `verify-release.ps1` vs its own sums | 3/3 OK |
| V1.4.1 frozen | `verify-release.ps1` vs its own sums | 3/3 OK (hashes in `07_RELEASE_MANIFEST.md`) |
