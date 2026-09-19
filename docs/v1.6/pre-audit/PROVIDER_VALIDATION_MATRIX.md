# PROVIDER_VALIDATION_MATRIX — provider/model/runtime validation

updated: 2026-09-18 (Phase 10 — real calls attempted; see `docs/v1.6/phase10/PROVIDER_VALIDATION.md`)
rule: **mock validation is never real-provider validation.** A row may only read `real: PASS` with
a recorded call artifact (date, transport, result — never credentials).

Providers (`runtime/kel/providers.py` DEFINITIONS): `claude-code` (native CLI, subscription),
`codex` (native CLI, subscription), `internal` (Anthropic API key), `deepseek` (API key).
Engine adapters: native, internal, coding, durable/research.

## Matrix

| Provider | Model | Runtime | AUTO | PREFERRED | FIXED | fallback | Capability grants | Privacy/local-only | Budget | Real call (2026-09-18) | Credentials | Result | Evidence | Known limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **claude-code** | claude-native | native CLI | assignment-layer fixtures | same | same | recorded-basis fixtures | fail-closed grants tests | subscription auth | n/a | **PASS** — `claude -p "Reply with exactly: ok"` returned `ok` (exit 0); client `2.1.215` | CLI installed + authenticated | **real CLI call validated** | `docs/v1.6/phase10/PROVIDER_VALIDATION.md` | app's native-adapter spawn path packaged end-to-end not separately proven |
| **codex** | codex-native | native CLI | assignment-layer fixtures | same | same | same | same | subscription auth | n/a | **FAIL (environment)** — real transport reached; service refused: `'gpt-6-astra' model requires a newer version of Codex` (HTTP 400); client `codex-cli 0.142.5` | CLI installed; auth implied by service response | **not validated (tooling limitation)** | same | upgrade or model fix needed before re-probe; never record as pass |
| **internal** (Anthropic API) | claude-sonnet-4-6 | engine adapter | routed fixtures | same | same | same | same | privacy-enforced checks | reservations tested | **Unavailable** — no credential exists on this machine (env + app store searched) | none | transport real (historical packaged probe, dummy key, HTTP 401); real success NOT validated | `PROVIDER_VALIDATION.md`; ux-audit/p1-capability-engine-probe.py | provide a key → re-run Phase 10 probe |
| **deepseek** | deepseek-chat / deepseek-reasoner | engine adapter | routed fixtures | same | same | same | same | — | same | **Unavailable** — no credential exists | none | untested real | same | provide a key → re-run |

Fixture refresh (same day): `python -m pytest tests/test_v14_providers.py tests/test_workforce_assignment.py -q` → **55 passed**.

## Model routing semantics (engine-level, audited through `8a2b25d`; unchanged since)

- AUTO / PREFERRED / FIXED resolution with no silent substitution; requirement profiles fail closed.
- Per-mode fallback basis recorded; cross-mode arguments refused.
- Capability grants fail closed against the authority ceiling.

## RC checklist (remainder)

- [x] Enumerate reachable provider paths; attempt real calls where a credential exists.
- [x] Record unavailable paths as `unavailable` — never as pass.
- [x] Confirm no credentials appear in any evidence artifact (probes printed presence only).
- [ ] Re-run the model-routing fixtures at RC and attach counts (scheduled).
- [ ] If credentials appear later: re-run the `internal`/`deepseek` probes; re-try `codex` after
      a CLI upgrade; record each result here.

## PRE-AUDIT RC update (2026-09-19)

Unchanged at RC: validation evidence stands as recorded; provider access remains the limiter
(LIM-14). No provider-facing code changed in R9–R12 (desktop presentation + supervision only);
the packaged engine boots with provider discovery unchanged (4 providers in the R8 assertion;
RC upgrade boot probed the same path).
