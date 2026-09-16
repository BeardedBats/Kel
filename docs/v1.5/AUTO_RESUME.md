# AUTO_RESUME — Kel V1.5

Continuation record for the V1.5 program. Read this first when work resumes, then `00_STATUS.md`.

## Position (turn 2026-09-16, continuing)

- Commits on `main`: `b1f9aa5` (G1), `d0c1990`, `5ed6e1d` (G2), `f12bff6` (G3), `439de12` (G4),
  `7e60203` (G5), `6a8e593` (G6). **G7** is in the working tree (commit follows).
- Gates: G0 ✓ · G1 ✓ · G2 ✓ · G3 ✓ · G4 ✓ · G5 ✓ · G6 ✓ · G7 closed (donor sunset + copy truth +
  claims re-pin) · next G8 (starts with the carried desktop `tsc` blocker).
- Full suite **438 passed + 10 subtests**; zero regressions.
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
| `runtime/kel/memory.py`, `core.py` (G6) | physical forget purge (`secure_delete`, FTS merge, WAL checkpoint) |
| `runtime/tests/test_v15_memory_packets.py` | G6 — packet lifecycle probes (4 tests) |
| `desktop/src` (G7) | donor sweep: `[AionUi]`→`[Kel]` logs ×21 files; tray, notification, app-name, `X-Title`, updater, browser copy; Autonomy copy with claims re-pin |
| `docs/v1.5/*` | status board, authorization model, **effect-path matrix `02A`**, ledger classification, security matrix, test matrix, skeletons |

## Next steps, in order

1. Commit G7; then G8 — diagnostics / performance / packaging, starting with the carried release
   blocker: baseline-and-fix the desktop `tsc --noEmit` errors (or re-scope with recorded evidence
   — never ship unexamined), add authorization/provider diagnostics surfaces, measure performance
   with a recorded basis, and complete the WS23 packaging-hygiene items. Then G9–G13.
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
- `runtime/tests/test_v141_claims.py` pins shipped UI copy; both UI pins were re-anchored in
  G4 (injection) and G7 (enforcement). Any future copy edit must update the pin in the same change.
- Keep bash tool commands under ~9 KB — longer inputs are truncated mid-file.
