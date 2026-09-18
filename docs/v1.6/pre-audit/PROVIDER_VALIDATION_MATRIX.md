# PROVIDER_VALIDATION_MATRIX — provider/model/runtime validation

updated: 2026-09-18T16:05Z (seed; completed in Phase 10 — sprint §36)
rule: **mock validation is never real-provider validation.** A row may only read `real: PASS`
with a recorded call artifact (timestamp, transport, result — never credentials).

Providers defined in `runtime/kel/providers.py` (`DEFINITIONS`): `claude-code` (native CLI,
subscription), `codex` (native CLI, subscription), `internal` (Anthropic API, `ANTHROPIC_API_KEY`),
`deepseek` (API, `DEEPSEEK_API_KEY`). Engine adapters: native, internal, coding, durable/research.

## Matrix

| Provider | Model | Runtime | AUTO | PREFERRED | FIXED | fallback | Capability grants | Privacy/local-only | Budget | Real call? | Mock only? | Credentials? | Result | Evidence | Known limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| internal (Anthropic API) | claude-sonnet-4-6 | engine adapter | routed via assignment tests | routed | routed | recorded-basis tests (engine) | fail-closed grants tests | privacy-enforced checks in assignment | reservations tested | **wire reached once** — packaged engine probe, HTTP 401 with dummy key (`package-p1cap`) | routing/assignment fixtures | none available in this environment (as of corpus open) | transport real, auth denied; real success NOT yet validated | ux-audit/p1-capability-engine-probe.py; 5.1 record | real-credential run pending Phase 10 |
| deepseek | deepseek-chat / deepseek-reasoner | engine adapter | same test surface | same | same | same | same | — | same | no | fixtures only | none available | untested real | — | — |
| claude-code | claude-native | native CLI | assignment-layer only | assignment-layer | assignment-layer | fallback recorded at assignment layer | native tools (text/tools/edit/shell) | subscription auth | n/a | no | fixtures only | unknown in this environment | untested real | — | Phase 10 |
| codex | codex-native | native CLI | assignment-layer only | assignment-layer | assignment-layer | same | text/tools/edit/shell | subscription auth | n/a | no | fixtures only | unknown | untested real | — | Phase 10 |

## Model routing semantics under test (engine-level, audited through 8a2b25d)

- AUTO / PREFERRED / FIXED resolution with no silent substitution; requirement profiles fail
  closed; overlays are a graceful no-op registry (Phase 5.1; audits 10–11).
- Per-mode fallback basis recorded (`fallback_basis`); cross-mode arguments refused.
- Capability grants fail closed against the authority ceiling.

## Phase 10 completion checklist

- [ ] Enumerate every provider path reachable in this environment; attempt a real call where a
      credential exists; record timestamp/result.
- [ ] Record unavailable paths as `unavailable` — never as pass.
- [ ] Confirm no credentials appear in any evidence artifact (scan).
- [ ] Re-run the model-routing fixtures at RC and attach counts.
