# V2-09 — Routing intelligence (2026-09-21)

Increment: durable routing outcomes, Automatic routing informed by measured evidence, and the
authoritative “Why this model?” answer — plus the measured phone-routing gap
(a phone turn that asked for a command and a connected service was answered conversationally).

Everything below is implemented against the systems that already existed; nothing new was invented:
the `routing_outcomes` table V1.5 writes, `kel.router.select`, `model_prefs`, the provider state row,
and the `run.claimed` event the state surface already reads.

## What changed

| Piece | Where | What it does now |
|---|---|---|
| Evidence module | `runtime/kel/routing_evidence.py` (new) | One place that reads/writes `routing_outcomes`: richer facts per run, decayed scoring, a small-sample floor, plain-words summaries. Chooses nothing. |
| Evidence columns | `kel/core.py` schema init (additive `ALTER`) | `model`, `ms`, `at`, `fallback`, `source`, `review_provider`, `review_model`, `cost`. One table — still no prompt, answer, path or credential. |
| Review writer | `core.record_review` | Writes the reviewed verdict through the evidence module (model, observed span, reviewer provenance) and sets the provider's `quality` from the **decayed, windowed** score. |
| Failure writer | `core.consume` (a failed attempt) | Records an inferred `FAILED` (`source='milestone'`) per run — failures that never reach a review are evidence too. |
| Precedence | `routing_evidence.record` | A reviewed verdict (`source='review'`) refines an inferred failure; an inferred failure never overwrites a review. One row per run (`run_id`). |
| Evidence-aware ordering | `kel/router.py::select` | Eligible models can be **demoted** by recent results — never removed, never past an explicit choice or a preference, and only when the floor was met. Explanations carry `why`, `chain`, `demoted`, `evidence`, `excluded`. Policy id: `eligible-cost-v2`. |
| Engine | `kel/engine.py` (tick) | Builds the evidence summary for the candidate list and passes it into `select`; the route (with its explanation) still rides the `run.claimed` event. |
| State surface | `kel/service.py::state` | Unchanged shape — `routes[job_id].route` now carries the explanation for free. |
| “Why this model?” | `kel/service.py::action('/api/model')` | New `action: 'why'` reads the decision back from the stored route (authoritative, not recomputed) and answers in one plain sentence. |
| Phone-routing gap | `kel/router.py::needs_work` + `service._plan` | A message that asks for a command or a connected service is a work request: it becomes a real work turn instead of the saved-context conversational answer. |
| Assignment label | `kel/assignment.py` | AUTO bindings report `eligible-cost-v2` (the ordering they actually use). |

## Rules the increment pins

- **Decay**: an outcome's weight halves every 7 days; the window is 30 days. Old failures stop
  punishing a provider (recovery is real), and a provider that failed minutes ago weighs fully.
- **Floor**: below ~3 fresh runs of decayed weight there is **no rate at all** (`verified_rate is
  None`) — small samples never overrule the safe cost/health defaults.
- **The person's ordering is not evidence**: an explicit model choice and a preference are protected
  from demotion; demotion only reorders otherwise-eligible candidates.
- **The explanation is read back**, never recomputed for display, so a surface and the engine can
  never disagree about why a model ran.

## Verification (on the final code of this increment)

Bounded groups, one stack at a time — no monolithic run:

- `tests.test_v2_routing tests.test_service_routing tests.test_model_prefs tests.test_v14_providers
  tests.test_v15_completion` → **57 OK** (includes the 13 new V2-09 tests: decay/recovery, the floor,
  review precedence, the richer row, demotion + preference/explicit protection, the explanation shape,
  and the tool-request predicate with the exact measured phone sentence).
- `tests.test_workforce_assignment` (via `discover -s tests`) → **43 OK**.
- `tests.test_v16_r8_migrations tests.test_v14_diagnostics tests.test_v14_upgrade
  tests.test_v15_reliability tests.test_v15_roles tests.test_v13_continuation_service
  tests.test_review_recovery` → **41 OK**.
- `tests.test_research tests.test_v13_work_context tests.test_acp_host` → **41 OK**;
  `tests.test_coding_boundaries tests.test_coding_recovery tests.test_coding_transport` → **22 OK**.
- Total **204 tests green** on this code.

Live probe (engine restarted on this code; `C:\Users\Nick\KelV2Runs\prepared\engine`), the exact
measured phone turn sent through `/api/send`:

```
engine pid=29140 url=http://127.0.0.1:56054
jobs before=0
tool send -> {'id': 'probe-tool-1'}
jobs after=1 new=1
  job a4241bd5-… state=RUNNING request='Use the connected GitHub service to check which account…'
  route a4241bd5-… provider=codex why='lowest cost among the models that are healthy and capable here'
        chain=['codex', 'claude'] demoted=[]
why answer -> Kel is using Codex: the lowest cost among the models that are healthy and capable here.
why payload keys -> ['chain','demoted','evidence','excluded','job','provider','selected','why']
chat send -> {'id': 'probe-chat-1'}
jobs after chat=1 (delta=0)
RESULT tool_turn_created_job=True chat_turn_created_job=False
```

So: the tool-shaped turn now creates real work with a stored, readable explanation, while an ordinary
chat turn stays conversational (no job). The probe engine was stopped afterwards; the job it created
is left in the V2 test root.
