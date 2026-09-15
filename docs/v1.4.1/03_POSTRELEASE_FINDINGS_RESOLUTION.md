# 03 — Post-Release Findings Resolution

Every audit finding from `docs/v1.4-postrelease/06_V1_4_1_DEFECTS.md` (D-01…D-11) and the required
workstreams from the V1.4.1 brief, with the exact disposition. “Bounded” means the implementation did
not change; the claims were corrected to state the real boundary (the brief’s truthful-narrowing
option). Nothing was silently dropped.

## Findings

| # | Finding | V1.4.1 disposition | Evidence |
|---|---|---|---|
| D-01 | Capability-lease/guardrail enforcement not wired (P1) | **Partially wired + bounded.** Two real, fail-closed increments added: tamper refusal for new work (`Engine.tick` → `guardrails.assert_intact`), frozen/system refusal on engine-owned project writes (`apply_changes.apply_checked` → `guardrails.protected_reason`). Everything else stated as checker-level; full execution-path enforcement deferred to V1.5. All overstated documents and UI copy corrected. | `test_v141_boundaries.py::GuardrailTamperTests`, `ProtectedPathTests`; corrected `SECURITY_MODEL`/`AUTONOMY_POLICY`/`ARCHITECTURE`/`TEAM_MODEL`; `test_v141_claims.py` pins the wording |
| D-02 | Native coding host full access vs containment claims (P1) | **Bounded (Option B).** Trust boundary stated exactly in `SECURITY_MODEL` §6 and `02_RUNTIME_TRUST_BOUNDARY.md` §4: user-authorized high-privilege host, full access, not sandboxed, not contained by leases; protections = snapshot topology, Kel-run tests/diff evidence, user-gated apply (now protected-path-checked). Narrowing the host was rejected as destabilizing on Windows; recorded in §3 of the boundary doc. | `host_runtime.py` unchanged; `test_host_runtime.py` (existing full-access assertions); corrected docs |
| D-03 | Emergency stop partial (P2) | **Implemented to scope + wording aligned.** Revokes all active leases **and** pauses all active/queued jobs; runs marked CANCEL_REQUESTED so brokers/adapters stop workers at the next cancellation check; pending approvals cancelled; pending boundary requests remain pending but their leases are revoked. Policy §6 and the Autonomy page now state exactly this (no “stop everything”). | `autonomy.emergency_stop`; `service` wiring (engine cancel events); `EmergencyStopTests` (scope incl. queued/cancelled jobs, resume path), `ActorBoundaryTests` (through the real service) |
| D-04 | Caller-supplied actor gate + token at rest (P2) | **Hardened.** Identity is no longer accepted from the request payload: `/api/autonomy` and `/api/approval` reject any `actor` field; the service supplies `user` from the authenticated local session; the engine refuses any non-`user` actor; the renderer no longer sends `actor`. Token-at-rest remains a documented property of the single-user local model (same-user processes are inside it) — stated in the boundary doc, not hidden. | `service._action`; `ActorBoundaryTests` (spoof attempts for worker/system/reviewer/user payloads all rejected); `EmergencyStopTests::test_only_the_user_can_trigger_it` |
| D-05 | Credential injection claim unimplemented (P2) | **Claim corrected; implementation deferred.** Custody, renderer isolation, and metadata-only engine storage were already true and remain; the “value injected at run time” statement is replaced by the actual state; the reserved `getCredential` helper is marked unused. | `SECURITY_MODEL` §3; Providers page copy; `kelCredentials.ts` comment; `CredentialCustodyTests` (ref-not-value, export refuses secret-shaped provider values) |
| D-06 | Donor identity strings (P3) | Deferred to V1.5 (`06_V1_5_DEFERRED_WORK.md`), unchanged here to keep the patch surgical. | — |
| D-07 | Carried `debug.log` / packaging hygiene (P3) | Deferred to V1.5 packaging tooling. | — |
| D-08 | Version labeling (P3) | **Fixed.** `ENGINE_VERSION='1.4.1'`; `desktop/package.json` version `1.4.1`; diagnostics shows “Engine 1.4.1”. | `service.py`; `desktop/package.json`; `ActorBoundaryTests::test_state_reports_engine_version_and_guardrails` |
| D-09 | Manifest coverage / unhashed donor binary (P3) | Deferred to V1.5 tooling (documented). | — |
| D-10 | Harness determinism (pet enable, close handshake) (P3) | Deferred to V1.5 tooling. | — |
| D-11 | Ledger statuses stale for 72 delivered rows (info) | Deferred (docs hygiene); cross-referenced in `06_V1_5_DEFERRED_WORK.md`. | — |

## Required workstreams

1. **Runtime trust boundary** — delivered: `02_RUNTIME_TRUST_BOUNDARY.md` (layers, per-layer block/
   advisory/trust table, native-host model, can/cannot-enforce list). Docs and UI now match it.
2. **Minimal enforcement decision** — delivered and recorded (boundary doc §3): **wired** for
   (a) tamper refusal on new work and (b) frozen/system refusal on engine-owned project writes;
   **deferred** for lease-required execution, effect-point scope checks, tool-policy denial, and
   host-level blocking — with the rationale that a partial implementation would create new false
   claims and that an OS sandbox is V2+ territory.
3. **Actor hardening** — delivered with spoof tests across `worker`/`system`/`reviewer`/`user`
   payloads and a user-only test on the engine API.
4. **Emergency-stop truthfulness** — delivered: exact scope implemented, tested against active
   lease/run, queued work, cancelled work (untouched), and through the real service; wording aligned
   in policy + UI. (Process-level kill of uncooperative children is explicitly out of scope and
   stated.)
5. **Credential truthfulness** — delivered: audited end-to-end (storage → renderer → engine →
   consumption) and documented exactly; engine-side tests cover ref-not-value storage and
   export refusal. The packaged credential probe (`packaging/verify-credentials.cjs`) is unchanged
   and remains the packaged-level check.

## Release-decision checklist (brief)

| Gate | Result |
|---|---|
| P1 contradiction between runtime and claims | Resolved: claims now match the boundary; two increments wired |
| Authorization spoofable | No: payload identity rejected at the service boundary; engine refuses non-user actors (tests) |
| Credential plaintext leaks | No change found; custody tests re-assert ref-only + export refusal |
| Docs imply nonexistent enforcement | Corrected (term sweep + pinned claims tests) |
| Patch destabilizes core flows | No: full suite green (see `05_TARGETED_TEST_RESULTS.md`); adversarial sweep clean |
| Existing release verification regresses | V1.4 frozen re-verified 3/3 untouched; V1.4.1 verified 3/3 (see `07_RELEASE_MANIFEST.md`) |
