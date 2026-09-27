# D-57 implementation design — scheduled tasks as scheduled Recipes in the engine

Status: approved for implementation 2026-09-27 (decision D-57 by Nick; the design's open policies settled
by the coordinator below). A schedule is a **trigger**, not a new kind of work: each firing becomes an
ordinary submission → D-53 hand-off → ordinary job, so Work, Activity, Needs you, the card, Retry, Stop
and "Why this model?" come for free. Run history is derived from events + submissions + jobs (no run
table, no task table). Build after D-54 (Projects) lands; schedules carry `project_id`.

## Contract changes (engine API as implemented — the renderer builds against this)
The sections below named the actions but not their JSON; these are the exact shapes. All times are
**epoch seconds** (floats). A refusal is HTTP 400 `{error: "<plain sentence>"}` (PolicyError).

`POST /api/schedules {action, ...}`:

| action | request | response |
|---|---|---|
| `list` | `{project?: id\|'*'}` (omitted = every project) | `{schedules: Schedule[], needs_attention: n}` |
| `get` | `{id}` or `{origin}` | `{schedule: Schedule, conversations: {created: n, open: n}}` |
| `create` | `{name, project_id, target, cadence, timezone?, start_mode, conversation_id?, model?, skip_if_running?, enabled?}` | `{schedule}` |
| `update` | `{id, …any create field}` | `{schedule}` (a valid update clears `problem`; it never replays) |
| `pause` / `resume` | `{id}` | `{schedule}` (resume re-validates and refuses in plain words) |
| `delete` | `{id, conversations: 'keep'\|'delete'}` | `{ok, id, hidden: cid[], kept_open: cid[]}` (`hidden` = engine chats now hidden; the shell removes their donor rows) |
| `run_now` | `{id}` | `{submission, conversation}` |
| `history` | `{id, limit?}` (default 50) | `{rows: HistoryRow[]}` newest first |
| `preview` | `{cadence, timezone?, count?}` (default 3) | `{valid, message, description, next: number[], timezone_label}` — never 400 for a bad cadence |
| `import` | `{items: ImportItem[]}` | `{results: [{origin, id, status: 'imported'\|'imported_paused'\|'exists'\|'refused', problem, message}]}` |
| `migration_status` | `{}` or `{record: {…summary}}` (marks done) | `{done, at, summary}` |

```
Schedule = {id, name, project_id, project_name,
  target: {kind:'recipe', recipe_id, inputs, recipe_name} | {kind:'instruction', text},
  cadence: {kind:'manual'} | {kind:'cron', expr} | {kind:'interval', minutes} | {kind:'once', at},
  timezone: IANA name | null (= this computer's zone), timezone_label,
  start_mode: 'new_conversation'|'existing', conversation_id, conversation_title,
  model: {provider, model|null} | null (= Automatic), model_label,
  skip_if_running, enabled, status: 'active'|'paused'|'needs_attention'|'done'|'manual',
  description ("Every weekday at 9:00 AM"), next_due_at, running, last_run: HistoryRow|null,
  problem, origin, created, updated}
HistoryRow = {at, slot, late_by, conversation, job_id, submission_id, status, label, cause}
  status: running|needs_you|success|needs_look|stopped|not_started|settled|skipped|queued|
          coalesced|missed|imported   (label is the plain sentence to show; cause may be null)
ImportItem = {origin, name, project_id?, target, cadence, timezone?, start_mode,
  conversation_id?, model?, skip_if_running?, enabled?, problem?, runs?: [{conversation_id, at}]}
  (an item that fails validation is imported paused with that refusal as its `problem`)
```
Hidden conversations (deleted schedules' run chats) are left out of `/api/state` `conversations` and
`GET /api/conversations`, so the boot adoption loop never sees them. `GET /api/conversations` rows
created by a schedule carry `schedule_id`. Scheduled runs' user message carries
`meta = {kind:'scheduled', schedule_id, name, slot}`. Activity rows of kind `scheduled` carry
`schedule_id`.

## Settled policies
1. "Skip if still running" means exactly what it says. Migrated donor tasks map `skip_if_running =
   state.queue_enabled` (the switch Nick saw was labelled "Skip if still running").
2. Deleting a schedule soft-deletes it; conversations its new-conversation runs created (with no open
   job) are **hidden** via an engine conversation-hidden flag (add it; the boot adoption loop must skip
   hidden conversations). Open runs are kept and the confirm says so.
3. Missed runs: after sleep/closure only the newest slot runs, if ≤ min(12 h, cadence gap) late; older
   slots are recorded as one "Missed N runs while Kel was closed". Minimum interval 5 minutes.
4. Vendor `tzdata` into the engine build (requirements + `collect_data_files('tzdata')` in
   `KelEngine.spec` + THIRD_PARTY_NOTICES line); fall back to the computer's zone if unavailable.
5. The recipe picker lives under the dialog's Advanced settings (Figma gap; record in FIGMA_GAPS.md).

## Engine (`runtime/kel/schedules.py`, migration = next free number after Projects)
```sql
CREATE TABLE IF NOT EXISTS schedules(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, project_id TEXT NOT NULL,
  target TEXT NOT NULL,       -- {"kind":"recipe","recipe_id","inputs"} | {"kind":"instruction","text"}
  cadence TEXT NOT NULL,      -- {"kind":"manual"}|{"kind":"cron","expr"}|{"kind":"interval","minutes"}|{"kind":"once","at"}
  timezone TEXT, start_mode TEXT NOT NULL,   -- 'new_conversation'|'existing'
  conversation_id TEXT, model TEXT, skip_if_running INTEGER NOT NULL DEFAULT 1,
  enabled INTEGER NOT NULL DEFAULT 1, next_due_at REAL, queued_slot REAL, last_slot REAL,
  zone_sig TEXT, problem TEXT, origin TEXT UNIQUE,
  created REAL NOT NULL, updated REAL NOT NULL, deleted REAL);
CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(next_due_at) WHERE enabled=1 AND deleted IS NULL;
```
Events on aggregate `schedule:<id>`: created/updated/paused/resumed/deleted/imported and run events
fired/skipped/queued/missed/not_started, each with `dedupe='schedule:<id>:<slot>'` (manual:
`…:manual:<submission>`) so a slot never fires twice.

- Cadence: stdlib 5-field cron parser (`*`, lists, ranges, steps, MON-SUN/JAN-DEC, Vixie DOM/DOW OR) +
  `next_after(cadence,tz,after)`; DST gap → first valid minute, fold → once; intervals anchored to
  `created`; `once` fires at most once; `manual` only via Run now; `zone_sig` recompute on tz/clock change.
- Scheduler runs inside `Service._tick` at most every 5 s (no daemon); skips while draining/stopping;
  compare-and-set claim of `next_due_at`; missed-run policy; still-running (latest fired submission
  PLANNING or job not CLOSED/CANCELLED, AWAITING_USER counts) → skip or one coalesced queued run; the
  engine's InstanceLock guarantees a single scheduler per Data root.
- Firing: resolve conversation (`new_conversation` → `context.conversation(project,title='<name> · <local
  time>')`; `existing` → must exist in the project) → `service.submit(data, origin={id,name,slot,late_by,
  model})` with deterministic id `sched-<id8>-<slot>`; `origin` is Python-only (HTTP can't fake it).
- `_plan`: scheduled submissions go straight to `_handoff` with a template acknowledgement "Scheduled run
  of “<name>” started. I'll post the result here once it has been checked." (no turn model).
- `_start_work`: recipe invocation compiles via a `_recipe_contract` helper extracted from `_recipe_run`;
  `contract['schedule']={id,name,slot,model}`; guard: no greenfield, coding instruction without a project
  folder refused in plain words.
- `ModelPrefs.resolve_for_job` prefers `contract.schedule.model` (never rewrites a conversation's choice).
- History fold (`Scheduler.history`) → rows `{at,slot,late_by,conversation,job_id,submission_id,status,
  label,cause}`; "Success" only for CLOSED+VERIFIED; CLOSED+other → "Finished — needs a look".
- API `POST /api/schedules {action}`: list, get (id|origin), create, update, pause, resume, delete
  (`conversations:'keep'|'delete'` → hides), run_now, history, preview (description + next 3), import
  (main-process only), migration_status. Validation: project exists; existing conversation in same
  project; recipe gettable + dry compile; model validated; once in future; interval ≥ 5 min.
- `activity.py`: kind `scheduled`, plain sentences, project from `detail.project_id`.
- Problems (recipe/project/conversation gone) set `problem`, pause the schedule, and surface in Needs you.

## Migration of donor cron (main process, once, through the engine API)
New `desktop/packages/desktop/src/process/services/kel/scheduleMigration.ts`, called from `initializeKel`
after the mapping/reconcile block: read `migration_status`; `core('/api/cron/jobs')`; map cadence
(`cron`/`every`<5 min → paused+problem/`at` past → paused once/'' → manual), text, name, conversation
(`existing` via mapping, else new with a note), project (from workspace via `for_folder`, else chat's
project, else default), model (validated, else Automatic + note), skip (= queue_enabled), enabled, up to
20 past run conversations as `schedule.imported_run` events; `import` (idempotent by `origin UNIQUE`,
`next_due_at` from now — never replays); **only after** the engine confirms, disable each donor job
(`PUT /api/cron/jobs/<id> {enabled:false}`); record done. Then retire donor cron from the renderer:
remove `ipcBridge.cron`, `listByCronJob`, cron notification/skill-suggest UIs; keep old `cron_trigger`
artifacts rendering and pointing to `/scheduled?origin=…`. Donor rows stay disabled (not deleted) for
one release.

## Renderer
`kelApi.ts` `kelSchedules` + types; `kelRequestGuard.ts` allows `schedules` and refuses `import`;
`KelService.ts`: extract `adoptEngineConversation(cid)`, IPC `kel:open-engine-conversation`, 20 s
adoption sweep for scheduled-run conversations, call the migration; preload exposes the IPC.
`pages/cron/`: `useSchedules.ts` replaces `useCronJobs.ts` (refresh on mount/focus/visibility/15 s while
visible/after actions); `cronUtils.ts` builds cadences and uses engine descriptions; delete
`repairCronJobTimeZone.ts`, `jobAgentMeta.ts`, `resolveCronAgentConfig.ts`; `ScheduledTasksPage/index.tsx`
(list from engine, "Needs attention" chip, footer "Scheduled tasks run while Kel is open on this
computer."); `TaskDetailPage.tsx` (delete the legacy duplicate block; pause/resume/update/runNow/history;
Project row shows name; route `:id` + `?origin=`); `CreateTaskDialog.tsx` (Assistant fixed to Kel; Model
from `/api/model` with unavailable options disabled; start mode; skip; Advanced: Project select + "Run a
recipe instead"; live preview "Next: …"; submit create/update with engine refusal text);
`CronJobManager.tsx` → `ScheduleIndicator`; update ChatConversation/ChatHistory/GroupedHistory/
ConversationRow/team hooks/SkillSuggest/MessageCronTrigger/Router; `needsAttention.ts` schedule problems.

## Tests
Engine `runtime/tests/test_v2_schedules.py`: parser; next_after incl. DST + tz fallback; missed policy
(within window once late; beyond → missed only; hourly after 8 h = 1 run + 7 missed; replay no dup);
fire → normal submission/ack/job visible in state('*')/_work/activity; skip vs queue; recipe schedule
(card, recipe_marks, library.history; continue-work no job); guards (no greenfield, missing root,
deleted recipe/project/conversation → problem+pause); model preference not rewriting chat choice;
history labels; API actions; import idempotent; draining blocks firing; migration fixtures.
Desktop: request-guard (schedules allowed, import refused), `schedule-migration.test.ts` (import-before-
disable, crash between, idempotent rerun, refused items still disabled+paused), `schedules-surface.dom`
(renders from engine payloads, JR-47 missing fields, no machinery nouns), needsAttention schedule problems.
