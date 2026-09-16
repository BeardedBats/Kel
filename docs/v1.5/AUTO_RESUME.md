# AUTO_RESUME — Kel V1.5

Continuation record for the V1.5 program. Read this first when work resumes, then `00_STATUS.md`.

## Position (turn 2026-09-16, continuing)

- Commits on `main`: `b1f9aa5` (G1), `d0c1990` (record), `5ed6e1d` (G2 complete). **G3** is in the
  working tree (commit follows).
- Gates: G0 verified · G1 ✓ · G2 ✓ · G3 closed (role snapshots + tool-class enforcement) · next G4.
- Full suite **423 passed + 10 subtests** (43-test authorization suite + 5-test roles suite); zero
  regressions.
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

1. Commit G3; then G4 — credentials + provider runtime (the largest remaining engine task): real
   injection (secure store → per-run env only; never persisted/logged/exported), leak-detection
   suite, provider audit (WS8), and the WSL setup credential propagation (`02A` row 28).
2. G5–G13 per the gate board; ledger advancement waves (72 citations, 28 annotations, REQUIRED
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
