# 14 — Test Matrix (Kel V1.5)

Status: **working** — maps every gate and ledger row to its tests and runtime evidence. Counts are
recorded after each increment from an actual run, never estimated.

## Authorization (G1 + G2 closure)

`runtime/tests/test_v15_authorize.py` — **43 tests** (run: 43 passed): lease lifecycle
(issue/scope/renew/revoke/expire), decision recording + dedupe, locked kinds, frozen/system paths,
destructive snapshot + approval (including cross-job approval binding), guardrail tamper, worker
identity (liveness, job/milestone binding), boundary expansion (domain/tool/repo asks, once/project
grants, denied-sticky, grant revocation, allow-once consumption), role policy (narrowing, unknown
role, fresh evaluation after edits), engine claim gate (blocked + allowed), coding adapter effect
point (revoked/expired/emergency-stop ⇒ BLOCKED, zero workspaces), application gate, greenfield
project creation (policy + service integration), autonomy shell restriction (no lease issuance),
read-only agent argv pin, internal-worker recursion denial, parallel-worker isolation,
restart/resume reauthorization, malformed contexts, denial during active work.

Full-suite counts per increment are recorded in `00_STATUS.md` (`00` carries the last verified
number; this file carries the per-suite citations).

## Roles (G3)

`runtime/tests/test_v15_roles.py` — **5 tests** (run: 5 passed): frozen snapshot attached to every
run at claim; the snapshot governs after a role edit; a strict snapshot blocks the coding
dispatcher before any workspace exists; retries reuse the same frozen assignment; text jobs attach
the documentation role.

## Credentials (G4)

`runtime/tests/test_v15_credentials.py` — **6 tests** (run: 6 passed): secret redaction for durable
text; transport errors never echo the key; the key travels only in the request header; native
children get no cross-provider key; test commands get no provider keys; a completed run leaves no
key bytes anywhere in the store.
