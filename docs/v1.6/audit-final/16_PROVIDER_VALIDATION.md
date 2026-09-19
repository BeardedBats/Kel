# 16 — PROVIDER VALIDATION

Audit target `08f56673…`. Sources: PROVIDER_VALIDATION_MATRIX review, auditor real probes, suite re-run.

| Provider | Disposition | Evidence |
|---|---|---|
| `claude-code` (native CLI, subscription) | **REAL CALL — PASS (reproduced)** | `claude -p "Reply with exactly: ok"` → `ok`, exit 0; client `2.1.215` (`evidence/provider-claude-probe.txt`). Matches the claimed Phase-10 result. |
| `codex` (native CLI, subscription) | **ENVIRONMENT-BLOCKED — re-confirmed** | `codex exec …` → HTTP 400: "'gpt-6-astra' model requires a newer version of Codex"; client `claude`/`codex-cli 0.142.5`; exit 1 (`evidence/provider-codex-probe.txt`). Never a PASS; same limitation class as recorded (LIM-14). |
| `internal` (Anthropic API key) | **UNAVAILABLE_FOR_REAL_VALIDATION** | No credential exists on this machine (matrix + environment scan). Transport-reality recorded historically (dummy-key 401); not re-run. |
| `deepseek` (API key) | **UNAVAILABLE_FOR_REAL_VALIDATION** | No credential exists on this machine. |

- Routing semantics (AUTO/PREFERRED/FIXED, fallback-basis recording, fail-closed grants) are covered by the re-run suite (`test_workforce_assignment`, `test_v14_providers`); no provider-facing code changed in R9–R12 (reviewed).
- Provider child-env containment: see 07 (sentinel probes) — the only gap recorded is AUD-MINOR-003.
- No credentials were fabricated or read for this audit; all credential probes used synthetic sentinels.
