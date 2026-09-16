# AUTO_RESUME — Kel V1.5

Continuation record for the V1.5 program. Read this first when work resumes, then `00_STATUS.md`.

## Position (turn 2026-09-16, continuing)

- Commits on `main`: `b1f9aa5` (G1), `d0c1990`, `5ed6e1d` (G2), `f12bff6` (G3), `439de12` (G4).
  **G5** is in the working tree (commit follows).
- Gates: G0 ✓ · G1 ✓ · G2 ✓ · G3 ✓ · G4 ✓ · G5 closed (claims compiler, escalation-aware routing
  records, routing/completion/review audits) · next G6.
- Full suite **434 passed + 10 subtests** (43 authorization + 5 roles + 6 credentials + 5
  completion); zero regressions.
- Frozen releases remain untouched and verify 3/3.

## What landed (files)

| File | Change |
|---|---|
| `runtime/kel/authorize.py` | **new** — central boundary: intents, outcomes, roles, lease delegation, approval, expansion, `guardrail_decisions`, `block_job`, `resume_after_grant`, `ensure_job_lease`, `role_for` |
| `runtime/kel/autonomy.py` | `consume=` on `check`; `latest_lease`; deduped `allowed`/`denied` events; `decisions` action |
| `runtime/kel/core.py` | `create` issues the execution lease for coding jobs; `revise` retires it |
| `runtime/kel/engine.py` | claim gate for coding milestones |
| `runtime/kel/coding.py` | worker effect-point check (`repo`, tools) before any dispatch |
| `runtime/kel/apply_changes.py` | `write` authorization before touching the user's project; `actor` param |
| `runtime/kel/service.py` | uniform payload-`actor` rejection; `/api/apply` as `user`; grant wakes the blocked job; autonomy shell restricted to the user-safe set; greenfield creation gated |
| `runtime/tests/test_v15_authorize.py` | **new** — 43 adversarial tests (G2 charter matrix 25/25) |
| `runtime/tests/test_v15_roles.py` | G3 — frozen role snapshots (5 tests) |
| `runtime/kel/internal.py`, `native.py`, `host_runtime.py`, `research.py` | G4 — `redact`, `child_env`, `test_command_env` |
| `runtime/tests/test_v15_credentials.py` | G4 — leak suite (6 tests) |
| `desktop/.../KelService.ts`, `.../providers/index.tsx` | G4 — spawn-time injection; corrected Providers copy (claims test re-pinned) |
| `runtime/kel/core.py` (G5) | `completion_claims` on finalized contracts; `routing_outcomes.job_kind/attempts/escalated` |
| `runtime/tests/test_v15_completion.py` | G5 — claims + escalation outcomes (5 tests) |
| `docs/v1.5/*` | status board, authorization model, **effect-path matrix `02A`**, ledger classification, security matrix, test matrix, skeletons |

## Next steps, in order

1. Commit G5; then G6 — memory and knowledge hardening (provenance, trust, correction, conflict
   resolution, freshness, scope, retract/forget, project vs global memory) and continuation
   hardening, with deterministic recipes expanded only where a known recipe exists.
2. G6–G13 per the gate board; ledger advancement waves (72 citations, 28 annotations, REQUIRED
   rows in gate order).
3. Desktop (Electron) work for G7/G8/G10: Autonomy copy correction (with the paired
   `test_v141_claims.py` update), decisions surface, Work Center rows, provider settings,
   performance surfaces.
4. Release: bump `ENGINE_VERSION` to `1.5.0` at G13; packaging hygiene (WS23); freeze via
   `scripts/freeze-release.ps1`; verify + smoke; tag; release record.

## Commands and guardrails

- Suite: `cd runtime && python -m pytest tests -q` (~83–95 s; use a **managed background job** —
  shell `&` does not survive the tool session).
- Frozen verify: `powershell -ExecutionPolicy Bypass -File scripts/verify-release.ps1 -ReleaseDir
  "<dir>" -Manifest "<dir>/SHA256Sums.txt.txt"` (expect 3/3).
- Frozen releases are immutable; never edit `docs/v1.4*` (historical record).
- `runtime/tests/test_v141_claims.py` pins V1.4.1-era phrases, including desktop copy that says the
  engine is "not yet" wired; when G7 corrects the copy, update that test in the same change.
- Keep bash tool commands under ~9 KB — longer inputs are truncated mid-file.
