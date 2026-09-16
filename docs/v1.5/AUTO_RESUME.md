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
| `desktop/src` (G8) | tsc release blocker cleared — 9 files, type-only + behavior-preserving; `tests/vitest.setup.ts` + `tests/vitest.dom.setup.ts` restored (commit `6366976`) |
| `runtime/kel/diagnostics.py`, desktop diagnostics page, `kel-builder.json`, PWA assets (G8/2) | policy/lease/migration summary in the snapshot + rendered; `publish: null`, Kel copyright/linux entry, Kel manifest + SW cache (commit `9f2d890`) |
| `runtime/kel/core.py`, `service.py` (G9) | masked lock error unmasked; telemetry joined on shutdown; probes in `test_v15_reliability.py` (commit `74b6c33`) |
| `docs/v1.5/*` | status board, authorization model, **effect-path matrix `02A`**, ledger classification, security matrix, test matrix, skeletons |

## Next steps, in order

1. G10 (paused mid-prerequisites — run halted by user after the packaging attempt): staged = V1.5
   KelEngine rebuilt; `dist/package/win-unpacked` holds Kel.exe / app.asar / kel-engine /
   bundled-aioncore with **no app-update.yml**. Resume: fix the builder duplicate entry — remove
   `public` and `resources/bundled-aioncore` from `kel-builder.json` `extraResources` (base
   `electron-builder.yml` already contributes both; arrays merge, and the second copy of
   `aioncore.exe` deterministically EBUSYs) — then re-run from `desktop/`:
   `./node_modules/.bin/electron-builder --config kel-builder.json --win --dir --publish=never`
   expect EXIT 0. Then run the G10 probes with Playwright from `desktop/node_modules`:
   `node packaging/verify-packaged-ui.cjs <dist/package/win-unpacked> <fresh dataDir>` plus
   `capture-screens.cjs` and `a11y-probe.cjs` into an evidence dir; review JSONs, then G11–G13.

## Run checkpoint (paused 2026-09-15, user-requested)

- **Current gate:** G10 (visual / product acceptance). G8 and G9 are **closed** (review CONTINUE).
- **Completed:** G8 commits `6366976` + `9f2d890`; G9 commits `74b6c33` + `9cc6af7`; V1.5 KelEngine
  rebuilt (`dist/runtime/KelEngine`, PyInstaller exit 0); package staged with no app-update.yml.
- **Unfinished / uncommitted:** nothing uncommitted in source; G10 probes not run; electron-builder
  exits 1 on the duplicate `extraResources` EBUSY (staged artifact itself complete).
- **Latest passing counts:** engine 444 + 10 subtests (EXIT 0, 117.54 s; `/tmp/kel_suite_g9.txt`);
  desktop tsc 0 / vitest 72 / build 0.
- **Blocker:** duplicate packaging entry (fix + exact commands in step 1 above). No credential or
  approval blocker.
- **HEAD at pause:** `9cc6af7`; this checkpoint is the following commit. Tree clean except
  pre-existing untracked `Agents.md`; frozen releases untouched; no stray processes.
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
