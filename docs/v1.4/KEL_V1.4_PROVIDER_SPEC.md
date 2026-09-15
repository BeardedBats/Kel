# KEL V1.4 — PROVIDER SPEC

Status: v1 (2026-09-15) · Gate 2 design document. Companions: `KEL_V1.4_SECURITY_MODEL.md` (§3
credentials), `KEL_V1.4_TEAM_MODEL.md` (§4 role model preferences).

## 1. Current state (verified in source)

- Adapters: `internal.py` (Anthropic key via `ANTHROPIC_API_KEY`, model from `KEL_INTERNAL_MODEL`,
  default `claude-sonnet-4-6`), `native.py`/`native_group.py` (Claude Code and Codex CLIs as bounded
  native sessions; Codex auth detected at `CODEX_HOME/auth.json`), routed through `router.py`.
- State row: `providers(id, data)` holding `failures`, `circuit_until`, `quota`, `quota_unit`,
  `quota_observed_at`, `quota_reset`, `quota_source`, `quality_samples`, `quality`, `planType`;
  updated by `telemetry.refresh_codex` (source `account/rateLimits/read`) and by
  `core.provider_outcome` / `record_review` (`routing_outcomes` feed quality).
- Secrets hygiene already exists: child environments are scrubbed of `ANTHROPIC_API_KEY` /
  `OPENAI_API_KEY` before spawning workers; the reviewer provider/model are recorded for provenance.
- Shell: donor provider configuration screens exist; **no OS-backed credential storage is used today**
  (`safeStorage` is unused) — V1.4 replaces Kel-owned secrets with the OS store (Security model §3).

## 2. Provider classes and required providers

| Provider | Class | Detection | Authentication | Required in V1.4 |
|---|---|---|---|---|
| Claude (native CLI) | native-cli | CLI present on PATH | subscription session (CLI login) | yes |
| Codex (native CLI) | native-cli | CLI present + `CODEX_HOME` | subscription session (`auth.json`) | yes |
| Anthropic API | api | n/a | API key (OS store) | yes |
| DeepSeek API | api | n/a | API key (OS store) | yes (first-class) |
| future providers | either | registry row + capability matrix | per class | architecture only |

## 3. State model (each state is distinct in the UI and the API)

| State | Signal | UI wording |
|---|---|---|
| Not installed | binary missing | `Not installed` (+ install hint) |
| Installed, not authenticated | binary present, auth probe fails/absent | `Installed · sign-in needed` |
| Authenticated | auth probe ok | `Authenticated` |
| Healthy | last outcomes ok, `circuit_until` in past | `Healthy` |
| Degraded | `circuit_until` in the future | `Temporarily unavailable until <time>` |
| Quota remaining | `quota` present (`quota_unit=percent_remaining`) | `72% left · resets 14:00` |
| Quota not reported | provider exposes none | `Not reported` (never invented) |
| Unavailable | no usable provider | `No provider available` (+ fix path) |

Auth mode is always labeled: **Subscription (CLI)** vs **API key (billed per use)** — the setup card
explains the difference before a key is entered.

## 4. Capability matrix and readiness preflight

- `provider_definitions` rows carry per-model capabilities: `text`, `vision`, `function_calling`,
  `tools`, context size (donor precedent: `desktop/…/utils/modelCapabilities.ts` and platform base
  URLs, incl. DeepSeek at `https://api.deepseek.com/v1`).
- **Preflight** (before a job runs): resolve each milestone's required capability + role preference →
  chosen (provider, model) + fallback chain; if nothing satisfies the requirement, the job waits with
  a recorded wait reason and (if needed) a boundary request — never a silent downgrade.

## 5. Fallback policy

Triggers: circuit open (repeated failure), missing auth, exhausted quota, capability mismatch.
Recorded and explained: the wait/fallback panel states *what* changed and *why* (“Fell back from
Codex to Anthropic API: Codex quota exhausted at 12:04; reset 18:00”). Exact-session status:
native sessions are reused when valid (`native_session` on `runs`); when invalid or expired, Kel uses
the bounded context packet fallback with an explicit message (existing continuation behaviour).

## 6. Credentials (design pointer)

Engine stores **metadata only** (`credential_ref`, provider, fields, updated_at; never values).
Values live in the OS-backed store via the shell, namespaced `kel:provider:<id>:<field>`, injected
only as per-run environment to the specific child process and scrubbed from grandchildren. Support:
test, store, replace, delete for Kel-owned entries; no enumeration of unrelated credentials; no
values in logs, prompts, Git, screenshots, memory, diagnostics, or receipts.

## 7. DeepSeek (first-class)

- OpenAI-compatible: base URL `https://api.deepseek.com/v1`, models `deepseek-chat` (general) and
  `deepseek-reasoner`; capability matrix: text + function calling.
- Setup card: API key entry (OS store), **Test connection** (cheap authenticated call), then state
  transitions per §3. Quota is not exposed → `Not reported`.
- Tests: request path fixture (base URL, auth header, payload shape), connection test result
  handling, fallback when unreachable, and a live-gated smoke (skipped without a key).

## 8. Usage history, budgets, and provenance

`provider_usage` appends observations (quota, latency, outcome) alongside `routing_outcomes` quality;
the Diagnostics surface charts latency and quota history. Cost/time accounting uses measured values
where the provider reports them; otherwise the UI says `Not reported`. Every run records
provider + model + session for provenance (existing B3 discipline).

## 9. Surface mapping (acceptance matrix rows)

Provider Setup cards · Test connection · installed/authenticated/health/quota/reset/unknown ·
subscription-vs-API explanation · role model preferences · fallback rules + explanation · exact
session status · task budget linkage · readiness preflight · capability matrix · usage history ·
DeepSeek card · Credential test/replace/delete (Kel-owned only).

## 10. Tests (PROV-*)

PROV-AUTH-STATES · PROV-CLI-VS-API · PROV-DEEPSEEK-PATH · PROV-DEEPSEEK-LIVE (gated) ·
PROV-READINESS · PROV-QUOTA-UNKNOWN · PROV-EXHAUSTED-FALLBACK · PROV-FALLBACK-EXPLAINED ·
PROV-NO-LEAK (no secret in logs/errors/JSON) · PROV-CRED-REPLACE-DELETE · PROV-SESSION-EXACT ·
PROV-CAPABILITY-MATRIX.
