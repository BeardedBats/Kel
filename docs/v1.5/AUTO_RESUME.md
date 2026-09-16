# AUTO_RESUME — Kel V1.5

Continuation record for the V1.5 program. Read this first when work resumes, then `00_STATUS.md`.

## Position (continuing turn 2026-09-16)

- `main` carries **`b1f9aa5`** (increment 1, G1). The **G2 completion pass** is in the working tree
  (commit follows the closure review): effect-path inventory (`02A`), side-door closures, 25/25
  charter cases, restart/resume + parallel-isolation proofs.
- Full suite **418 passed + 10 subtests** (43-test adversarial suite); zero regressions from the
  375+10 baseline.
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
| `docs/v1.5/*` | status board, authorization model, **effect-path matrix `02A`**, ledger classification, security matrix, test matrix, skeletons |

## Next steps, in order

1. (this pass) closure review recorded; commit increment 2 (`feat(v1.5): complete G2 — effect-path
   coverage, side-door closures, 25/25 charter cases`); adjust the gate board if the review says so.
2. G3 — roles / leases / boundary-expansion completion: decide where assignments come from and wire
   role attachment; native-adapter tool-class enforcement; record decisions. Leases and expansion
   are already end-to-end.
3. G4 — credentials + provider runtime: real injection (secure store → per-run env only; never
   persisted/logged/exported), leak-detection suite, provider audit (WS8), and the WSL setup
   credential propagation recorded in `02A` row 28.
4. G5–G13 per the gate board; ledger advancement waves (72 citations, 28 annotations, REQUIRED
   rows in gate order).
5. Desktop (Electron) work for G7/G8/G10: Autonomy copy correction (with the paired
   `test_v141_claims.py` update), decisions surface, Work Center rows, provider settings,
   performance surfaces.
6. Release: bump `ENGINE_VERSION` to `1.5.0` at G13; packaging hygiene (WS23); freeze via
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
