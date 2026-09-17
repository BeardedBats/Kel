# 04 — Sidebar and Navigation

Everything below is measured from the running packaged build (`visual-a.json` shell capture) or read from the
audit baseline `ffeef73`. The sidebar is 268px wide in the default (expanded) state; rows are 34px tall with a
36px pitch.

## 4.1 What the sidebar actually contains (measured, top → bottom)

| y (px) | Item | Type | Evidence |
|---|---|---|---|
| 0–39 | Minimize / Maximize / Close | window controls | `visual-a.json` shell.nav |
| 3 | Collapse, Search messages, Back, Forward | titlebar icon buttons, 36×36, radius 6px | shell.nav |
| 91 | **New Chat** | button, **208×34, radius 7px** | shell.nav |
| 127 | **Work** | primary nav row, 34px | `SiderNav/KelNavEntries.tsx:18` |
| 163 | **Projects** | primary nav row | same |
| 199 | **Permissions** | primary nav row | same |
| 235 | **Transcription** | primary nav row | same |
| — | *divider* | 1px `--color-border-2` | `Sider/index.tsx:196` |
| — | **Pinned** | section label (only when non-empty) | `GroupedHistory/index.tsx:394` |
| — | *(Team slot)* | **rendered empty** | `Sider/index.tsx:206` passes `afterPinnedContent={<></>}` |
| — | **Projects** | section label; workspace folders | `GroupedHistory/index.tsx:417-419` |
| — | **Conversations** | section label; today/yesterday/… | `GroupedHistory/index.tsx:241-249` |
| bottom | **Back to Chat** / **Settings**, theme toggle (settings only) | footer | `SiderFooter.tsx:83-140` |

Conversation rows measured at 34px height, 244px wide, `padding-left: 10px`; project-grouped rows indent to
`ps-34px` (`ConversationRow.tsx:170`).

## 4.2 Semantics — what each thing means (item 14 of the report)

**The word "Projects" means two different things in the same application.** This is the single largest
source of confusion in the sidebar, and it is not a styling problem.

| Where | What "Project" means there | Evidence |
|---|---|---|
| Sidebar → **Projects** section | a **workspace folder on disk**, grouped with the conversations that ran in it | `GroupedHistory/index.tsx:221-238` — groups built from `item.workspaceGroup.workspace` / `display_name` |
| Primary nav → **Projects** page | the engine's **knowledge / map / recipes console for the single implicit `default` project** | `pages/kel/projects/index.tsx:36` reads `/api/work`; header prints `project_id === 'default' ? 'General' : project_id` |
| Engine | a real `projects` table exists | `roots/*/kel.sqlite3` — `projects` table present in every audited store |

So a user who clicks **Projects** expecting their folders gets "General · 0 knowledge records · map — ·
5 recipes" — a memory console. A user who sees a folder in the sidebar labelled as a project group cannot open
it as a place at all.

**Folders vs Projects:** they are not the same concept and neither is user-managed in the sidebar. Groups are
derived from the workspace recorded on each conversation; the only per-group actions are "new chat in this
workspace" and "archive project" (`GroupedHistory/index.tsx:426`, `460-490`). There is **no** create-folder,
rename-folder, or move-conversation affordance anywhere in the main sidebar.

**What a Project owns today.** From the engine store and the renderer: conversations (grouped by workspace),
and — on the `/projects` page — memory records, the project map, and recipes, all for `project_id` `default`.
The renderer never passes a project id to those calls: `kelWork('main')` and `kelMemoryAction(...)` default to
`'main'`/`'default'` (`components/kel/kelApi.ts:170,178`). **Therefore a user cannot select, create, or scope a
project from the UI at all**, and every Projects/Work surface silently reads the one implicit project.

**How a user enters a Project from the sidebar: they cannot.** There is no project home surface and no route
that opens a project. Documented plainly because the brief asked for exactly this determination.

**Conversation robot/agent icons (item 13).** Measured on a populated profile: 5 rows → **2 rows show the
generic `i-icon-robot` outline icon**, 3 show a round 16px agent logo image. The resolution logic
(`utils/conversationAssistantIdentity.ts:74-127`) branches: preset-assistant emoji → emoji; preset-assistant
image → image; `conversation.assistant` without avatar → **`assistant_fallback` → generic Robot**
(`ConversationRow.tsx:104-112`); otherwise backend logo, else generic message icon
(`ConversationRow.tsx:115-124`). In Kel's one-assistant framing (V1.5 G7 record: "the normal conversation does
not expose model, worker, provider, or agent selection") this leading mark is decoration: it either repeats the
same backend logo on every row or shows a generic robot/message glyph that distinguishes nothing. It is not
misleading, but it is redundant — and it costs 22px + 8px of every row.

## 4.3 Defect — Settings navigation ejects the user into the main sidebar (item 3) — **S1, reproduced**

Clicking **Agents**, **Team roles** or **Tools** in the Settings sidebar replaces the settings sidebar with the
main application sidebar, because those entries redirect *out of* the `/settings` prefix and the shell switches
on the prefix only (`Sider/index.tsx:52`, `203-208`).

| Settings entry (label the user sees) | Route | Redirect target | Result |
|---|---|---|---|
| Agents (`SettingsSider.tsx:87`) | `/settings/agent` | `/team/roster` | settings sidebar disappears |
| Team roles (`SettingsSider.tsx:92`, `defaultValue: 'Team roles'`) | `/settings/skills` | `/team/roster` | settings sidebar disappears |
| Tools (`SettingsSider.tsx:97`) | `/settings/tools` | `/autonomy` | settings sidebar disappears |

Redirects: `components/layout/Router.tsx:129-141`.

Measured, by clicking the entries in the running app:

```
#/settings/appearance  hasSettingsSider=true   hasMainNavWork=false
#/team/roster          hasSettingsSider=false  hasMainNavWork=true
#/team/roster          hasSettingsSider=false  hasMainNavWork=true
#/autonomy             hasSettingsSider=false  hasMainNavWork=true
```

Two further consequences: the Settings footer entry flips from "Back to Chat" to **"Settings"**
(`SiderFooter.tsx:83`), so the way back is not obvious; and because `/team/roster` and `/autonomy` are not
settings routes, the user's next Settings click lands on **Appearance** again
(`Sider/index.tsx:70-72` navigates to a fixed `/settings/appearance`, not the last settings tab).

**Fix options (in preference order):** (a) give these three destinations real settings routes that render the
same components inside the settings shell (e.g. `/settings/team`, `/settings/permissions`); (b) keep the
redirects but render the Kel pages inside the settings shell when reached from settings; (c) if they are not
settings, remove them from `SettingsSider` and put Team/Permissions in the primary nav where they belong.
Do **not** fix this by making the main sidebar appear less often — the destinations are correct, the
shell-switch trigger is wrong.

## 4.4 Settings shell inventory and dead entries

`SettingsSider` renders `model, agent, skills, tools, appearance, webui, pet, system, archived, about`
(`SettingsSider.tsx:39-49`) with group headers AI Core / Application / Archived conversations / Other.
`/settings/assistants`, `/settings/capabilities`, `/settings/skills-hub` are legacy redirects to
`/team/roster` and should either be deleted or given an explicit "opens Team" affordance so the hop is
intentional rather than a shell failure.

## 4.5 Dead code found while tracing (not user-visible, worth knowing)

`components/layout/Sider/TeamSiderSection.tsx` (327 lines: team list, pin, rename, archive, and the
**create-team modal**) is **not imported or rendered anywhere** — `Sider/index.tsx` never mounts it, and
`afterPinnedContent` is an empty fragment. The donor team route is disabled at the router
(`Router.tsx:61` `HIDE_DONOR_AGENT_SURFACES = true` → `/team/:id` redirects to `/guid`). So the sidebar "Teams"
feature is unreachable in V1.6 while its source remains in the tree. This is also why "Add Agent" cannot be
found (see `07_TEAM_AND_AGENTS.md`).

## 4.6 Empty / sparse sidebar states (items 10, 12)

With no conversations the scroll area renders Arco's `Empty` with `t('conversation.history.noHistory')`
(`GroupedHistory/index.tsx:258`) — a bare centred empty block inside a large white area; the four nav rows
above it are 34px tall against a 900px viewport, so the sidebar reads as mostly whitespace. Recommend a
one-line, left-aligned hint plus the New Chat affordance, not a centred illustration-style empty.

## 4.7 Recommendation (minimum coherent model)

1. **Rename the nav entry** `Projects` → **Knowledge** (or "Project knowledge"), because that is what the page
   contains. Keep the word "Projects" for the sidebar folder groups — or rename those to **Workspaces**.
   One word must not mean two things.
2. **Promote the sidebar section labels to real structure**: Pinned / Workspaces / Conversations, with the
   workspace disclosure showing "N conversations" and an explicit "Open project" action once such a surface
   exists.
3. **Make Permissions and Team reachable from the primary nav** (or from Settings, correctly staged — see
   4.3). Today Team is reachable *only* through the settings entry that breaks the shell.
4. **Drop the per-row leading icon** in the single-assistant case (keep it where a conversation genuinely
   belongs to a different assistant), and reclaim the 30px for the title.
5. **Reserve action space properly**: the row must reserve `end-8px + 20px + 8px gap = 36px`, not 16px
   (see `03_CHAT_AND_COMPOSER.md` §3.4).
6. **Never create a conversation that has no turn** (see `03_CHAT_AND_COMPOSER.md` §3.5) so the sidebar
   cannot accumulate rows that say nothing.
