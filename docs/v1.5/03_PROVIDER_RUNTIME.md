# 03 — Provider Runtime (Kel V1.5, G4 audit)

Status: **audited** — statements below are source-traced (V1.5 G4); "unknown" values stay unknown,
and nothing here claims an execution path that does not exist.

## Per-provider audit

| | Claude Code (native CLI) | Codex (native CLI) | Codex-code / claude-code (full agents) | Anthropic API (internal worker + research) | DeepSeek |
|---|---|---|---|---|---|
| Auth path | the CLI's own sign-in; `NativeAdapter` refuses `.cmd/.ps1` wrappers | the CLI's own login | same as native CLI, run inside Kel's gated coding flow | Kel-managed key injected at engine start (G4); header-only | stored credential metadata only |
| Session continuity | `--resume <session_id>`; id parsed from JSON result and persisted in `runs.native_session` | `resume <thread> -`; `thread_id` from `thread.started` events | native session persisted (`kel/session` → `runs.native_session`); recovery via `recover_checked_code` / `recover_pending_checks` | stateless per request; bounded loop keeps its own messages | n/a |
| Capability support | `['text','native_session']` — tools disabled by argv | same | `repository_edit`, `native_session` (+`approval_stream`) | `text`, `image`; research adds `web_research` | registry/readiness only |
| Model selection | CLI default | CLI config (`model_reasoning_effort=\"low\"` pinned for read-only) | engine route (explicit contract/model preference) | `KEL_INTERNAL_MODEL` or default; per-job `options.model` recorded | registry entry lists models for display |
| Health | probe `--version` (installed/version) | probe + quota observation | probe via CLI presence; failures feed `provider_states` | failures feed `provider_states` (circuit on 401/403/auth) | readiness surface |
| Rate limits | not observed (unknown) | not observed beyond quota windows (unknown stays unknown) | same as CLIs | provider-side; surfaced as failures if hit | unknown |
| Quota state | unknown (`quota=None`) | `account/rateLimits/read` → percent remaining, reset, source recorded; unavailable ⇒ unknown | same as Codex | unknown | unknown |
| Failure handling | non-zero exit ⇒ FAILED with bounded stderr pointer; output cap 4 MB | parse errors/events ⇒ FAILED; malformed JSON tolerated line-wise | uncertain outcomes fenced (`fence_uncertain_code`), never retried blindly | bounded loop returns FAILED with **redacted** error | n/a |
| Retry | engine attempts (≤4 per milestone) via routing | same | same; isolated-copy failures may safely retry without replaying user effects | same | n/a |
| Failover | engine route: after 2 attempts the same provider is excluded when alternatives exist; circuit/quality/cost signals | same | same | same | n/a |
| Cancellation | process kill on cancel; `CANCEL_REQUESTED` acknowledgment | same | broker monitor + typed stop receipts; no unconfirmed writer replay | cancel checked between iterations | n/a |
| Credential source | CLI login (Kel does not copy keys into it — `child_env` strips the other provider's key) | CLI login (Kel-managed Anthropic key stripped from codex children) | CLI login; WSL isolated runtime has its own in-distro auth | Kel-managed key (G4, `04_CREDENTIAL_RUNTIME.md`) | stored metadata; **no live execution path yet** |
| Context handoff | prompt + saved handoff packet (context, not permissions) | same | contract objective + tests + workspace context | prompt + attachment snapshots | n/a |

## Truthful gaps recorded by this audit

- **DeepSeek**: registered with model metadata and a readiness surface, but no engine call path and
  no credential consumption yet; do not surface it as usable for execution until a path exists.
- **Explicit "Test connection" action (V14-122)**: readiness probes exist (installed, version,
  capability); a user-triggered connection test remains open — queued with the provider surfaces
  work (G7/G8), not silently claimed here.
- **Rate-limit observation** exists only where the Codex quota endpoint reports it; everything else
  is recorded as unknown, never fabricated.
- **Subscription-vs-API explainer copy (V14-120)** remains open (G7 settings copy).
- WSL in-distro provider auth (`runtime_setup.py` root-only `auth.json` copy) is out of the host
  env path; re-checked at G8/G9 per `02A` row 28.
