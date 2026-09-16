# 05 — Routing (Kel V1.5, G5 audit)

Status: **audited + bounded learned-record increment** — routing stays deterministic and
cost-first; learning only records inspectable outcomes. Source citations below (V1.5 G5).

## The deterministic layer (`kel/router.py`, `Engine.tick`)

Hard filters first, then cost ordering — never a generic "best model" ranking:

| Signal | Where | Behavior |
|---|---|---|
| explicit provider | `select(explicit=…)` | contract/spec choice wins or the candidate is excluded |
| installed / authenticated | candidates + probe | missing install or auth ⇒ excluded with a reason |
| capability | `required ⊆ capabilities` | `repository_edit`, `web_research`, `image`, `text` |
| quota | `provider_states.quota` | `<= 0` ⇒ excluded; unknown stays unknown |
| health circuit | `circuit_until` | open circuit ⇒ excluded (auth failures set a 24h circuit) |
| privacy scope | `local_only` | non-local candidates excluded when local is required |
| quality floor | `quality` from verified outcomes | below floor or unknown ⇒ excluded *only when a floor is requested* |
| cost | sort key after eligibility | unknown cost sorts last; tie-break: latency, then higher quota, then name |
| session continuity | `Engine._execute` | previous `native_session` per (job, milestone, provider) is reused |
| provider diversity on retry | `Engine.tick` | after 2 attempts, the same provider is excluded when alternatives exist |
| task family | `classify` + compilers | greenfield/coding/document/research classification drives contract compilation |

Empty eligibility raises `No eligible route: {reasons}` — surfaced to the user as a readable
blocking explanation, never a silent substitution.

## The bounded learned layer (`routing_outcomes`, G5 increment)

Recorded per verified/denied outcome: run, provider, verdict, **task class (`job_kind`)**,
**attempts for the milestone**, and **escalated** (a verified result whose provider differs from
the first attempt). `provider_states.quality` is computed from these outcomes (≥3 samples) and is
usable as a quality floor input.

Rules held by this increment:

- learned data **advises**; it never overrides capability/auth/quota/circuit/lease rules;
- every record is inspectable (`routing_outcomes` rows; no opaque scoring);
- unknown values stay `None`/unknown; nothing is fabricated.

## Open items (recorded, not hidden)

- `quality_by_kind` weighting (task-class-specific quality) is not yet consumed by `select`;
  today the task class is *recorded* per outcome so the signal exists when consumed.
- rate-limit observation beyond the Codex quota endpoint remains unknown (`03_PROVIDER_RUNTIME.md`).
- verification-cost modeling (routing to reduce review cost) is not implemented; recorded for the
  ledger/backlog rather than claimed.
