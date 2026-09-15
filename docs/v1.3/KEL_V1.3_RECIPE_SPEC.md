# KEL V1.3 — RECIPE SPEC (C5: Reusable Workflow Recipes)

Status: Gate 1 design deliverable. Approved checkpoint: reviewer relay CONTINUE (2026-09-14).
Basis: V1.2 deterministic compilers (CONFIRMED in source: `core.validate_contract`,
`engine.compile_document`, `coding.compile_coding`, `research` pipeline); donor audit (conductor:
per-type forbidden-field validation + explicit terminate step — ADAPT; forge: honest third
terminal state — ADAPT idea only; brief C5 initial recipe list).

## 1. Purpose and scope

Recipes are **validated declarative templates** that compile into the existing CompletionContract
system. They encode repeatable workflows (Fix Bug, Audit and Repair, Ship Release, Research Then
Implement, Continue Work) as data, so Kel can run them deterministically through the *existing*
scheduler, store, verification, and publication paths.

Hard boundaries:

- Recipes never execute anything themselves. There is no recipe runtime, no DAG engine, no visual
  editor. Compilation produces a CompletionContract; everything after that is V1.2 machinery.
- Compilation refuses anything the existing system cannot execute: only the trusted check kinds
  (`contains`, `min_chars`, `manual_review`), at most 5 milestones (existing contract bound),
  dependency acyclicity, no executable oracles.
- Terminal verdicts remain Kel-controlled (`assess()`); recipes may declare *which outcomes they
  promise* but cannot change how verdicts are produced.
- Versioned: every recipe has an immutable `(recipe_id, recipe_version)` with a content digest;
  runs pin the exact version they compiled from.

## 2. Recipe schema (schema_version = 1)

Strict validation: unknown fields are errors (conductor discipline — a field for another kind of
step must be rejected, not ignored).

| Field | Type | Rules |
|---|---|---|
| schema_version | int | must be 1 |
| recipe_id | str | slug `[a-z0-9-]{3,64}`, unique per scope |
| recipe_version | str | `MAJOR.MINOR.PATCH`; immutable once saved |
| name / description | str | name ≤ 80 chars; description ≤ 500 chars |
| source | str | `builtin` \| `project` \| `from_job:<job_id>` (provenance; from_job requires user confirmation to save) |
| kind | str | `coding` \| `document` \| `research` \| `mixed` |
| inputs | list | each: `{name, type: text\|path\|choice\|bool, required, default?, choices?, max_chars?, description}`; validated at invocation; missing required input → ask, never guess |
| steps | list | 1–5 items (contract bound). Each: `{id, title, action: plan\|work\|check\|review, kind_override? (mixed only), objective (template with {inputs}), depends_on: [ids], checks: [ {kind, value?/rubric?} ], retries: {max_attempts 1..4, on_fail: retry\|escalate\|block}}` |
| permissions | list | subset of `project:read`, `project:write`, `tests:run`, `web:search`, `files:attach`; undeclared use at compile time = hard error |
| verification | list | required check kinds per step; every step must include at least one; `manual_review` requires a nonempty rubric |
| terminal_states | list | subset of `[VERIFIED, FAILED, UNCERTAIN]`; `UNCERTAIN` must remain possible (honesty requirement) — declaring only `[VERIFIED]` is rejected |
| budget | int | 1..100 attempt units (existing contract semantics); default 8 |
| retry_policy | dict | `{max_attempts_per_milestone: 1..4, provider_switch_after: 2}`; must not exceed engine caps |

Template rules: `objective` strings may reference `{input_name}` placeholders only; no free-form
code, no shell, no URLs executed. All template expansion happens at compile time and is persisted
in the contract.

## 3. Example recipe (annotated)

```json
{
  "schema_version": 1,
  "recipe_id": "fix-bug",
  "recipe_version": "1.0.0",
  "name": "Fix Bug",
  "description": "Reproduce, diagnose, implement, test, and review a bug fix in this project.",
  "source": "builtin",
  "kind": "coding",
  "inputs": [
    {"name": "bug", "type": "text", "required": true, "max_chars": 2000,
     "description": "What is broken, and how do we see it?"},
    {"name": "scope", "type": "text", "required": false, "max_chars": 500,
     "description": "Optional area/paths to focus on."}
  ],
  "steps": [
    {"id": "reproduce", "title": "Reproduce the failure",
     "action": "work", "kind_override": null,
     "objective": "Reproduce the reported failure: {bug}. Record the exact command and output.",
     "depends_on": [], "checks": [{"kind": "min_chars", "value": 80},
                                  {"kind": "manual_review", "rubric": "The reproduction is concrete: exact steps or command, observed vs expected."}],
     "retries": {"max_attempts": 2, "on_fail": "escalate"}},
    {"id": "fix", "title": "Implement the fix",
     "action": "work",
     "objective": "Diagnose and implement the smallest correct fix for the reproduced failure. Scope hint: {scope}.",
     "depends_on": ["reproduce"],
     "checks": [{"kind": "manual_review", "rubric": "The change addresses the reproduced failure without unrelated edits."}],
     "retries": {"max_attempts": 4, "on_fail": "escalate"}},
    {"id": "verify", "title": "Tests and independent review",
     "action": "review",
     "objective": "Run the project test command and have the result independently reviewed.",
     "depends_on": ["fix"],
     "checks": [{"kind": "manual_review", "rubric": "Tests pass on the current tree and the fix matches the reproduction."}],
     "retries": {"max_attempts": 2, "on_fail": "block"}}
  ],
  "permissions": ["project:read", "project:write", "tests:run"],
  "verification": ["repository_evidence", "manual_review"],
  "terminal_states": ["VERIFIED", "FAILED", "UNCERTAIN"],
  "budget": 10,
  "retry_policy": {"max_attempts_per_milestone": 4, "provider_switch_after": 2}
}
```

## 4. Validator rules (strict; every rule gets a test)

Structural (types/ranges per §2) plus:

1. **Unknown fields are errors** (per-recipe and per-step), with a message naming the field.
2. Step `id`s unique; `depends_on` only references existing step ids; dependency graph acyclic
   (same discipline as `validate_contract`'s cycle rejection).
3. 1–5 steps; every step has ≥1 check; check kinds limited to `contains` / `min_chars` /
   `manual_review`; `manual_review` requires a nonempty rubric; no executable oracles ever.
4. Permissions ⊆ enum, and **kind-specific minima**:
   - `coding`: must include `project:read`; steps whose objective implies file changes must declare
     `project:write`; any step whose checks imply test execution must declare `tests:run` —
     otherwise compile refuses (undeclared capability = hard error).
   - `research`: must include `web:search`.
   - `mixed`: every step requires an explicit `kind_override` ∈ {coding, document, research}.
   - `document`: no extra minima.
5. `terminal_states` must be nonempty, ⊆ {VERIFIED, FAILED, UNCERTAIN}, and **must include
   UNCERTAIN** (a recipe may not promise certainty).
6. `budget` 1..100; `retry_policy.max_attempts_per_milestone` 1..4;
   `provider_switch_after` == 2 (engine behavior; any other value rejected until the engine
   supports it).
7. `recipe_version` is `MAJOR.MINOR.PATCH`; `(recipe_id, recipe_version)` is immutable — saving
   different content under an existing version is rejected (bump the version instead).
8. `source = from_job:<job_id>` requires that the job exists and that saving carries an explicit
   user confirmation flag (proposal flow, §7).
9. Template placeholders in `objective` may only reference declared `inputs`.

Error style: each rejection is user-readable (what/why/how to fix), mirroring the V1.2 failure
explanation style.

## 5. Compilation to CompletionContract

`compile_recipe(recipe, inputs, project_id)` produces:

```json
{
  "request": "<rendered invocation summary: recipe name/version + input values>",
  "kind": "<recipe.kind>",
  "budget": 8,
  "recipe": {"id": "fix-bug", "version": "1.0.0", "digest": "<sha256 of canonical recipe>"},
  "source_digest": "<optional; project fingerprint at compile time>",
  "milestones": [ ... one per step, dependencies preserved ... ],
  "final_milestone": "<id when a synthesis milestone is appended>"
}
```

Mapping rules (all reusing existing compilers and validation):

- **steps → milestones**: ids preserved; `objective` rendered from the template; `depends_on` →
  milestone dependencies; `checks` carried verbatim (validated); per-kind engine additions:
  coding milestones go through the coding pipeline (`compile_coding` semantics: snapshot → turn →
  fixed test command → diff digest → review); research steps go through the research pipeline
  (citation-gated); document steps follow `compile_document`; a document recipe with more than one
  step gets the existing supervised `combined-result` synthesis milestone appended (one voice).
- **permissions → capabilities**: `project:read`/`project:write` → coding snapshot/apply paths;
  `tests:run` → the engine-run fixed test command; `web:search` → research adapter; `files:attach`
  → handoff attachments. The engine's existing hard filters still apply at routing time; a recipe
  cannot widen them because the compiled contract only ever *narrows* capability demand.
- **verification minima**: every milestone ends with the trusted checks it declared; coding
  milestones additionally carry the engine's repository-evidence verification exactly as
  `compile_coding` does today (engine computes it; recipes cannot fake test evidence).
- **terminal states**: carried as recipe metadata used in messaging; **`assess()` is untouched** —
  VERIFIED/FAILED/UNCERTAIN verdicts remain the engine's own (brief: "Recipe terminal verdict
  remains Kel-controlled").
- **provenance**: `recipe.compiled` event; the contract digest pinned in `contracts`; Work context
  shows recipe name+version; the V1.2 publication text and verification summary are unchanged.
- **invocation**: missing required input → ask the user; invalid choice → explicit error; the
  rendered request strings are persisted with the contract (auditable).

## 6. Initial recipe library (V1.3)

**Amendment A1 (permissions enum).** The enum in §2/§4 gains `commands:run`: execution of
*declared project commands* (package / smoke), run by the engine itself with the same fixed-command
discipline as the test command. Recipes referencing those commands without `commands:run` fail
validation; projects without declared commands produce a clear compile error ("declare package/
smoke commands in the project map first").

1. **Fix Bug** (kind=coding, §3 example). Mirrors the existing coding pipeline: reproduce → fix →
   tests+review. Permissions: project:read, project:write, tests:run. Approvals for file writes
   flow through the existing coding approval gates.
2. **Audit and Repair** (kind=mixed). Inputs: `area` (optional), `depth` (choice quick|deep,
   default quick). Steps: `audit` (document; findings artifact; min_chars + manual_review) →
   `repair` (coding; objective references the findings artifact; existing snapshot/test/review
   pipeline; writes remain approval-gated) → `verify` (review). Permissions: project:read,
   project:write, tests:run, files:attach. "Repair approved scope" is enforced by the existing
   approval + digest-bound apply paths, not by recipe code.
3. **Ship Release** (kind=mixed). Inputs: `version` (required), `notes` (optional). Steps:
   `baseline` (document: tree state, hashes, declared commands) → `tests` (engine-run fixed test
   command; tests:run) → `package` (commands:run: declared package command) → `smoke`
   (commands:run: declared smoke command) → `manifest` (document: version + hashes artifact;
   freeze record). Permissions: project:read, tests:run, commands:run, files:attach.
4. **Research Then Implement** (kind=mixed). Inputs: `question` (required), `deliverable`
   (optional). Steps: `research` (research pipeline; web:search; citation-gated evidence) →
   `approach` (document: chosen approach + rationale) → `implement` (coding) → `verify` (review).
   Permissions: project:read, project:write, tests:run (when verification runs tests), web:search.
5. **Continue Work** (special). Compiles to a *continuation invocation*, not a new contract: the
   steps map onto the continuation stages — resolve prior job → validate current state → preserve
   accepted milestones → resume remaining → review and publish. Inputs: optional text hint only.
   No candidate → the §4 "none" message. This is the only recipe that creates no new job.

All five are seeded as `scope='builtin'` and are also the first candidates for demonstration in
Gate 7's live acceptance runs.

## 7. Versioning and storage (migration 004)

```sql
CREATE TABLE IF NOT EXISTS recipes(
  recipe_id TEXT NOT NULL,
  recipe_version TEXT NOT NULL,
  scope TEXT NOT NULL,            -- 'builtin' | 'project'
  project_id TEXT NOT NULL DEFAULT '',   -- '' for builtin
  digest TEXT NOT NULL,           -- sha256 of canonical recipe JSON
  data TEXT NOT NULL,
  source TEXT NOT NULL,           -- 'builtin' | 'from_job:<job_id>' | 'user'
  created REAL NOT NULL,
  updated REAL NOT NULL,
  PRIMARY KEY(recipe_id, recipe_version, scope, project_id));
```

- **Seeding** is idempotent (`INSERT OR IGNORE`); changing builtin content requires a version bump.
- **Precedence**: a project-local recipe shadows a builtin with the same `recipe_id` inside that
  project; both remain inspectable (scope shown).
- **Immutability**: rows are append-only; re-saving an existing `(id, version, scope, project)`
  with different content is a `PolicyError` (bump the version).
- **Propose → confirm → save**: `propose_from_job` builds a draft (steps from milestones, checks
  from the contract, inputs inferred; preview mandatory); **saving requires explicit user
  confirmation**; saved with `source='from_job:<job_id>'` and a `recipe.saved` event. No automatic
  saving, ever.
- Project-local recipes use the same validated schema; there is no separate file-based format in
  V1.3.

## 8. Acceptance mapping (brief recipe matrix → test ids)

| Brief item | Test id |
|---|---|
| Each initial recipe compiles to a valid CompletionContract | REC-01 |
| Interrupted recipe resumes | REC-02 |
| Accepted steps remain frozen | REC-03 |
| Failed step receives bounded repair | REC-04 |
| Recipe cannot escalate undeclared permissions | REC-05 |
| Recipe terminal verdict remains Kel-controlled | REC-06 |
| Project-local recipe versioning works | REC-07 |
| Saving a successful run as a recipe requires confirmation | REC-08 |

## 9. Explicit non-goals

No visual workflow editor; no generic DAG platform; no sub-recipes/nesting in V1.3; no invocation
hooks (conductor removed its own as never-effective — do not resurrect); no recipe marketplace or
sync; no worker-chosen commands (only declared, engine-run commands); recipes never alter
`assess()`; no new approval mechanisms beyond the existing gate mapping.


