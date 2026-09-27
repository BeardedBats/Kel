# D-54 implementation design — Projects as the one context boundary

Status: approved for implementation 2026-09-27 (decision D-54 by Nick; open questions settled below by the
coordinator under handoff §36 "conservative inference"). Engine is the single source of truth for the
active project; all new engine logic lives in `runtime/kel/projects.py` so `service.py`/`acp_host.py`
edits stay thin.

## Contract changes / confirmations (engine agent, 2026-09-27)
No deviations from the shapes below; these pin down what the doc left open. Migration **32
`v2-projects`** is confirmed free (31 = `v2-handoff-and-conversation-indexes`).
- **Project row** (every action that returns a project): `{id, name, root, has_folder, test_command,
  kind, archived, archived_at, conversations, open_work, needs_you, updated, last_active, context}` —
  `has_folder` = root set and the folder exists; `archived` is a boolean (`archived_at` the time or
  null); `test_command` an argv list or null; `conversations` counts real chats (not `main`, not the
  hidden Recipe-runs chat); `open_work`/`needs_you` count jobs via `job_projects`.
- `/api/project {action}` returns: `list` → `{projects:[row], active}` (General first, then most
  recently active; `include_archived`/`include_system` booleans); `create`/`update`/`for_folder`/
  `archive`/`restore` → the project row (flat, so `.id` works like legacy create); `delete` →
  `{ok:true,id}`; `set_active` → `{active}`; `bind` → `{donor, project_id}`; `of` →
  `{project: row|null, pending, conversation}` (`pending` = the chat has no engine row yet, so
  `project` is where its first message will create it). `update` takes `id` plus any of `name`,
  `root` (`null`/`''` clears the folder), `context`, `test_command` (`null` clears). Refusals are
  plain sentences in `{error}` (HTTP 400) like every other route.
- `active` is a project id or `'*'` (All projects). `/api/state` gains `active_project`, and
  `projects[]` rows gain `kind`/`archived`; `conversations[]` rows gain `utility:true` for the hidden
  per-project Recipe-runs chat.
- `'*'` reads: `/api/memory` `proposals`/`history`/`learnings` return every live project's items,
  each carrying `project_id`; `/api/recipes` `list`/`search` return built-ins plus each live
  project's own recipes labelled `project_id`/`project_name`; `/api/map` refuses with "Choose a
  project to see its map."; `/api/work?project=*` has `memory:null`, `map:null`.

## Settled questions
1. The default project is shown as **General** (the engine's real name). "No project" is not used.
2. The sidebar bottom-nav **"Workspaces" slot is removed**. "Projects" opens the Projects area whose card
   nav gains **"All projects"** (`/projects/list`). **"Set up Kel" moves to Settings → Kel** (JR-14).
3. Moving an existing chat to another project is **out of scope**. In a chat, the header chip shows that
   chat's project; choosing another project makes it active for *new* chats and says so.

## Facts found (real Data, read-only)
8 project rows: `default` (General, 45 chats, 2 context packets), one greenfield user project
(`i-want-to-create-a-little-app-that-a`, test command, 1 job), and six plumbing rows (`Temp`, `work`
rooted at `Data\engine`, four `acp-temp-*`) owning nothing but 31 chats. Hazards: `Context.project()`
overwrites every column (rename would wipe root/context); `projects`/`conversations` inserts are
positional (add side tables, never columns); Knowledge/Map/Recipes resolve via conversation `'main'`;
Recipes page runs land in hidden `'main'`; Work merges only 4 conversations; the renderer hides plumbing
with regexes; migration numbers 31 is taken (engine indexes) — **Projects uses 32** (confirm free).

## Engine
### Schema (`projects.py`, migration 32 `v2-projects`, `ensure_schema` pattern; never alter tables)
```sql
CREATE TABLE IF NOT EXISTS project_meta(project_id TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'user',
  archived REAL, created REAL, utility_conversation TEXT);          -- kind: general|user|system
CREATE TABLE IF NOT EXISTS project_prefs(scope TEXT PRIMARY KEY, value TEXT, updated REAL NOT NULL); -- 'active' -> id|'*'
CREATE TABLE IF NOT EXISTS project_bindings(donor_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS project_moves(conversation_id TEXT, from_project TEXT, to_project TEXT, at REAL, reason TEXT);
```
`classify(store,row)`: `general` if id=='default'; `system` if name matches `-temp-[0-9a-z]+$`, or root
is/inside the OS temp dir or `/tmp`, or inside `store.root` or `store.root.parent/{engine,store,host}`, or
path contains `conversations/users`; else `user`. Rows without meta are classified on read and written.
Migration 32 (one transaction, counts in `schema_migrations.note`): meta row per project; each `system`
project owning nothing in any project-scoped table (memories, memory_proposals, memory_conflicts,
unrevoked grants, project_tests, project recipes, recipe_marks, project_maps, capability_leases,
solution_briefs, vetting_sessions, artifact_lineage, context_packets — check each table exists) gets its
chats moved to `default` (logged in project_moves) and is archived; system projects that own something
are only flagged+archived; nothing deleted; `project_prefs.active='*'`.

### `Projects` class
`list(include_archived=False, include_system=False)` → `{id,name,root,has_folder,test_command,kind,
archived,conversations,open_work,needs_you,updated,last_active}`; `create(name,root?,test_command?,context?)`;
`update(id, …partial…)` (only sent keys change; new root revokes grants; test_command=None deletes;
refuses system); `for_folder(root)` (live user project with that root, else create named after folder;
refuses plumbing roots); `archive/restore` (default not archivable; archive revokes grants; active falls
back to '*'); `delete` only if the project owns nothing ("This project still has 3 chats. Archive it
instead."); `active()/set_active(id|'*')` (rejects archived/system); `bind(donor_id,project_id)`
(idempotent); `resolve_new(project?,donor?)` = explicit → binding → active (real) → 'default';
`of(conversation?,donor?)` → `{project,pending}`; `job_projects(job,conv_map)` = conversation's project ∪
contract.project_id; `utility_conversation(pid)` (hidden per-project engine chat for Recipe runs).

### Service/API (thin hunks)
- `/api/project` with `action` → `Projects.apply` (list, create, update, for_folder, archive, restore,
  delete, set_active, bind, of); without `action` → legacy create (compat).
- `/api/conversation` → `{id,project_id}` with `resolve_new(data.project, data.donor)`; also accepts an
  explicit `id` (the engine agent's lazy creation reserves ids). The ACP host's first-prompt lazy creation
  must forward `donor` and use `resolve_new`.
- `acp_host.py`: stop sending `project:'default'`; send `{'donor': AIONUI_CONVERSATION_ID}` or `{}`.
- `state(cid, project=None)`: add `active_project`, `kind`/`archived` per project; filter jobs by
  `job_projects` and continuation by project when given. GET reads `project` query.
- `_work(cid, project=None)`: with project (id or '*') loop all jobs in scope; for '*' memory/map blocks
  are None. GET accepts `?project=`.
- `_scope(data, write=False)`: `data.project` (exists; writes not archived) | `'*'` (reads only) |
  `_project_of(conversation)`. Used by Knowledge, Map, Recipes, briefs, Activity. Memory writes in '*'
  mode must name the record's own project (keep `_owned_memory` guard).
- Recipes `run {project}` without conversation → utility conversation, returns `{submission,conversation}`;
  `preview` `needs_project` adds `project_id` and `missing:['folder'|'test_command']`.
- `activity.py`: match rows by `project_id in job_projects(...)`.
- Copy: coding-without-folder → "This looks like a code change, but this project has no folder yet. Open
  Projects, choose this project and set its folder and test command — or ask me to create a new project."
  Missing test command → "This project needs a test command. Set it in Projects before coding."
- Attention stays global (Needs you, palette, notifications, brief) — rows name their project.

## Renderer (paths under desktop/packages/desktop/src/)
- `renderer/components/kel/activeProject.ts` (new; delete `activeWorkspace.ts`): `useProjects()` →
  `{projects,active,activeProject,refresh}` (refresh on focus/visibility/`kel:active-project`);
  `setActiveProject(id|'*')` writes engine then broadcasts; one-time import of localStorage
  `kel.activeWorkspace_v1` if engine active is '*' and it names a live user project, then delete the key.
- `kelApi.ts`: `kelProjects.{list,create,update,forFolder,archive,restore,remove,setActive,bind,of}`;
  `kelState(conversation, project?)`; `kelWork*({project})`; replace `'main'` defaults with a
  `KelScope = {conversation}|{project}` body arg; extend project type.
- `ShellWorkspaceLink.tsx` (keep file/export): label = active project name or "All projects"; menu
  "Projects" label, "All projects", rows with check, "New project", "Manage projects" → `/projects/list`;
  prop `conversationId` → shows that chat's project via `of({donor})`, choosing another sets active and
  goes to `/guid` with note "New chats start in X. This chat stays in Y."; no regexes; no "Workspace".
- `KelDesktopProjectMenu.tsx` takes `{id,name,root}[]`; "No project" row → "General".
- `GuidWorkspaceFootnote.tsx` becomes a view of the same switcher (active name; list = engine projects;
  pick → setActiveProject; Browse → forFolder → setActive); drop recent-folders + mobile dropdown.
- `useGuidInput.ts`: dir from `activeProject?.root`; `locationState.workspace` → forFolder + set active.
- `useGuidSend.ts`: pass projectId, `workspace=root||''`, `custom_workspace=!!root`,
  `extra.kel_project_id`; after create `await kelProjects.bind(conversation.id, projectId)` before navigate
  (non-fatal); remove `setDir('')`.
- Forks (`useForkConversation.ts`, `ChatConversation.tsx`) bind to the source chat's project.
- `ChatLayout/index.tsx`: `<ShellWorkspaceLink conversationId=…/>`; right panel header "Workspace" → "Files".
- Composer footer (`AcpSendBox.tsx`, `AionrsSendBox.tsx`): show the chat's project name via a shared
  `useConversationProject(conversationId)` (folder as title); delete `displayWorkspaceName`.
- `KelDesktopWorkspaceHeader.tsx`: "Workspace" → "Files" (+ aria labels); update its DOM test.
- `KelInChatFrame.tsx`: card-nav group "Workspaces" removed; add "All projects" (`/projects/list`) to the
  Projects group; "Set up Kel" moves to the Settings nav ("Kel" group); headings: `/projects/list` →
  "Projects", `/onboarding` → "Set up Kel"; remove the project-name guess (use `useProjects`).
- `KelBottomNav.tsx`: remove the "Workspaces" slot; Projects active regex also matches `/projects/list`.
- `Router.tsx`: add `/projects/list` → new `KelProjectsList`.
- `pages/kel/projects/list.tsx` (new): rows name, folder (full path on hover), test-command chip, chat
  count; actions Open (set active → `/projects/knowledge`), Rename (inline), Set/Change folder (dialog),
  Test command (argv editor), Archive (confirm); "Archived" section with Restore (+ Delete only when
  empty); "New project"; deep link `?edit=<id>&focus=folder|test`; note "Your active project is the same
  on every device".
- `pages/kel/projects/index.tsx`: pass `{project: active}`; '*' mode: Knowledge grouped by project
  (actions send record's project), Map card "Choose a project to see its map.", Recipes show built-ins +
  each project's with label; `needs_project` → "Set project folder" button to `/projects/list?edit=…`.
- `pages/kel/work/index.tsx`: one `kelState('*', active)` + `kelWorkRows({project: active})`; delete the
  4-conversation merge; `kelTeam.office(active==='*'?'default':active)`.
- `pages/kel/activity/index.tsx`: `kelState(KEL_ALL_CONVERSATIONS, active)`.
- Scheduled page: until D-57 carries project ids, one plain line when a project is active: "Scheduled
  tasks show for all projects for now."
- `pages/kel/onboarding/index.tsx`: step "Workspace" → "Project"; "Workspace folder" → "Project folder";
  `chooseWorkspace` → forFolder + setActive; drop `kel.setupWorkspace_v1`.
- `kelRequestGuard.ts`: allow `state?conversation=(id|*)(&project=(id|*))?`, `work?(conversation=id|
  project=(id|*))`, `conversation`, `conversation-title`; keep refusing everything else.
- `KelService.ts:~404`: `kel_project_id: conversation.project_id` in `extra` for imported chats.
- i18n en-US: `guid.json` noProject → "General"; `conversation.json` unnamedSpace → "Project".

## Edge cases
Project without folder allowed (coding floor copy above; Recipe preview `missing` → "Set project folder");
archive not delete for projects with chats (chats stay openable, chip shows "Name (archived)", grants
revoked so Kel asks again); active archived elsewhere → engine falls back to '*', renderer re-reads on
focus; binding written before navigation wins over later switches; donor cron chats resolve to active
project until D-57 (note in KNOWN_LIMITATIONS); phone/WebUI share the global active project; check donor
`GroupedHistory` doesn't create folder-named groups (pass `custom_workspace:false` if it does); two
projects with the same folder → `for_folder` returns most recently updated live one.

## Tests
Engine `runtime/tests/test_v2_projects.py`: migration classification on an 8-row fixture (only
empty-owner plumbing moved, moves logged, owner kept), partial rename keeps root/context, root change
revokes grants, test_command None clears, set_active rejects archived/system, archiving active → '*',
delete refuses non-empty, default not archivable, resolve_new order, bind idempotent, `/api/conversation
{donor}` lands in bound project, state/work project filters, greenfield job in both projects, `_scope`
refuses '*' writes, recipe run utility conversation, preview `missing`, activity counts = work counts.
Update `test_acp_host.py` (donor not project), `test_v2_activity.py`, `test_v13_recipes.py`,
`test_b6_project_root.py` (new copy).
Desktop: `kel-project-switcher.dom`, `kel-projects-list.dom`, `kel-guid-project.dom` (create sends
`kel_project_id` and binds before navigate; footer/header agree), updates to navigation/pickers/
onboarding/request-guard/all-conversations tests, and a source guard `kel-no-workspace-label.test.ts`
(no user-facing "Workspace(s)" label in components/kel, pages/kel, pages/guid, ChatLayout, en-US guid.json).
