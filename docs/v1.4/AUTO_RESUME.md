# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~17:35 ET · Session: #6 (Gate 6 one item from closing; no blocker)

- **Current gate**: Gate 6 — **IN PROGRESS**, one item left: **OS-backed credential custody through the
  shell**. Gates 0–5 are CLOSED (relay CONTINUE each).
- **Done in Gate 6** (commits `7ca1feb`, `1f13a7a`, `966016a`; suite **346 passed + 10 subtests**):
  - **Providers engine** (migration 007): registry + capability matrix, eight-state model (incl.
    `quota_not_reported`), readiness preflight with recorded fallback reasons, credential **metadata only**,
    `/api/providers`, 20 PROV-* tests.
  - **Autonomy engine** (migration 008): capability leases (scope per kind; reviewed plan required; frozen
    and system roots refused), locked-kind enforcement, frozen-path denial, destructive snapshot rule,
    expiry/revocation denials, boundary expansion (ask once / project / deny, user-only), locked-guardrail
    tamper detection, emergency stop, `/api/autonomy`, 30 AUTO-* tests.
  - **UI**: `/providers` (cards with real states, models + capabilities, readiness panel, credential
    metadata) and `/autonomy` (leases with scope + revoke, boundary requests with the recorded
    why/benefit/fallback/risk and the three decisions, locked guardrail block, scope probe) — rendered from
    the packaged candidate: tags `g6`/`g6b`, 27 shots each, **0 renderer errors, 0 blank, app exit 0**,
    route contrast failures **0/0**. Sider entries + routes added; `/api/providers` + `/api/autonomy`
    allowlisted.
- **Process lesson (important)**: after any **engine** change, rebuild and replace the candidate engine
  before capturing: `powershell -ExecutionPolicy Bypass -File scripts/build-runtime.ps1` →
  `python packaging/verify_engine_pyz.py dist/runtime/KelEngine/KelEngine.exe` (expect `RESULT: OK`) →
  `rm -rf dev-tools/runs/v14/candidate/resources/kel-engine && cp -r dist/runtime/KelEngine
  dev-tools/runs/v14/candidate/resources/kel-engine`. Renderer-only changes need steps 1–4 of the loop below.
- **Exact next action** (last Gate 6 item):
  1. **OS-backed credential custody**: in the Electron **main** process, use `safeStorage`
     (DPAPI on Windows) to store provider values under `kel:provider:<id>:<field>`; the engine keeps
     `credential_ref` metadata only (already enforced). Add `test · store · replace · delete` for
     Kel-owned entries, and never expose values to the renderer, logs, diagnostics, Git or screenshots
     (the shell currently uses **no** `safeStorage` at all — `grep -rn safeStorage desktop/...` is empty).
     Suggested shape: a `kel:credential` IPC channel in `KelService.ts` + preload exposure
     (`setCredential(provider, field, value)` / `deleteCredential(provider)` / `hasCredential(provider)`),
     with the value never returned to the renderer; Providers UI then offers a real “Store API key” flow.
  2. Tests/evidence: a `verify-actions.cjs` step that stores a dummy value, asserts the engine's
     metadata row appears and no value is retrievable, then deletes it; capture the Providers surface
     again; commit + push; **Gate 6 reviewer relay**; close the gate and update the ledger.
- **PROVEN UI VERIFICATION LOOP**: build (`bun x electron-vite build --config
  packages/desktop/electron.vite.config.ts`) → overlay `desktop/out` into
  `dev-tools/runs/v14/shell-stage/out` → `asar-dedup-pack.js` → copy the asar into
  `dev-tools/runs/v14/candidate/resources/app.asar` → (engine changes: see the process lesson above) →
  `seed_ui_fixture.py` → capture (`capture-screens.cjs … --views`) → probe (`a11y-probe.cjs … --routes`) →
  interactions (`verify-actions.cjs`) → confirm 0 leftover `Kel`/`electron` processes.
  Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`. Fixture root
  `dev-tools/runs/v13/data/fixture-team` (seeds into `main`; includes a verified milestone and an active
  lease + pending boundary request).
- **Engine facts**: `Providers.readiness(capability, prefer)`; provider ids `claude-code`, `codex`,
  `internal`, `deepseek`; `Autonomy.check(lease_id, kind, target|tool, destructive_snapshot)` returns
  `{allowed, rule, reason}`; `Autonomy.resolve_expansion(request_id, allow, actor='user', grant_kind)`.
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); donor sidebar label
  contrast 2.92:1 (G7); dark mode, dense states and before/after comparisons pending (G9); dev-mode
  harness launch exists but the shell's engine gate blocks dev boot — use the packaged candidate.
- **Branch / commit / remote**: `v1.4-dev` @ `966016a` (+ this docs commit) · pushed to `origin`.
- **Tests**: **346 passed + 10 subtests** (engine); renderer build green; packaged captures/probes green.
- **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree apart from untracked `Agents.md`; no running processes).
