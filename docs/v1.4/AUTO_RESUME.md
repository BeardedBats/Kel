# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~16:45 ET · Session: #6 (Gate 6 in progress; no blocker)

- **Current gate**: Gate 6 — **IN PROGRESS** (providers · credentials · autonomy). **Engine half complete.**
  Gates 0–5 are CLOSED (each with a reviewer-relay CONTINUE).
- **Done in Gate 6** (commits `7ca1feb`, `1f13a7a`; suite **346 passed + 10 subtests**):
  1. **Provider layer** (`runtime/kel/providers.py`, migration **007**): registry with class
     (`native-cli` | `api`), auth mode, base URL and per-model capabilities for `claude-code`, `codex`,
     `internal` (Anthropic API) and **`deepseek`** (`https://api.deepseek.com/v1`); the eight-state model
     (`not_installed` · `installed_not_authenticated` · `healthy` · `degraded` · `quota` ·
     **`quota_not_reported`** · `unavailable`); readiness preflight with recorded fallback reasons;
     credential **metadata only** (`provider · fields · credential_ref · timestamps` — no value column);
     `/api/providers`; 20 PROV-* tests.
  2. **Autonomy engine** (`runtime/kel/autonomy.py`, migration **008**): capability leases
     (`capability_leases` + `lease_scope` + `lease_events` + `boundary_expansion_requests`) that require a
     reviewed plan, refuse frozen/system roots, enforce scope per action kind (root/repo/domain/tool/
     external), fail closed for locked kinds (`registry` · `system` · `credential` · `github_admin`), deny
     frozen paths even inside a leased root, require a snapshot for destructive actions, deny
     expired/revoked/unknown leases, and never create approval rows for approved-plan work; boundary
     expansion with ask-once (single-use grant), project grants, deny, user-only resolution; locked-guardrail
     tamper detection (digest); emergency stop; `/api/autonomy`; 30 AUTO-* tests.
- **Remaining in Gate 6** (in order):
  1. **OS-backed credential custody through the shell**: store values in Windows DPAPI / Credential
     Manager from the Electron main process under `kel:provider:<id>:<field>`; the engine keeps metadata
     only (already enforced). Today the shell does not use `safeStorage`; replace the donor's plaintext
     provider config for Kel-owned keys and add test · store · replace · delete in Providers UI.
  2. **Providers surface** (`/providers`): one card per provider with the eight states, auth mode
     (subscription vs API key), test connection, quota/reset/`Not reported`, role model preferences,
     readiness panel with the fallback reason, usage history, DeepSeek card.
  3. **Autonomy surface** (`/autonomy`): autonomy profile, lease viewer (roots · repos · domains · tools ·
     external actions · expiry · revoke), Approval Inbox (allow once / allow for project / deny with
     reason), locked-guardrail block read-only with the “why locked” explanation, emergency stop.
  4. Wire both through `KelService.ts` allowlist; capture + probe + interaction verification; acceptance
     rows; commit/push; **Gate 6 relay**.
- **PROVEN UI VERIFICATION LOOP** (unchanged): build (`bun x electron-vite build --config
  packages/desktop/electron.vite.config.ts`) → overlay `desktop/out` into
  `dev-tools/runs/v14/shell-stage/out` → `asar-dedup-pack.js` → copy the asar into
  `dev-tools/runs/v14/candidate/resources/app.asar` (engine changes: `scripts/build-runtime.ps1` then
  replace `resources/kel-engine`) → `seed_ui_fixture.py` → capture (`capture-screens.cjs … --views`) →
  probe (`a11y-probe.cjs … --routes`) → interactions (`verify-actions.cjs`) → confirm 0 leftover
  `Kel`/`electron` processes. Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`.
  Fixture root `dev-tools/runs/v13/data/fixture-team` (seeds into the `main` conversation the shell
  renders, including a milestone completed through the engine's real verify/assess path).
- **Engine facts confirmed (Gate 6)**: `Autonomy.check(lease_id, kind, target/tool, destructive_snapshot)`
  returns `{allowed, rule, reason}` and fails closed; `resolve_expansion(..., actor='user', grant_kind='once'|'project')`;
  `Providers.readiness(capability, prefer)` returns `{chosen, chain, reasons, reason}`; provider ids are
  `claude-code`, `codex`, `internal`, `deepseek`.
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); donor sidebar label
  contrast 2.92:1 (G7); dark mode, dense states and before/after comparisons pending (G9); dev-mode
  harness launch exists but the shell's engine gate blocks dev boot — use the packaged candidate.
- **Branch / commit / remote**: `v1.4-dev` @ `1f13a7a` (+ this docs commit) · pushed to `origin`.
- **Tests**: **346 passed + 10 subtests**; renderer build green; packaged captures/probes/interactions
  green in Gate 5.
- **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree apart from untracked `Agents.md`; no running processes).
