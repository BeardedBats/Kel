# KEL V1.4 — AUTO-RESUME

Updated: 2026-09-15 ~16:20 ET · Session: #6 (Gate 6 in progress; no blocker)

- **Current gate**: Gate 6 — **IN PROGRESS** (providers · credentials · autonomy).
  Gates 0–5 are CLOSED (each with a reviewer-relay CONTINUE).
- **Done in Gate 6 so far** (committed `7ca1feb`):
  1. `runtime/kel/providers.py` (migration **007**: `provider_credentials`, `provider_usage`) with
     provider **definitions** (class `native-cli` | `api`, auth mode, base URL, per-model capabilities)
     for `claude-code`, `codex`, `internal` (Anthropic API) and **`deepseek`**
     (`https://api.deepseek.com/v1`, `deepseek-chat` / `deepseek-reasoner`).
  2. The **state model**: `not_installed` · `installed_not_authenticated` · `healthy` · `degraded`
     (`circuit_until`) · `quota` · **`quota_not_reported`** · `unavailable`, with CLI detection via PATH +
     auth file (`CODEX_HOME/auth.json`) and API detection via credential metadata (env or stored ref).
  3. **Readiness preflight** (`readiness(capability, prefer)`): honours the preferred provider, records
     the fallback reason (“Fell back to …”) plus every unusable provider's reason, and returns a clean
     no-provider result when nothing is usable.
  4. **Credential metadata only** — the engine stores `provider · fields · credential_ref · timestamps`
     and never a value (`set_credential_metadata` refuses an empty reference); set/delete are observed.
  5. `/api/providers` service envelope (`list`, `status`, `readiness`, `credentials`, `set_credential`,
     `delete_credential`, `usage`).
  6. **20 new PROV-* tests**; full suite **316 passed + 10 subtests** (0 failures).
- **Remaining in Gate 6** (in order):
  1. **OS-backed credential custody**: store values through the shell main process (Windows DPAPI /
     Credential Manager) under `kel:provider:<id>:<field>`; the engine keeps metadata only. Replaces the
     donor's plaintext provider config for Kel-owned keys; test · store · replace · delete; never into
     logs/prompts/Git/screenshots/memory/diagnostics. The shell currently does **not** use `safeStorage`.
  2. **Autonomy engine**: `capability_leases` (+ roots/repos/domains/tools/external actions +
     `lease_events`), boundary-expansion requests (allow once / allow for project / deny with reason),
     and guardrail enforcement points; publish `kel/guardrails.py` `locked_block()` to the UI.
  3. **AUTO-* test set** from `KEL_V1.4_AUTONOMY_POLICY.md` §8: AUTO-ROOT · AUTO-REPO · AUTO-BROWSER ·
     AUTO-BLOCK-REG · AUTO-BLOCK-SYSTEM · AUTO-FROZEN · AUTO-GH-ADMIN · AUTO-GH-ALLOW · AUTO-DESTRUCT ·
     AUTO-CRED · AUTO-PRIVATE · AUTO-LEASE-EXPIRY · AUTO-ASK-ONCE · AUTO-GUARDRAIL-IMMUTABLE ·
     AUTO-EMERGENCY-STOP · AUTO-NO-PROMPT-AFTER-REVIEW.
  4. **Providers + Autonomy surfaces** (`/providers`, `/autonomy`) on the Desk tokens: provider cards
     with the eight states, test connection, role preferences, usage history; lease viewer with revoke,
     Approval Inbox (allow once / allow for project / deny), locked-guardrail block read-only.
  5. Captures + probe + interaction verification; acceptance rows; commit/push; **Gate 6 relay**.
- **PROVEN UI VERIFICATION LOOP** (unchanged): build (`bun x electron-vite build --config
  packages/desktop/electron.vite.config.ts`) → overlay `desktop/out` into
  `dev-tools/runs/v14/shell-stage/out` → `asar-dedup-pack.js` → copy the asar into
  `dev-tools/runs/v14/candidate/resources/app.asar` (engine changes: rebuild with
  `scripts/build-runtime.ps1` and replace `resources/kel-engine`) → `seed_ui_fixture.py` → capture
  (`capture-screens.cjs … --views "id:/hash,…"`) → probe (`a11y-probe.cjs … --routes …`) → interactions
  (`verify-actions.cjs`) → confirm 0 leftover `Kel`/`electron` processes.
  Env: `PLAYWRIGHT_MODULE=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/node_modules/playwright`,
  `PLAYWRIGHT_BROWSERS_PATH=C:/Users/Nick/Desktop/Kel/dev-tools/playwright/browsers`.
  Fixture root: `dev-tools/runs/v13/data/fixture-team` (seeds into the `main` conversation the shell
  renders, including a milestone completed through the engine's real verify/assess path).
- **Known notes (carried)**: engine shutdown needs the bounded kill (G7/G10); donor sidebar label
  contrast 2.92:1 (G7); dark mode, dense states and before/after comparisons pending (G9); dev-mode
  harness launch exists but the shell's engine gate blocks dev boot — use the packaged candidate.
- **Branch / commit / remote**: `v1.4-dev` @ `7ca1feb` (+ this docs commit) · pushed to `origin`.
- **Tests**: **316 passed + 10 subtests** (engine); renderer build green; packaged captures/probes/
  interactions green in Gate 5 (Gate 6 UI not yet rendered).
- **Tests failing**: none. **Blocker**: none. **HARD STOP: no.**
- **Frozen-hash state**: 3/3 verified; `Kel Releases/` untouched. **Dogfood isolation**: intact.
- **Continuation safety**: safe (clean tree apart from untracked `Agents.md`; no running processes).
