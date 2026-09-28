# Routing 2 — task-aware, evidence-driven model routing

Status: design for implementation, 2026-09-27. It finishes workforce-os doc 10 ("Model & provider
routing", 2026-09-17) on top of what D-66/D-67/D-69 built. Inputs read: handoff §§14–16; intent
document (2026-09-27) §§4, 12, 13; workforce-os docs 01, 05, 10, 14, 15 (recovery archive, read-only);
`docs/v1.5/05_ROUTING.md`; `docs/v2/design/D-66_WORKFORCE_LIVE.md`; decisions D-64..D-70; the engine
code named below; a live off-screen check of the packaged build of `main@61c73ff` on a copy of Nick's
data (reported by the coordinating agent); and a read-only study of three donors (below).

Nothing here changes who decides: Nick's per-role choice (Fixed / Preferred / Automatic, D-67) and
D-69 ("staff always use their role models; the chat model is Kel's own") always win. Routing only
decides what Nick left to Kel, and says why.

## 1. What doc 10 specifies

| § | Requirement |
|---|---|
| 1 | Keep V1.5's deterministic eligibility filters + cost ordering; add a requirement vocabulary, **dispatch tiers fast / standard / deep / assurance set per task in the contract**, AUTO/PREFERRED/FIXED, a heterogeneity rule, a **budget governor with reserve-before-spawn**, per-model overlays, a **calibration harness** feeding quality floors (advisory, ≥ 3 samples). |
| 2 | Default requirement profiles and tiers per role (Commander deep, Discovery standard/fast, Builder standard/fast/deep, Verifier and Sentinel **assurance, never downgraded for cost**). |
| 3 | Review in a different family (then provider); reduced independence is coverage debt, never clean. |
| 4 | Overlays: subordinate per-model patches, no-op when absent. |
| 5 | Mission budget classes **tiny / standard / deep / high-assurance** with token, wall-clock and (where measurable) cost ceilings; reserve before spawn; exhaustion stops with a wait reason, never a silent downgrade of a safety reviewer; accounting reuses `provider_usage` + quota telemetry; spent vs reserved on the record. |
| 6 | Retry ladder (same binding → provider diversity at attempt ≥ 2; auth → 24 h circuit; quota excludes); a reroute records its reason; never silent. |
| 7 | Calibration: real task prompts, latency / tokens / cost, optional model judge; **advisory only**; quality floors stay evidence-based (≥ 3 verified outcomes per task class per provider); no black-box learned routing. |
| 8 | Non-goals: no per-token micromanagement, no silent downgrade of assurance, no model-branded roles. |

## 2. What exists (measured in code, before this work)

| Piece | Where | State |
|---|---|---|
| Eligibility + cost order, preferred first, explicit wins, recent-failure demotion | `router.select` | built (V1.5, V2-09); cost/latency are per **adapter**, not per model |
| Decayed outcome evidence (7-day half-life, 30-day window, weight floor 3) | `routing_evidence` | built; keyed by **provider only** — `job_kind` is recorded but never read (`05_ROUTING.md` open item) |
| Role → model (Fixed / Preferred / Automatic), real reasoning flags, independence for reviewers, refused-model memory (24 h) | `role_models`, `staff`, engine `_role_binding` | built (D-67/D-69); Automatic = "adapter by cost, runtime's default model"; a Preferred model that cannot run falls back to that same cost order |
| Staffing tier D0–D4 + feature vector + budget class | `staff.plan_job`, `staffing.decide` | built; `budget_class` is always `standard` (nothing sets it) |
| Budget | job units (`budget`/`spent`/`reserved` count runs); `budget_reservations` table (migration 21) exists but only the Phase 5.1 demo path uses it | no token/time/cost ceilings |
| Usage capture | Claude CLI reports `usage` + `total_cost_usd` (kept in the run result, used only as a per-adapter cost average); `provider_usage` table only holds credential events | **Codex usage is dropped** (exec `turn.completed.usage`, app-server `thread/tokenUsage/updated`); no per-model or per-job accounting; coding runs report no duration |
| Turn classification | `turn.decide` (model: reply / work / amend); `router.classify` regex decides `kind` | the **regex decides the class** (coding / document); the model only decides work-or-not |
| DeepSeek | catalog row, no adapter ("Not supported for chat yet") | Utility always falls back |
| Calibration harness, overlays, dispatch tiers | — | not built (`assignment.DISPATCH_TIERS` is a vocabulary only) |

## 3. The live check (packaged `main@61c73ff`, copy of Nick's data)

Request in a real project (calc.py + test_calc.py, test command set, Full access): "In this project,
add a multiply(a, b) function to calc.py and a pytest test for it in test_calc.py." Result: a
*writing* job, no files changed, failed. Root causes, all in `runtime/**`:

1. **Coding floor missed.** The floor is `text.startswith(CODING_VERBS)`; "In this project, add…"
   does not start with a verb, and the regex classifier returned `conversation`, so the job compiled
   as a document even though the turn model said "work".
2. **Codex errors were thrown away.** `codex exec --json` reports a failed turn as
   `{"type":"turn.failed","error":{"message":…}}`; the parser read only a top-level `message`, so every
   refusal became "Native turn failed" and the refused-model memory never matched.
3. **Availability was a guess.** `/api/model roles` marked GPT-6 Luna / Astra available because a
   Codex adapter existed. Codex answered HTTP 400 "not supported when using Codex with a ChatGPT
   account" (Luna) and "requires a newer version of Codex" (Astra). The same model was tried again in
   the same job.
4. **Wrong note.** After two failed attempts the engine removes the failing adapter for provider
   diversity; `resolve` then said "needs Codex, which is not set up on this computer" — false.
5. **No replacement reviewer.** The Verifier's model failed at run time and the review became
   UNCERTAIN; D-69's hand-off to the next model only happened at resolution time (and only for the
   Oracle's wording). Kel's planner likewise dropped to the fixed template although other models ran.
6. **Old Codex.** `codex` on PATH is the Codex desktop app's bundled CLI 0.142.5; an npm-global
   0.144.5 exists (latest 0.157+). Kel used whichever came first on PATH and recorded no version.
   (`~/.codex/models_cache.json` is shared with the desktop app and reflects the last client that
   fetched it — 0.142.5 saw only GPT-5.5; 0.158.0 sees the GPT-6 family.)

Also reported: `/api/project create` with a backslash path answered "That folder does not exist".
The engine resolves backslash paths (pinned by a test over the real HTTP handler); the renderer's
`JSON.stringify` and the main process's `fetch` preserve them. The most likely cause is the
reproduction itself: a path typed inside a JavaScript string literal loses its backslashes (`\U`,
`\A`… are identity escapes). Not reproduced as a product defect (§8); if it recurs from the real
folder picker, capture the request body.

## 4. Donors (read-only study; patterns, no code)

- **Forge** (github.com/Adulari/forge @ `39a63bb`, AGPL-3.0 — patterns only). Rule-based mesh routing
  with a normative spec (`docs/features/mesh-routing.md`, constants checked by CI). Additive score per
  tier (capability fit weighted by tier, cost class free/subscription/metered, quota penalties,
  log-scaled subscription burn); high effort orders by benchmark band first, low effort cheapest
  first. **Eligibility is separate from ranking** and every decision's rationale is persisted.
  **Typed provider errors** (rate-limited / unavailable / auth / capability / no-model-access /
  context overflow) each get their own health response: capability/no-access excludes the model for
  24 h, transient benches ~60 s, context overflow is never the model's fault, auth escalates from the
  model to the provider only on a repeat ≥ 120 s later; any success clears health. An LLM classifier
  (small fixed model, hard timeout, cache) may only **raise** the heuristic tier; follow-ups inherit
  the task's tier. Usage: Claude input = input + cache read + cache creation; Codex input already
  includes cached; unknown cached tokens stay unknown; an unpriced metered model is never "free".
  Its only learned signal (`duel_boosts`) stable-sorts by boost alone — one win jumps the whole list
  (a flaw to avoid).
- **MoFlo** (github.com/eric-cielo/moflo @ `5aefad9`, MIT). The "learned routing" chooses agent
  types, not models: successes are embedded as keyword patterns; failures are ignored; quality
  defaults to 0.85/0.3; no decay, no minimum samples; the model router's outcome history is recorded
  but never read; its circuit breaker is in memory only. Useful idea only: outcome-aware ranking
  per task type. Everything it lacks (decay, sample floor, negative evidence, persistence) is what
  Kel's `routing_evidence` already has — so Kel keeps its own evidence and adds the task class.
- **ryderderder/orchestrator** (@ `5bc35eb`, MIT). Reads native-CLI capacity from local sources
  (Codex rollout JSONL `rate_limits`, Claude statusLine JSON); exclusion first, ranking only reorders
  survivors; failure signals expire at the window's reset. Confirms Kel's approach (Codex quota from
  `account/rateLimits/read`, usage from the CLIs' own stream output).

**Adopted:** separate eligibility from ranking with a recorded reason per candidate; typed refusal
reasons with their own durations (§5.0); evidence as a *bounded* step inside tier fit (never a sort by
evidence alone); classifier may raise but floors never lower; usage normalised per runtime with
unknown kept unknown; unpriced models never treated as free. **Avoided:** sort-by-boost, defaulted
quality, in-memory health, complexity scores from word length.

## 5. Plan

### 5.0 Live-check fixes (first)
- **Codex CLI choice:** `native.codex_executable()` picks `KEL_CODEX_PATH` when set, else the newest
  installed Codex CLI among PATH entries, the npm-global package's native binary and the desktop
  app's bundled CLI (each asked `--version` once per process). The version rides every staff call
  (`ran.runtime_version`) and the Office detail shows it. Kel never updates a CLI itself.
- **Refusals are read and classified:** the Codex parser keeps `turn.failed.error.message`; a refusal
  is one of *account* ("your ChatGPT account doesn't offer it in Codex"), *old runtime* ("the Codex
  on this computer is too old for it"), *not found* — recorded at the first failure from any call
  site (staff step, Verifier, Oracle, Kel's turn/plan) with its plain reason and the runtime version.
  An old-runtime refusal lasts until the CLI version changes; the others 24 h. `/api/model roles`
  shows `available:false` with that reason; the card shows it on the staff row.
- **Honest notes:** `resolve` distinguishes "not installed" from "set aside for this step" and from
  "refused" — never "not set up" for a runtime that is set up.
- **Fallback at run time:** the Verifier and the Oracle hand the review to the next model (another
  family first, then the same family with reduced independence recorded) when the chosen one
  refuses or fails to start, up to three models; only when none can review is the check unverified.
  Kel's planner tries its role model, then the other runnable models, before the fixed template.
- **Coding floor:** a coding verb after a short lead-in ("In this project, add…", "please fix…") or a
  coding verb with a code file or code noun (function, test, class, module, bug) inside a project
  with a folder is coding.

### 5.1 Task classes and dispatch tiers
`kel/task_routing.py`. Task classes (plain labels): **quick answer** (Kel's own reply), **planning**
(Kel's plans), **research**, **coding**, **design**, **writing** (documents and posts — D-69 item 4
keeps it on the Builder), **review** (Verifier / Oracle / Sentinel), **utility** (short mechanical
work). Each class names the role whose Settings row governs it (quick answer / planning → Kel,
research → Discovery, coding / writing → Builder, design → Designer, review → Verifier, utility →
Utility).

Every staffed step gets `task_class` and `dispatch` (fast | standard | deep | assurance), frozen in
`contract['staffing']['steps'][id]`. Base tier per class (doc 10 §2): quick answer / utility fast;
research / coding / design / writing / planning standard; review **assurance, always** (never
lowered). The turn classifier's tier hint (5.5) sets a work step's tier; rules only raise it: a
security / irreversible / data-migration flag or complexity ≥ 2 on code → at least deep; D0 mechanical
work may stay fast. `assurance` for a work step is read as deep.

**Tier → reasoning and strength.** A role whose reasoning is **Auto** gets the tier's level: fast →
Low, standard → the model's own default (unchanged from D-66), deep → High, assurance → High,
clamped to what the model's runtime offers. An explicit reasoning level in Settings always wins.
Each catalog model carries a coarse **strength** (1 fast/cheap, 2 balanced, 3 strongest) and a
**list price** (USD per million input / cached / output tokens: DeepSeek's own pricing page and
OpenRouter's public model list, read 2026-09-27; used only to *estimate* cost when a runtime reports
tokens but no cost).

**Per-class ranked list** (`task_routing.ranking`): the role's Settings row first — Fixed: only that
model; Preferred: that model, then its D-67 fallbacks (Builder → Codex) — these are protected and
never moved by evidence. The remaining runnable models follow, ordered by: tier fit (|strength −
target|, target fast 1 / standard 2 / deep 3 / assurance 3), then evidence (5.3), then measured cost,
then measured latency, then name. Models that cannot run here are listed last with the reason.
`role_models.resolve(..., task_class, tier)` uses it: a Preferred model that cannot run falls to the
next *ranked* model (not "Kel's usual routing"); **Automatic** picks the top ranked model (with its
model flag), so Automatic finally chooses a model, not just a runtime. Review roles keep D-69's
family rule on top of the ranking.

### 5.2 Real cost and latency
`kel/usage.py`, reusing `provider_usage` (one `{"event":"run", …}` row per run/review/Oracle call,
idempotent per call id, indexed by job). Sources, verified on this PC (not guessed):
- Claude Code `-p --output-format json`: `usage` {input, cache_creation, cache_read, output},
  `total_cost_usd` (API-equivalent), `modelUsage`, `duration_ms` (seen in a real native log).
- Codex `exec --json`: `turn.completed.usage` {input_tokens, cached_input_tokens, output_tokens,
  reasoning_output_tokens} (field names in the 0.142.5 binary's event schema).
- Codex app-server: `thread/tokenUsage/updated` {tokenUsage: {total, last: {inputTokens,
  cachedInputTokens, outputTokens, reasoningOutputTokens, totalTokens}}} (protocol v2 struct names in
  the binary) — the coding bridge now keeps it.
- Kel's Claude host (`host_claude.mjs`/`native_claude.mjs`): passes `usage`, `total_cost_usd`,
  `duration_ms`, `modelUsage` on `turn/completed`.
- Anthropic API / DeepSeek / OpenRouter: the response `usage` (OpenRouter's reported `cost` when it
  sends one).
Normalised to *processed tokens* (Claude: input + cache creation + output; Codex: input − cached +
output + reasoning), cached tokens separately (unknown stays unknown), cost with its basis
(`reported` / `estimated from list price` / `unknown`), wall-clock ms measured around every
execution by the broker. The router's per-adapter cost/latency now come from these measurements (a
coding run reports its duration too), and the ranking reads per-model medians (30-day window).
Subscription runtimes' dollar figures are API-equivalent effort, not money charged — labelled so.

### 5.3 Outcome-aware routing (MoFlo's idea inside doc 10's limits)
`routing_outcomes` gains `task_class` (additive column) and every row written (review verdicts,
milestone failures) carries it and the model that ran. `routing_evidence.class_summary(task_class,
models)`: decayed per (task class, model): first-try VERIFIED 1.0, VERIFIED after rework 0.5,
FAILED 0; weight floor 3 **and** ≥ 3 samples. **Promote** at ≥ 0.85 (one tier-fit band up),
**demote** below 0.5 (to the end of the runnable list). Bounds: never past a Fixed/Preferred choice
(protected head), never lifts a weaker model above a stronger one for an **assurance** binding,
never removes a model. Every step's staff call records the class, tier, the top of the ranking and
the plain reason ("Promoted: verified in 92% of its recent coding runs"); `/api/model {action:'why'}`
reads it back.

### 5.4 Budget governor
`kel/budget.py`. Classes and default ceilings (until Nick sets them):

| Class | Processed tokens | Run time | Cost (API-equivalent) | Given to |
|---|---|---|---|---|
| tiny | 300 k | 20 min | $2 | D0 |
| standard | 3 M | 90 min | $10 | D1, D2 |
| deep | 8 M | 4 h | $30 | D3, or D2 with complexity ≥ 2 |
| high-assurance | 15 M | 8 h | $60 | D4, or any security / irreversible / release / data-migration flag |

The class is frozen in the staffing record. **Reserve before spawn:** before a staffed step is
claimed, the engine estimates the step (measured median for its class and model, else the class
default) plus its review, and checks spent + open reservations + estimate against each ceiling; the
reservation is written in the claim transaction (`budget_reservations`, reservation id = run id)
and settled with the measured usage. **Exhaustion** stops the job before the next step
(`WAITING_RESOURCE`, route block "Budget reached: …" in plain words, marked Needs you) — never
auto-retried, never continued on a cheaper model. Reviews of finished work and the Oracle always
run on their assured model (their share is reserved with the step). `POST /api/office
{action:'raise_budget', id}` moves the job one class up (recorded, one Activity line) and resumes it.

### 5.5 Classification
The turn model (still the low-cost call: Kel's model at Low reasoning, 30 s) returns, for work,
`task_class` and `tier` besides title and acknowledgement. That is primary: research → a research job,
coding → the coding path (with a project folder; greenfield otherwise), design / writing / utility →
the planned document path with the class recorded. `router.py`'s regexes stay as floors that can
only force work or force coding (never turn work into a reply, never downgrade a class), and as the
fallback classifier when no turn model is available.

### 5.6 Missing adapters
`kel/api_models.py`: one OpenAI-compatible text adapter, used for **DeepSeek** (`deepseek-flash`,
`https://api.deepseek.com`, `DEEPSEEK_API_KEY`) and **OpenRouter** (`https://openrouter.ai/api/v1`,
`OPENROUTER_API_KEY`) as a second route to the same catalog models (DeepSeek Flash =
`deepseek/deepseek-v4.1-flash` there). Keys stay in the shell's OS-backed custody and reach only the
engine's environment at spawn (as the Anthropic key does); the engine stores metadata only. Without a
key the role row says "needs a DeepSeek API key" (honest), and routing skips it.

### 5.7 Calibration harness
`kel/calibration.py`: fixture suite (per task class: prompt + deterministic checks), runner that
measures latency / tokens / cost through the same usage normaliser, optional judge hook, results in
`calibration_runs`; advisory only (shown beside the ranking, never moves it). A fixture run ships with
the tests; a live run needs Nick.

### 5.8 API (read-only; the Settings UI can come later)
`POST /api/model {action:'ranking'}` → `{classes:[{task_class, label, role, role_label, mode, tier,
tier_label, models:[{id, label, rank, runnable, protected, why, evidence:{sentence, rate, samples},
measured:{runs, median_ms, avg_tokens, avg_cost, cost_basis}, calibration}]}], tiers, budget_classes}`.
The renderer needs: a read-only "How Kel picks models" table per task class under Staff & models
(D-70 item 3) with the reason per row; a "Raise budget" action on a budget-waiting card
(`/api/office {action:'raise_budget'}`); and the staff row's runtime version (already in
`/api/office/item`). No guard change is needed (`/api/model` and `/api/office` POST are allowlisted).

## 6. Needs Nick (the conservative option is built until he decides)

**Settled by D-72 (2026-09-28, recommended values; each is one setting to change), pinned by
`runtime/tests/test_d72_defaults.py`:** 1 tier → reasoning as built; 2 budget ceilings as in §5.4;
3 strength ranks derived from the list price (`role_models.strength_from_price`: output price under
$5 → 1, under $15 → 2, else 3; unpriced → 2), outcome evidence moves models in the ranking; 5 only
DeepSeek Flash on OpenRouter (the worker refuses other model ids); 6 Codex and Claude Code calls
rank at $0 marginal cost (`role_models.SUBSCRIPTION_ADAPTERS`) and a used-up plan quota makes the
model unrunnable in the ranking; 7 Kel's own turn, reply and plan calls are recorded in usage
(kinds `turn` / `reply` / `plan`, with the conversation and submission). The list below is kept as
the record of what was asked.
1. **Tier → reasoning for "Auto".** Built: fast → Low, standard → model default (unchanged), deep /
   assurance → High. Reviews therefore run at High by default. Alternative: keep every Auto at the
   model default.
2. **Budget ceilings** in §5.4 are starting values, not measured from Nick's work; exhaustion waits
   for him. He may prefer higher ceilings or no cost ceiling for subscription runtimes.
3. **Model strength ranks** (1–3) are coarse catalog values inferred from list price tier; he may want
   to set them.
4. **Codex version.** Kel picks the newest installed CLI or `KEL_CODEX_PATH`. With Nick's approval
   the npm-global Codex was updated to 0.157.1 (by the coordinating agent, 2026-09-27), and one-line
   `codex exec` calls ran GPT-6 Astra and Luna on his account with it — the live check's refusals were
   the old 0.142.5 on PATH. A refusal remembered from one CLI version no longer applies once the
   version changes. The desktop app's bundled 0.142.5 stays on PATH; nothing else needs Nick unless
   he wants a fixed path.
5. **OpenRouter scope.** Built only as a second route to catalog models (DeepSeek Flash). Which other
   OpenRouter models to offer (and whether) is his decision.
6. **Subscription cost.** Codex and Claude Code dollar figures are API-equivalent effort; Automatic
   ranking treats Codex as zero marginal cost when its subscription quota is observed (as before).
7. **Kel's own turn/reply calls** are not yet recorded in usage (only staff work, reviews and the
   Oracle are) — recording them is cheap if he wants Kel's own replies in the numbers.

## 7. Built vs still open after this work
Built (2026-09-27, one commit each on `main`):

| Increment | Commit | doc 10 |
|---|---|---|
| §5.0 live-check fixes (Codex CLI choice + version on staff rows, refusal reading and plain reasons, honest notes, run-time hand-over for planner / Verifier / Oracle, coding floor) | `7dd0611` | §3, §6 |
| §5.1 task classes, dispatch tiers, per-class ranking, tier → reasoning, `/api/model {action:'ranking'}` | `d26a4ee` | §1.2, §2 |
| §5.2 measured tokens / wall-clock / cost per call (`provider_usage`), fed to the router and the ranking | `96a8360` | §5 accounting, §1 cost ordering |
| §5.3 outcome evidence per (task class, model), promotion and demotion with bounds, "Why this model?" for staff | `1225bf4` | §1.7, §7 floors |
| §5.4 budget governor: classes, ceilings, reserve-before-spawn, plain stop, `raise_budget` | `c0cd740` | §5 |
| §5.5 model-primary classification (class + tier), regex floors as safety net | `3969511` | §1.2 (tier per task) |
| §5.6 DeepSeek Flash + OpenRouter workers, key injection from the desktop's custody | `c1ddfe2` | §6 credentials |
| §5.7 calibration harness (fixture run), advisory in the ranking API; migration 37 | `1806050` | §7 |

Engine API added for the renderer (no guard change needed): `POST /api/model {action:'ranking'}`
(per class: role, mode, tier, models with rank / runnable / protected / why / evidence / measured /
calibration); `POST /api/office {action:'raise_budget', id}`; `GET /api/office/item` now carries
`budget {class, ceilings, used, held, stopped, can_raise}` and each staff row's `runtime_version`;
`/api/model {action:'roles'}` rows say `available:false` with the refusal reason, and each model row
carries `runtime_version`. What the renderer would need: a read-only "How Kel picks models" table
per task class under Staff & models; a "Raise budget" button on a budget-stopped card; the runtime
version on the staff row.

Routing extras (2026-09-28, phase 3):
- **Codex replies stream.** `codex exec --json` has no partial events (checked live on 0.157.1: only
  `thread.started`, `turn.started`, `item.completed`, `turn.completed`); the app-server does
  (`item/agentMessage/delta` in the installed binary's generated schema). A streamed Codex reply now
  runs through the app-server with exec's limits (read-only, never asks, no tools, the user config's
  `notify` and MCP servers overridden) and feeds the same D-75.1 path; checked live with one short
  call (58 word updates). If the app-server cannot start, exec answers whole as before.
- **Per-model overlays** (`kel/overlays.py`): registry keyed by (runtime, model | family | '*'),
  versioned, appended after the prompt as a subordinate note, recorded on the call and in the staff
  call's `asked.overlay`. **Empty**: nothing in Kel's logs or tests shows a model quirk a patch
  fixes. The coding bridge does not apply overlays yet (nothing is recorded for it).
- **Subscription quota** (`kel/quota.py`): Claude Code's `rate_limit_event` (stream-json only — every
  Claude call now uses stream-json), Codex's `account/rateLimits/read|updated` and the rollout file
  of an exec session. Windows, pace samples and a reset-aware percent left on the provider state;
  exhausted → the plan's models can't run ("your Claude plan's 5-hour limit is used up until 15:40"),
  low (≤ 10% left, or on pace to run out before the reset with ≤ 25% left) → ranked one band lower
  and after same-fit peers, never past a Fixed/Preferred choice. `/api/model` `roles` and `ranking`
  carry `plans`. Kel's Claude host (coding) does not forward Claude's rate-limit events yet.
- **Local-only work**: a contract with `local_only: true` (or the `local_only` requirement) never
  reaches a cloud model; with none local it waits (`No model can do this:`) with plain words. This PC
  has no local models (no Ollama, no LM Studio); Kel has no local adapter, so detected runtimes are
  only reported (`/api/model` `local_models`).
- **KEL_PROTECTED_PATHS**: the desktop main process sets it for the engine (installed App folder and
  the credential folders).

Still open: a local model adapter, a live calibration campaign, and the renderer surfaces above
(including the plans and local models under Staff & models). (Kel's own turn/reply/plan calls are now in the usage
record — D-72; a research plan made by `compile_research` is not yet.)
Known limits: an outcome is recorded only for a reviewed verdict or a failed step, so work whose
contract has no review check never adds a success to the evidence; the coding path needs the
project folder to be a git repository (a plain folder fails to start with git's own message).

## 8. Reproduction note (backslash paths)
In a JavaScript string literal `'C:\Users\Nick\R6Proj'` is `C:UsersNickR6Proj` (unknown escapes
drop their backslash). Use `String.raw` or doubled backslashes when driving the renderer from page
JavaScript. The engine test `test_project_create_accepts_backslash_paths_over_http` pins the real
transport.
