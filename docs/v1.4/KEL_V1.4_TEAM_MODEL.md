# KEL V1.4 — TEAM MODEL

Status: v1 (2026-09-15) · Gate 2 design document. Companions: `KEL_V1.4_ARCHITECTURE.md` (§2 tables),
`KEL_V1.4_SECURITY_MODEL.md`, `KEL_V1.4_AUTONOMY_POLICY.md`.

> **Implementation status (V1.4.1):** role versioning, overrides, assignment snapshots, and the
> activity stream are implemented and tested. Tool-policy and guardrail *enforcement* statements in
> this document (§2 `BLOCKED`, §4, §6 `blocked`) describe the intended model: the checker exists but
> is not yet called on the execution path, and there is no `guardrail_decisions` table. See
> `docs/v1.4.1/02_RUNTIME_TRUST_BOUNDARY.md` and `06_V1_5_DEFERRED_WORK.md`.

Kel remains the single accountable voice. The Team is an optional, inspectable organization behind it.

## 1. Entities and relations

    role_template ──1:n── role_versions (append-only; each has instructions, tool policy,
                                         model preference, budget, department, status)
        │
        ├── role_overrides (scope = project | task; points at a version, never edits it)
        │
        └── team_assignment (freezes role_version_id + policy/model/budget snapshot at creation)
                 │            links: job_id, milestone_id, run_id, provider, model
                 ├── assignment_activity → team_events (append-only stream)
                 └── assignment_artifacts (digests; evidence classes)

- **Roster** = role_templates (+ current version, status). **Office** = team_assignments only.
- An assignment row is created **only together with a real run** (engine `claim()` path); the Office
  query joins assignments to `runs`/`jobs`, so a decorative worker cannot appear. Empty Office states
  point at the Roster instead of inventing staff.

## 2. Lifecycle (derived, never authored)

| Assignment state | Derived from | UI wording |
|---|---|---|
| QUEUED | job milestone READY, no run | `Queued` |
| ACTIVE | run state RUNNING | `Running…` |
| WAITING | run WAITING_APPROVAL / job WAITING_RESOURCE | `Waiting on you` / `Waiting on resource` |
| BLOCKED | guardrail decision recorded | `Blocked by guardrail` |
| DONE | milestone ACCEPTED and assessment VERIFIED | `Verified` |
| UNCERTAIN | assessment UNCERTAIN | `Uncertain — needs evidence` |
| FAILED | run failed past attempts / job BLOCKED | `Failed — see cause` |

State is computed from the engine; no UI or role can set it directly. Every transition appends a
`team_events` row (see §6).

## 3. Roles (instructions, versions, scopes)

- **Instruction schema (structured, not prose):** *Goal* · *Inputs* · *Outputs* · *Quality bar* ·
  *Boundaries (editable)* · *Locked guardrail block* (read-only) · *Escalation rules* · *Evidence
  expectations*. Editing is per-field; the locked block is rendered read-only and diff-protected.
- **Versioning:** editing a role creates a **new version** (`role_versions`, append-only). Diff view
  compares any two versions; **rollback** = new version copied from an older one (history never lost).
- **Scopes and resolution order** (at assignment creation): task override → project override →
  global default. The resolved set is **snapshotted** into the assignment; later edits cannot change a
  running assignment's instructions.
- **Seeded roles (V1.4):** Solution Strategist · UI/UX Expert · Research Specialist · Implementation
  Engineer · QA Engineer · Security Reviewer · Independent Reviewer · Release Engineer ·
  Documentation Specialist. Departments group them (Strategy, Product, Engineering, Verification,
  Delivery).

## 4. Policies per role

- **Tool policy (status V1.4.1):** allow/deny lists (`read`, `write`, `run_tests`, `install`,
  `browser`, `git`, `external_api`, `shell`) are stored per role version and snapshotted into the
  assignment, but they are **not yet enforced against a worker**; worker tool access is bounded by
  each adapter's own configuration (internal allowlist; native text slice with tools disabled; coding
  host full access — see the trust boundary doc). Enforcement is V1.5 work.
- **Model preference:** ordered list of (provider, model) with a fallback chain; empty = provider
  default. Availability/quota comes from the providers table (see Provider spec).
- **Budget:** attempt units (existing `budget`/`spent`), wall-clock cap, and — where measurable —
  token/time accounting. Exhaustion stops the assignment and reports the wait reason; it never
  silently continues.
- **Recursion ban:** an assignment can never create another assignment or spawn work. Enforcement is
  structural today: workers get no spawn-style tools (unknown tool calls are denied — `test_core.py`
  covers `spawn_agent`), native CLIs run with multi-agent/computer-use features disabled, and the
  engine caps concurrent runs. There is no separate engine check beyond this.

## 5. Staffing plan and “why this specialist”

At plan time the Solution Brief records the staffing decision: for each milestone, the chosen role,
the recorded reasons (capability match, tool needs, budget fit, provider availability), and the
alternatives considered. The Office shows those recorded reasons; it never generates post-hoc
explanation copy. A staffing plan is a **plan artifact** reviewable before execution.

## 6. Activity contract (`team_events`)

Append-only rows: `id`, `at`, `kind`, `actor` (assignment id or `kel`), `job_id`, `milestone_id`,
`run_id`, `refs_json`, `detail_json`.

| kind | emitted when | required refs |
|---|---|---|
| `assignment.created` | assignment row created with its frozen snapshot | job, milestone, role_version |
| `assignment.started` | run claimed | run |
| `step.started` / `step.finished` | bounded worker step boundaries | run, step |
| `artifact.produced` | artifact digest stored | run, digest, filename |
| `evidence.recorded` | evidence class + source captured | run, class, digest |
| `decision.made` | worker decision summary (no hidden reasoning) | run, summary |
| `approval.requested` | approval gate opened | run, approval_id |
| `blocked` | guardrail/policy stop | run, guardrail_decision id |
| `assignment.finished` | terminal state with verdict | run, verdict |

Forbidden in events: raw chain-of-thought, prompts, secrets, unrelated private content. Events are the
only source for the Office timeline and for completion receipts.

## 7. API surface (additive, allowlisted)

| Endpoint | Purpose |
|---|---|
| `GET /api/team/office?project=` | live + historical assignments with derived state |
| `GET /api/team/roster` | role templates + current versions + status |
| `GET /api/team/roles/:id` / `:id/versions` / `:id/diff?from=&to=` | role inspection |
| `PUT /api/team/roles/:id` | create new version (structured fields only) |
| `POST /api/team/roles/:id/rollback` | new version from a prior one |
| `POST /api/team/overrides` | project/task override create/update |
| `GET /api/team/assignments/:id` / `/activity` / `/artifacts` | assignment detail, timeline, evidence |
| `GET /api/work?conversation=` (existing) | Work panel; extended with assignment ids |

All endpoints are read-only except role/override edits, which write new versions and append events.

## 8. Audit guarantees (what an assignment must answer later)

For any historical assignment: which instructions governed it (version id + hash), which tools/models
it was allowed, its budget and spend, every meaningful action (events), the artifacts and evidence
digests, its provider/model/session (B3 provenance), and the verdict + receipt. This is the
inspectability promise of the product model.

## 9. Tests (TEAM-*)

Role versioning · rollback · project override · task override precedence · locked-section
immutability · assignment snapshot immutability · no-recursive-delegation · Office-shows-only-real-
assignments · tool-policy denial fails closed · budget exhaustion stops cleanly · activity contract
field completeness + no-CoT sampling · staffing reasons recorded in the brief.
