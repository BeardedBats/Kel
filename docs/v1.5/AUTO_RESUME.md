# AUTO_RESUME — Kel V1.5

Continuation record for the V1.5 program. Read this first when work resumes, then `00_STATUS.md`.

## Position (end of turn 2026-09-15)

- Working tree on `main` @ `6b01e04` + the V1.5 authorization increment (see `git status`;
  commit may follow this turn's review checkpoint).
- G1 implemented; G2 increment 1 landed; full suite **398 passed + 10 subtests** (82.9 s).
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
| `runtime/kel/service.py` | uniform payload-`actor` rejection; `/api/apply` as `user`; grant wakes the blocked job |
| `runtime/tests/test_v15_authorize.py` | **new** — 23 adversarial tests |
| `docs/v1.5/*` | status board, authorization model, ledger classification, skeletons |

## Next steps, in order

1. Record the review-relay checkpoint result for this increment in `00_STATUS.md`.
2. Commit the increment (suggested: `feat(v1.5): central authorization boundary in the execution
   path` — body = files above + suite counts).
3. G2 remainder: decide and either gate or truthfully scope V14-151/152; add engine-level drills for
   revoke-mid-run → BLOCKED → blocked job, and emergency-stop → resume → reissued lease through the
   service; wire `decisions` into `/api/diagnostics` (WS22).
4. G3 remainder: role attachment (where assignments come from) + native-adapter tool-class
   enforcement; document the decision.
5. G4: credentials injection (desktop main-process `kelCredentials.getCredential` → per-run child
   env only; fake secure-store adapter for engine tests; leak-detection tests) and the provider
   runtime audit (WS8) — the largest remaining engineering chunk.
6. G5–G13 per the gate board; ledger advancement waves (72 citations, 28 annotations, REQUIRED
   rows in gate order).
7. Desktop (Electron) work is required for G7/G8/G10: Autonomy copy correction, decisions surface,
   Work Center rows, provider settings, performance surfaces.
8. Release: bump `ENGINE_VERSION` to `1.5.0` at G13; packaging hygiene (WS23); freeze via
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
