# D-66/D-67 implementation design — the workforce, live in everyday work

Status: approved for implementation 2026-09-27 (decisions D-53, D-55, D-64, D-65, D-66, D-67 by Nick;
open questions settled below under handoff §36 "conservative inference" and listed under **Needs
Nick**). Inputs read: handoff §§1, 13–17; intent document (2026-09-27) §§6, 9, 10, 13; the Workforce
OS research (`workforce-os/00, 05, 06, 08, 10, 14, 15`) and role charters (`00, 04, 05, 13`) from the
recovery archive; `docs/v1.6/phase5/*`, the Phase 8 worker-view decision, `docs/v2/evidence/v2-12`,
`KNOWN_LIMITATIONS` V2-11..13.

## What is true before this change (measured)
- `workforce.enabled` (`KEL_WORKFORCE`) defaults **off**; `delegation.delegate`, `pods.run_d2` and
  `parallel.run_parallel` are called only by `kel/evaluation.py` and tests.
- Everyday work: `Service._plan` → `_handoff` (D-53) → `_start_work` → `_compile_work` (coding:
  `compile_coding`; research: `compile_research`; writing: `Commander.plan`) → `Engine.submit` →
  `Engine.tick` claims each READY milestone on the cheapest healthy adapter (soft preference: the saved
  chat model), runs it in a durable broker, `Store.verify` runs the built-in checks, and the engine's
  reviewer (`Commander.review`, health → different family → different provider) judges the rubric.
  Coding verdicts add repository evidence; D-65 `auto_apply.settle` applies a VERIFIED change.
- There is no staffing record, no role→model setting, no reasoning level anywhere, no Oracle, and the
  coding runtimes hard-code their model (`host_claude.mjs`: `claude-sonnet-4-6`; Codex: the CLI's
  default model at effort `low`).
- The engine already runs independent milestones of one job at the same time (global cap: two runs).

## Principle
One workflow engine, one task database, one coding bridge (handoff §13, §17). Staffing is a
**recorded decision on the job's own contract** plus **bindings on the job's own runs**; review is the
engine's existing reviewer; the Oracle is one more read-only review on the same review pool;
parallel streams are the job's own independent milestones. Nothing here spawns a loop outside the
engine, and nothing Nick sees requires managing an agent (D-66).

## 1. Staffing on the everyday path
**Where.** `Service._start_work` (every D-53 hand-off), `Service._recipe_run` and scheduled runs call
`staff.plan_job(store, contract, request, conversation)` after the contract compiles and before
`Engine.submit`. The result is frozen into the contract as `contract['staffing']` — it is digested
and versioned with the contract, so a restart can never re-decide it. Right after the job exists, one
`staffing.decided` team event (job-scoped) records the same decision (V2-12 history reads it).

**Decision.** `staff.features_for(contract, request)` computes the doc-05 feature vector
deterministically from the compiled contract and the request text (kind, milestone count and
dependencies, request length, scope words — security/credentials/permissions → `security_boundary`;
deploy/release/publish → `release`; delete/send/pay/publish externally → `irreversible`;
migration/schema/database/delete data → `data_migration`; install/add a dependency →
`new_dependency`; UI/screen/design/layout → user-facing). A positive scope signal is never negated
(doc 05 §2). `staffing.resolve` then decides the tier with R1–R10, `tier_max` and the one-step V2-12
history advice. Kel's own application rules (recorded as reasons):

| Tier (internal) | What runs | Who is on it |
|---|---|---|
| D0 — Kel alone | Kel's own model does the work | Kel; a Verifier judges any rubric (never self-certified) |
| D1 — one specialist | one role instance per step, **one at a time** | Builder / Discovery / Designer / Utility; Verifier check |
| D2 — pod | as D1, and the Verifier reviews through lenses; findings go to the assurance ledger and a live blocker/critical holds the step | specialist + Verifier (lens review) |
| D3 — parallel | 2–3 genuinely independent steps run at the same time, each owned by its own instance; Kel combines | several specialists + Verifier |
| D4 | runs as a D2/D3 pod with the security lens and a mandatory Oracle | + Oracle |

- **Coding** is never below D1 (a Builder always writes code) and never D3: the coding bridge keeps
  one project copy per job (`code_workspaces` is keyed by job), so parallel code streams are not
  available; a D3 decision for code is capped at D2 with that reason.
- **D3 only where the plan is genuinely parallel.** A writing/research plan with 2–3 independent
  parts (no `depends_on`, distinct outputs, one combine step) is validated through
  `parallel.plan_streams` (2..3 streams, unique names, pairwise-disjoint write paths = each part's own
  output file, an explicit merge strategy — R9's decomposition statement is recorded). Exclusive
  write ownership is structural: each part writes only its own artifact file, and the store allows one
  live run per step. A D2 decision whose plan has that shape runs its parts in parallel (doc 05 E4:
  decomposability ≥ 2, sequentiality ≤ 1); anything else runs **one step at a time** — the engine
  does not start a second step of a staffed job below D3. R8 caps are recorded; the engine's own cap
  (two concurrent runs) is lower.
- **Roles per step.** coding → Builder; web research → Discovery; design/UI writing → Designer;
  short mechanical work (format, convert, rename, translate, tidy) → Utility; other writing at D1+ →
  Builder (charter: "produces the implementation or artifact"); D0 writing and the combine step of a
  parallel plan → Kel. Roles are spawned per step; the same role can have several live instances.
- **Off-switch.** `KEL_WORKFORCE=0|false|off|no` (env) turns all of this off: jobs are created exactly
  as before (no `staffing` key) and every path below takes today's branch. Default is **on**.

## 2. Role → model resolution (D-67)
`kel/staff.py` owns the role table (`role_models`, one row per role Nick changed; absent rows use the
D-67 defaults) and the model catalog. Modes: **Fixed** (exactly this model or wait with a plain
reason), **Preferred** (this model when available, else fall back and say so), **Automatic** (today's
routing).

| Role | Default (Preferred) | Runtime used | Reasoning |
|---|---|---|---|
| Kel (Commander) | ChatGPT Luna (`gpt-6-luna`) | Codex CLI | Auto |
| Discovery | Claude Sonnet | Claude Code (`--model sonnet`) / Anthropic API for web research | Auto |
| Designer | Claude Fable 5.1 (`claude-fable-5-1`, CLI fallback `fable`) | Claude Code | Auto |
| Builder | Claude Opus 5.5 (`claude-opus-5-5`, CLI fallback `opus`), then Codex | Claude Code / Codex | Auto |
| Verifier | GPT-6 Astra (`gpt-6-astra`) | Codex CLI (read-only, tools off) | Auto |
| Oracle | GPT-6 Astra | Codex CLI (read-only, tools off) | Auto |
| Utility | DeepSeek Flash | none installed (no DeepSeek adapter) → falls back, recorded | Auto |
| Architect, Sentinel, Release | Automatic | today's routing | Auto |

**Precedence** (most specific first): a scheduled run's model (D-57) → the model Nick picked for this
chat (CH-2; an explicit instruction for that chat's work) → the role setting → Automatic routing (the
default chat model stays a soft preference, as today). Kel's own replies and plans use the chat model
when one is saved, else the Kel role.

**Reasoning levels are real flags, verified on the installed CLIs (not guessed):** Claude Code 2.1.215
`--effort low|medium|high|xhigh|max` (+ `--model`, `--fallback-model`); Codex 0.142.5 app-server
`turn/start {model, effort}` and `thread/start {model}` (response reports `model` and
`reasoningEffort`), `codex exec -m <model> -c model_reasoning_effort="<level>"`; each Codex model's
supported levels come from its catalog (`~/.codex/models_cache.json`: `gpt-6-astra` low…ultra,
`gpt-6-luna` low…max). The Anthropic API worker has no reasoning setting here (recorded as "not
adjustable"). **Auto** = Kel does not override the model's own default level; the only exception is
the quick reply-or-work decision of a chat turn, which keeps `low` (30-second budget) and records it.

**Independence.** Verifier and Oracle must be a different model family from the step's Builder when
one is available (`anthropic` ≠ `openai` ≠ `deepseek`). If the preferred Verifier shares the Builder's
family (e.g. the Builder fell back to Codex), Kel picks the first available model of another family
and records why; if none exists the review runs with `independence: reduced` recorded (never hidden).
A Fixed Verifier/Oracle is honoured and its reduced independence recorded.

**Truth recording.** Every model call made for a staffed job is one `staff_calls` row:
`asked` (role, mode, model, reasoning), `ran` (runtime, provider/adapter, model, reasoning,
runtime version) and `why` (fallback reason, if any). `ran.model` is written **only** from what the
runtime reported (Claude Code's `init` event / `modelUsage`; Codex `thread/start` response; a
successful `codex exec -m X`), and `model_confirmed` stays false until then — the live view never
shows a model that did not run. A model the runtime rejects is remembered for 24 h
(`staff_model_status`) so the next step falls back instead of failing again.

**Settings API** (engine, through the existing allowlisted `/api/model`): `{action:'roles'}` → every
role row `{role,label,mode,model,model_label,reasoning,reasoning_options,available,note,default}` plus
the choosable models; `{action:'set_role', role, mode, model?, reasoning?}`; `{action:'reset_role',
role}`. The renderer's Settings row is out of scope for this increment (data only).

## 3. Review and the Oracle
**Verifier.** Staffed jobs keep the engine's review path (`_schedule_review` → `Commander.review`).
The Commander resolves the Verifier binding (above) and runs a fresh-context, read-only review. At D2+
the prompt asks for lens findings (`functional-testing`, `maintainability` for code;
`requirements-coverage` for writing/research; `security` when the security flag fired;
`data-integrity` for migrations). Findings are recorded through `assurance.record_finding`
(mission = job, task = `pod:<job>:<step>`, artifact = the reviewed digest). **A VERIFIED verdict over
a live blocker/critical finding is recorded as FAILED** (never a clean pass over open blockers), so
the step goes back to the Builder with the findings — the engine's existing repair loop. Findings on a
superseded artifact are closed `fixed` against the re-review's evidence row.

**Oracle trigger** (recorded with its reasons): a staffed job reaches CLOSED/VERIFIED and any of —
tier D4; tier ≥ D2 with a security, irreversible, release or data-migration flag; or a verified code
change Kel would auto-apply (Full access) that touches more than 10 files or 400 changed lines.
**Hook:** in `Engine.tick`, before D-65 `settle`/`publish`, a triggered job waits for its Oracle; the
Oracle runs on the engine's review pool (one at a time, never inside the tick lock) through
`assurance.oracle_check`: fresh context, read-only, tools off, outside the reporting line (it sees the
request, the claims, the checks and the artifact/diff — never the team's narrative or earlier
findings), family-diverse from the Builder. Its challenges become `adversarial` findings
(`oracle:<job>`). **A live blocker stops auto-apply** (`auto_apply.why_wait` → waiting, reason in plain
words) and marks the work **Needs you** (`/api/work`, the hand-off card, `/api/office`). The Oracle has
no implementation authority: it cannot change the verdict, the artifact or the project. If it cannot
run (no model, twice interrupted, unreadable answer) the gap is recorded and a triggered code change
**waits for Nick** instead of applying (missing coverage is never clean).

`oracle_reviews(job_id, subject, attempts, status, …)` mirrors `review_runs`: RUNNING rows become
INTERRUPTED at engine start and are retried at most twice.

## 4. Live state API (D-66)
Read-only; the renderer polls it. Plain words only — no tiers, lease ids, run ids or event names.

`GET /api/office?project=<id|*>` →
```
{generated, project, items:[{job_id, title, project_id, conversation_id, submission_id,
  kind:'code'|'writing'|'research'|'recipe', state, status_line, needs_you,
  progress:{done, total, label}, team_size, started_at, updated_at}]}
```
Active work plus work settled in the last 24 h (at most 20). `state` ∈ `working | in_review |
needs_you | done | stopped | failed`. `progress` counts accepted steps out of real milestones and names
the phase in words ("2 of 3 steps done", "Checking the result") — never a percentage.

`GET /api/office/item?job=<id>` →
```
{job_id, title, project_id, kind, state, status_line, needs_you, why, next, progress,
 staff:[{id, role, role_label, doing, state:'working'|'done'|'failed'|'stopped'|'waiting',
         model, model_label, version, model_confirmed, provider, runtime, runtime_version,
         reasoning, asked:{model_label, reasoning}|null, note, started_at, finished_at}],
 steps:[{id, label, state, at}], review:{verdict, checked_by, independence, findings:[…]},
 oracle:{state:'not_needed'|'waiting'|'running'|'done'|'could_not_run', why, independence, findings:[…]},
 files_changed:[path…]|null, verification:{result, summary:[…]},
 links:{conversation_id, submission_id, message_seq}}
```
Finding rows: `{severity:'blocker'|'critical'|'note', area, summary, where, status:'open'|'resolved'}`.
The desktop allowlist (`kelRequestGuard.ts`) admits exactly these two GET shapes; `kelApi.ts` gets
`kelOffice(project)` and `kelOfficeItem(job)` with typed results. No UI is built here (a Figma
exploration is choosing the design).

## 5. Migrations and storage
One additive migration, **35 `v2-workforce-live`** (`staff.ensure_schema`, idempotent, no table
altered): `role_models(role PK, mode, model, reasoning, updated)`, `staff_calls(id PK, job_id,
milestone_id, role, instance, kind, subject, state, asked, ran, why, summary, started, finished)`,
`staff_model_status(model PK, status, reason, at)`, `oracle_reviews(job_id, subject, attempts,
status, detail, PK(job_id, subject))`. Existing tables are read, never reshaped: `contracts` carries
`staffing`; `team_assignments`/`team_events` carry the authority snapshot and `staffing.decided`;
`findings`/`evidence_records` carry review and Oracle results. `Store.claim` gains an optional
`staff=` argument that writes the step's `staff_calls` row **in the claim transaction**.

## 6. Failure and restart behaviour
- The decision is frozen in the contract; a restart never re-staffs a job. Old jobs (no `staffing`)
  run exactly as before.
- A step's binding lives with its run (`staff_calls.id = run id`, written in the claim transaction);
  an adopted broker after restart resumes on the same model and reasoning. A run fenced by V2-11
  recovery marks its staff call `stopped`.
- Reviews keep `review_runs` recovery; the Oracle keeps `oracle_reviews` recovery (≤ 2 attempts, then
  a recorded gap). Staff calls left `running` by a killed engine become `stopped` at the next start.
- A preferred model that is missing (no CLI, no credential, rejected) falls back per routing; a Fixed
  one that is missing leaves the step waiting with a plain reason (existing `wait_for_route`).
- Invariants unchanged: executor never reviews itself (`record_review`), reviewers read-only with
  tools off, authority only narrows (the executor's `team_assignments` snapshot keeps the tool policy;
  `role_for` and artifact binding now skip review roles so a Verifier row can never become the
  executor's policy), budgets and caps as before, D-64 protected paths, D-65 applies only a VERIFIED
  change with no live pod or Oracle blocker.

## 7. What stays deferred (and why)
- **Parallel code streams (D3 for coding):** needs per-stream project copies in the coding bridge.
- **A separate Sentinel staff member:** the security lens runs inside the Verifier's review;
  Sentinel remains Automatic with no dedicated review call.
- **Red Team mode, adaptive gating (5.7), depth-2 grandchildren:** unchanged, still deferred.
- **DeepSeek Flash:** there is no DeepSeek adapter; Utility work always falls back (recorded).
- **The Office UI and the Settings row for role models:** data only here.
- **Scoping (vetting) as the default for big requests:** not built. What it would take: a size/risk
  trigger at `_plan` (the same features as staffing: complexity ≥ 2 or D2+ with a flag) that routes the
  request into `vetting_session` instead of `_handoff`, a D-55-compatible "ask before starting"
  acknowledgement, and a hand-off from the accepted scope into `_start_work` — plus Nick's call on
  where the threshold sits.

## Needs Nick (conservative choices taken; each is one setting or constant to change)
1. **Chat model vs role models.** A model picked in a chat applies to that chat's work (CH-2 kept);
   otherwise roles decide. Nick may prefer roles to always win for staff.
2. **"Auto" reasoning** means "the model's own default level" (Codex: medium for Astra/Luna); the chat
   turn decision stays `low`. No role starts above its default.
3. **Model ids for Claude Opus 5.5 and Fable 5.1.** The installed Claude Code (2.1.215) lists
   `claude-fable-5` and `claude-opus-4-8` but not these; Kel asks for `claude-opus-5-5` /
   `claude-fable-5-1` with the CLI's own `--fallback-model opus|fable`, and records what actually ran.
4. **Non-code writing at D1+ is staffed as Builder** (charter wording); D-67 describes Builder as
   coding.
5. **Oracle thresholds** (10 files / 400 changed lines, flags, D4) and "a triggered code change whose
   Oracle could not run waits for you".
6. **Staffed jobs below D3 run one step at a time** (previously independent parts could overlap).
7. **Kel (Commander) now prefers ChatGPT Luna** for replies and plans when no chat model is saved;
   messages with images still go to the Anthropic API worker when it is available.
