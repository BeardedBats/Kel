# Phase 10 — Real provider validation

date: 2026-09-18
increment: PHASE10-PROVIDER-VALIDATION
scope (sprint §36): validate every provider path current access allows; real calls where possible;
record unavailable paths accurately; never leak credentials into evidence.

## What was validated (real, this session)

| Path | Probe | Result |
|---|---|---|
| `claude-code` (native CLI) | `claude --version` → `2.1.215 (Claude Code)`; minimal real call `claude -p "Reply with exactly: ok"` (neutral cwd) | **PASS — returned `ok` (exit 0).** Client installed and authenticated. |
| `codex` (native CLI) | `codex --version` → `codex-cli 0.142.5`; minimal real call `codex exec --skip-git-repo-check "Reply with exactly: ok"` | **Real transport reached; run refused by the service:** `The 'gpt-6-astra' model requires a newer version of Codex. Please upgrade…` (HTTP 400). Environment/tooling limitation of the installed CLI, recorded as such — NOT validated real success. |
| `internal` (Anthropic API key) | environment (`ANTHROPIC_API_KEY`), app credential store search (`kel-credentials.json` across the user profile) | **Unavailable — no credential exists on this machine.** (Historical: a packaged engine probe reached the real wire once with a dummy key and got HTTP 401 — unchanged.) |
| `deepseek` (API key) | environment (`DEEPSEEK_API_KEY`) | **Unavailable — no credential exists on this machine.** |

Engine-level routing/authorization fixtures re-run for freshness:
`python -m pytest tests/test_v14_providers.py tests/test_workforce_assignment.py -q` → **55 passed**
(model prefs, provider registry, assignment/fallback paths — fixture-level, not real calls).

## Honest bounds (never blurred)

- `claude` PASS validates the *installed CLI* (availability + auth + a real request round-trip).
  The app's native-adapter **spawn path** packaged end-to-end is NOT proven by this probe; it
  remains covered by fixture tests + the historical packaged engine probe (401 dummy-key wire
  reach). Campaign B should re-run whatever the RC package allows.
- `codex` is present and reachable but refused by model-version logic — recorded as an environment
  limitation, never as a pass.
- No credential values were read, printed, or stored anywhere in this record. Probes used only
  presence checks and the CLIs' own configured auth (which is the user's, not exported).

## Matrix updated

`docs/v1.6/pre-audit/PROVIDER_VALIDATION_MATRIX.md` — rows rewritten with today's results; no row
claims more than its probe proved.
