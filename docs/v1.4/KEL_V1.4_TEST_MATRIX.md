# KEL V1.4 — TEST MATRIX

Status: v0.1 (Gate 0). Planned structure + verified baseline. Fills per gate; no existing test may be deleted or weakened.

## 0. Method and levels (inherited from V1.3, extended)

- **U** unit — pytest, hermetic, fakes, temp dirs.
- **I** integration — real SQLite store on disk, fake providers, real engine tick loop.
- **L** live — real engine process, throwaway data dirs.
- **P** packaged — real `Kel.exe` / `KelEngine.exe`, Playwright, isolated data root.
- **V** visual — packaged screenshots, keyboard, resizing, accessibility checks.

Retention rule: the engine suite must stay ≥ **267 passed + 10 subtests** at every gate. Deletions/weakenings are prohibited; new tests are additive.

## 1. Verified baseline (this session)

| Suite | Command | Result |
|---|---|---|
| Full engine suite | `cd runtime && python -m pytest tests/ -q` | **267 passed + 10 subtests** (55.58s, exit 0) |

## 2. Planned suites (IDs map to the feature ledger `V14-###`)

| Area | ID prefix | Level focus | Status |
|---|---|---|---|
| Solution quality (V14-001…018) | SLN | U/I + reviewer relay | planned |
| Team / Office / Roster / Studio (019…040) | TEAM | I + L | planned |
| Work Center (041…062) | WORK | I/L/P | planned |
| Memory / context (063…082) | MEM | U/I (extend V1.3 MEM-*) | planned |
| Continuation (083…096) | CONT | I/L (extend V1.3 CONT-*) | planned |
| Verification / trust (097…118) | VER | U/I | planned |
| Providers / credentials (119…136) | PROV | U/I + secret scans | planned |
| Autonomy / guardrails (137…153) | AUTO | U/I adversarial — blocked actions must fail closed | planned |
| Recipes (154…166) | REC | I/L (extend V1.3 recipes) | planned |
| Desktop (167…183) | DESK | P/V + keyboard/a11y | planned |
| Diagnostics (184…200) | DIAG | U/I + sanitization checks | planned |

## 3. New-test requirements (from the brief, instantiated per gate)

- Role versioning/rollback/overrides, assignment snapshots, locked-guardrail isolation, no self-certification, no recursive delegation (G3).
- Credential isolation; no secret logging or unrelated enumeration; provider auth-state distinctions; DeepSeek request path; quota-unknown; exhausted fallback (G6).
- Blocked-by-default checks: Registry writes, screen takeover, synthetic input, non-Firefox general browsing, unrelated personal paths, frozen-release writes, GitHub admin actions, force-push main. Allowed: reviewed-plan edit/test/install/commit/push (G6).
- Packaged: boot, V1.3-data migration, zero orphans after shutdown, relaunch, full visual suite (G10).

## 4. Gate 0 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G0-REF | refs/tag/frozen-hash verification | U (to be scripted) | **PASS** (session 1; manual) |
| G0-SUITE | baseline suite green (267 + 10) | U | **PASS** (session 1) |
| G0-HARNESS | packaged screenshot harness (isolated, offscreen, bounded shutdown) | P | **PASS** (`packaging/capture-screens.cjs`) |
| G0-CAPTURES | baseline captures (2 states × 30 views, 5 widths, 0 errors) | P/V | **PASS** (`docs/v1.4/screenshots/baseline/`) |
| G0-FIXTURE | fixture generator for populated states (jobs/approval/memory) | I | **PASS** (`runtime/tools/seed_ui_fixture.py`) |
| G0-PERF | startup/performance baseline | L | pending (G8 tooling) |

## 5. Gate 1 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G1-DIRECTIONS | two materially different directions rendered + audited (contrast, type, emoji, focusables) | V | **PASS** (`packaging/render-directions.cjs`, `screenshots/directions/`) |
| G1-FOCUS | every tab stop shows a focus ring; first stop = skip link | V | **PASS** (0 failures, both directions) |
| G1-A11Y-BASE | packaged V1.3 a11y probe (contrast/focus/type/tab order) | P/V | **PASS** (findings: `KEL_V1.4_UI_AUDIT.md` §5) |
| G1-DOCS | design system + interaction patterns + accessibility standard + visual acceptance matrix | docs | **PASS** (4 documents) |

## 6. Gate 2 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G2-ARCH | architecture + 5 Best Solution Gate decisions grounded in source | docs | **PASS** (`KEL_V1.4_ARCHITECTURE.md`) |
| G2-TEAM | Team model incl. activity contract + no-fake-specialist enforcement | docs | **PASS** (`KEL_V1.4_TEAM_MODEL.md`) |
| G2-AUTONOMY | lease + guardrail enforcement mapped to AUTO-* tests | docs | **PASS** (`KEL_V1.4_AUTONOMY_POLICY.md`) |
| G2-PROVIDERS | state model + DeepSeek first-class + credential custody | docs | **PASS** (`KEL_V1.4_PROVIDER_SPEC.md`) |
| G2-UX | IA + surface specs + old-surface migration + screenshot strategy | docs | **PASS** (`KEL_V1.4_UX_SPEC.md`) |
| G2-SECURITY | threat model + sanitizer + retention + supply chain | docs | **PASS** (`KEL_V1.4_SECURITY_MODEL.md`) |

## 7. Gate 3 additions

| Id | Check | Level | Status |
|---|---|---|---|
| G3-SUITE | full engine suite after V1.4 modules | U/I | **PASS** (296 passed + 10 subtests; retention rule ≥267 + 10 held) |
| G3-SLN | brief/options/comparison/search/opportunity/idea/recommend/review/approve gate | U | **PASS** (12 tests, `tests/test_v14_solution.py`) |
| G3-TEAM | role versioning · rollback · project/task override precedence · locked-section isolation · assignment snapshot immutability · tool policy fails closed · no recursive delegation · activity contract (no hidden reasoning) · staffing reasons · seed idempotency | U/I | **PASS** (17 tests, `tests/test_v14_team.py`) |
| G3-MIGRATION | migrations 005/006 additive, recorded in `schema_migrations`, idempotent | I | **PASS** |
| G3-API | `/api/brief` + `/api/team` wired in `service._action` | I | **PASS** (service envelope test) |

## 8. Gate 4 additions (in progress)

| Id | Check | Level | Status |
|---|---|---|---|
| G4-BUILD | desktop dependencies + renderer build on this machine | I | **PASS** (`bun install --frozen-lockfile` 1591 pkgs; `bun x electron-vite build` exit 0 → `desktop/out/{main,preload,renderer}`) |
| G4-ALLOWLIST | `/api/brief` + `/api/team` reachable from the renderer | I | **PASS** (`KelService.ts` route allowlist) |
| G4-FIXTURES | team/solution fixtures seed an isolated data root | I | **PASS** (`data/fixture-team`: 9 roles, 2 assignments, activity + artifact, APPROVED brief) |
| G4-UI | Office / Roster / Studio + Work Center surfaces implemented, routed, and compiling into the renderer bundle | I/V | **PASS (code)** — `030cb61`; rendered capture verification pending |
| G4-CAPTURE | five-width captures of the new surfaces + comparisons | V | pending |
