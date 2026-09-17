# 07 — Team and Agents

The question was: what does Kel currently mean by *Agent, Specialist, Team, Roster, Office, Studio, Worker,
Role* — and does V1.6 actually support user-created agents?

## Answer in one line

V1.6 supports **engine-seeded role templates only**. There is **no user-created agent, no role editor, and no
"Add Agent" affordance anywhere in the UI.** Several of the eight words are synonyms for one of two objects,
and two of them ("Team", "Agent") currently point at *disabled donor surfaces*.

## What exists, with evidence

| Word | What it actually is | Where the user sees it |
|---|---|---|
| **Role / Role template** | Engine object `role_templates` / `role_versions`, seeded from `SEED_ROLES` | `KelTeam` Roster list: `role.name`, `v{version}`, `{assignments} assignments` |
| **Specialist** | A role *bound to a milestone*, i.e. a live `team_assignments` row (`role`, `role_version`, `snapshot_digest`) | Work → "Team assignments" table, column header `Specialist`; Team → Office; copy "No specialist has been assigned yet." |
| **Worker** | Engine-side executor of a milestone. Not a user-manageable object | Work → milestone table column `Worker state` (raw engine state string) |
| **Team** | The page at `/team/office|roster|studio`, `h1` = "Team" | Main nav → Settings → Agents/Team roles (see below) |
| **Office** | Tab + card: live assignments only, chip `real assignments only` | `/team/office` |
| **Roster** | Tab + card: role templates grouped by `department`, each row `Open in Studio` | `/team/roster` |
| **Studio** | Tab + card: read-only role detail + `Locked guardrails` + `Version history` with rollback | `/team/studio` |
| **Agent / Assistant** | Donor concept. **Disabled in Kel** | `HIDE_DONOR_AGENT_SURFACES = true` (`components/layout/Router.tsx:61`) makes `/assistants` and `/team/:id` redirect to `/guid` |

Source: `pages/kel/team/index.tsx` (352 lines — tabs, cards, FIELD_LABELS, rollback), `components/kel/kelApi.ts`
(`kelTeam` = `office | roster | seed | role | history | rollback | timeline`), `components/settings/SettingsSider.tsx`
(settings entries).

## Creation is not possible from the UI — confirmed

`kelTeam` exposes exactly two mutations: `seed()` and `rollback(templateId, to)`.
The role editor (Studio) renders `detail.fields` as **text**, not inputs, and its guardrail block is labelled
`read-only — not editable by any role`. The only "create" affordance in the whole surface is the empty-state
button `Seed the default roster`.

**Recommendation: do not invent Add Agent in this pass.** Two options are honest:

1. **Rename to match reality** (preferred, cheap): the surface is a *roster of Kel's built-in roles plus a
   version history*, so label it as such and stop implying a staffing feature. Suggested: page title
   **"Team"** stays; tabs become **Working now** (`office`), **Roles** (`roster`), **Role detail** (`studio`).
   Drop the word "Studio" from the user's vocabulary — it implies authoring that does not exist.
2. **Add authoring later** (a real V1.7 feature): a *New role* action that copies an existing template into a
   new version (the engine already versions append-only and supports rollback, so "copy-forward" is the
   natural first authoring step).

## Defect found (real, cheap to fix)

`pages/kel/team/index.tsx`, Office empty state:

```tsx
actionLabel="Seed the default roster"
onAction={() => void load()}        // ← reloads; never seeds
```

versus the Roster empty state, which is correct:

```tsx
onAction={() => { void kelTeam.seed().then(load); }}
```

So the button offered in Office is a **no-op that can never do what it says**. Either call `kelTeam.seed()` or
remove the button and point at the Roster tab.

## The "Team" collision, and how a user reaches this page at all

Two different objects are both called "Team":

* the **page** above (roles/assignments), and
* the **donor Team groups** — `components/layout/Sider/TeamSiderSection.tsx` (327 lines: create team modal,
  pin, rename, archive). **It is never mounted**: `Sider/index.tsx` does not import it, and passes
  `afterPinnedContent={<></>}` where the team slot used to be. Its create path is therefore dead code, and
  `/team/:id` redirects away.

That means the *only* way a user reaches `/team/*` is through Settings entries labelled **Agents** and
**Team roles** (`SettingsSider`, ids `agent` and `skills`) — which redirect to `/team/roster` and, in doing so,
break the Settings shell (see `04_SIDEBAR_AND_NAVIGATION.md`). Team has no entry in the primary sidebar
(`KelNavEntries` = Work, Projects, Permissions, Transcription).

**Recommended coherent model:**

* Primary nav: keep **Work, Projects, Permissions, Transcription**.
* Settings → replace the two entries `Agents` and `Team roles` with **one** entry, **Team**, that stays inside
  the Settings shell and does not eject the sidebar.
* Retire the word "Agent" from user-facing copy until agents are creatable. "Specialist" is good and already
  used consistently for a working role instance — keep it.
* Delete or wire up `TeamSiderSection`; today it is dead code that costs maintenance and misleads anyone
  reading the sidebar implementation.
