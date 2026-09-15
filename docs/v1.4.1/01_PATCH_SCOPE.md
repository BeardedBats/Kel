# 01 — V1.4.1 Patch Scope

V1.4.1 is a **small, surgical patch** issued directly after the independent post-release audit
(`docs/v1.4-postrelease/01…09`). It is not a feature release and does not pull V1.5 architecture
forward. Its governing principle: **Kel's safety claims must exactly match Kel's real execution
boundaries.**

## Disposition of the audit findings

| Finding | Disposition in V1.4.1 | Evidence |
|---|---|---|
| D-01 lease/guardrail enforcement not wired (P1) | **Partially wired + precisely bounded.** Two genuinely small, low-risk runtime increments are now real: (1) runtime tamper detection refuses new worker runs; (2) engine-owned project writes refuse frozen/system paths. Full lease-scope enforcement is explicitly deferred to V1.5 (`06_V1_5_DEFERRED_WORK.md`), and every overstated document/UI claim is corrected. | `guardrails.assert_intact` (called in `Engine.tick`); `guardrails.protected_reason` (used by `apply_changes.apply_checked`); corrected `SECURITY_MODEL`/`AUTONOMY_POLICY`/`ARCHITECTURE`/`TEAM_MODEL`; UI copy on the Autonomy page |
| D-02 native coding host runs `danger-full-access` (P1) | **Truthfully bounded (Option B).** The host is intentionally the user-authorized high-privilege runtime; narrowing it on Windows would risk the core coding flow, so the trust boundary is now stated exactly (host = full user rights inside an isolated snapshot; not contained by leases). | `SECURITY_MODEL` §6; `02_RUNTIME_TRUST_BOUNDARY.md` §4; existing tests `test_host_runtime.py` (full-access applied to thread/turn) |
| Emergency stop partial (P2) | **Implemented to scope + wording aligned.** It now revokes every active lease **and pauses all active or queued jobs** (runs marked CANCEL_REQUESTED; workers stop at their next cancellation check; pending approvals cancelled). Exact semantics in policy + UI. | `autonomy.emergency_stop`; `service` wiring to `engine.control`; UI note; tests `test_v141_boundaries.py::EmergencyStopTests`, `ActorBoundaryTests` |
| Caller-supplied actor gate (P2) | **Hardened.** Authorization identity is no longer accepted from the request payload at all: `/api/autonomy` and `/api/approval` reject any `actor` field; the service derives `user` from the authenticated local session; the engine continues to refuse any non-`user` actor. Spoof attempts are test-proven. | `service._action`; `autonomy` validation; renderer no longer sends `actor`; tests `ActorBoundaryTests`, `EmergencyStopTests::test_only_the_user_can_trigger_it` |
| Credential injection claim (P2) | **Claim corrected, implementation deferred.** Custody/rendering/metadata facts stay (they were true); the “value injected at run time” statement is replaced with the actual state and a V1.5 deferral. | `SECURITY_MODEL` §3; Providers page copy; `kelCredentials.getCredential` comment; `06_V1_5_DEFERRED_WORK.md` |
| Version labeling (P3, audit D-08) | Fixed: engine + shell version now report 1.4.1. | `service.py` `ENGINE_VERSION`; `desktop/package.json` |
| Donor identity, packaging hygiene, harness determinism, ledger hygiene (P3) | Deliberately deferred to V1.5; recorded in `06_V1_5_DEFERRED_WORK.md`. | — |

## What changed (file-level)

- **Engine:** `guardrails.py` (digest + `assert_intact` + protected-path predicates), `autonomy.py`
  (predicates reused; emergency-stop scope; message wording), `engine.py` (tamper check per tick;
  refuses new claims while tampered), `service.py` (actor rejection at the boundary; emergency-stop
  wiring; `guardrails_ok` in state; version), `apply_changes.py` (protected-path refusal).
- **Shell:** `kelApi.ts` (no `actor` in payloads), Autonomy page copy (checker status, emergency-stop
  scope, “Covered by test” column), Providers page copy (injection status), `kelCredentials.ts`
  comment, `desktop/package.json` version.
- **Docs:** corrections in `docs/v1.4/KEL_V1.4_SECURITY_MODEL.md`, `KEL_V1.4_AUTONOMY_POLICY.md`,
  `KEL_V1.4_ARCHITECTURE.md`, `KEL_V1.4_TEAM_MODEL.md`, `KEL_V1.4_TEST_MATRIX.md`, plus post-release
  notes on the historical records (`STATUS`, `RELEASE_MANIFEST`, `FEATURE_LEDGER`).
- **Tests:** `runtime/tests/test_v141_boundaries.py` (10 tests), `runtime/tests/test_v141_claims.py`
  (2 tests pinning the corrected claims).

## Explicit non-goals (not in V1.4.1)

No new orchestration systems, no personal-assistant features, no new worker types, no UI redesign, no
memory work, no agent trees, no plugin systems, and none of the 38-row V1.5 backlog. The frozen V1.4
folder (`Kel Releases/Kel-V1.4-Frozen`) is untouched; V1.4.1 freezes to its own folder.

## What did not change

The work engine's core semantics (contracts, completion authority, verification, review, durable
brokers, routing, retries, providers, memory, recipes, continuation) are untouched. The AUTO-* checker
behavior is untouched except where predicates were centralized and messages reworded.
