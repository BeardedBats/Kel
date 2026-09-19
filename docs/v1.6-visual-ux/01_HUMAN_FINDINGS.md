# 01 — Human Findings (the 17 reported problems, checked one by one)

Severity: **S1** blocks or misleads a normal user · **S2** major friction/credibility · **S3** moderate ·
**S4** polish. "Reproduced" = observed in the packaged app. "Source-mapped" = deterministic from code.
"Judgement" = design opinion, labelled.

---

## 1. Theme colour picker closes while interacting with it — **S2 · source-mapped + measured proxy**

**What actually happens.** `AppearanceSettings` → `AppearanceModalContent` → `ThemeColorsSection`
(`components/kel/ThemeColorsSection.tsx`). Each row renders a native `<input type="color">`
(`ThemeColorsSection.tsx:107-120`) and the whole list is keyed on a counter:

```tsx
// ThemeColorsSection.tsx:154,196-199
const [refresh, setRefresh] = useState(0);
const handleChanged = useCallback(() => setRefresh((value) => value + 1), []);
...
<div className='divide-y divide-border-2' key={`${themeId}:${refresh}`}>
  {FEATURED.map((row) => (
    <ThemeColorRow key={`${themeId}:${row.token}:${refresh}`} ... onChanged={handleChanged} />
```

and each change both bumps local state and notifies the parent:

```tsx
// ThemeColorsSection.tsx:97-101
const apply = useCallback(async (value) => {
  await setThemeOverride(activeThemeId(), token, value);
  setRev((n) => n + 1);
  onChanged?.();          // -> setRefresh -> new keys -> row subtree re-created
}, [onChanged, token]);
```

**Measured evidence.** Driving the sibling hex field on the same row (`[data-testid="theme-hex-bg-base"]`),
150 ms after the first change event: `focused: false`, `document.activeElement === BODY`, while the
override *did* apply (`--bg-base` became `#123456`). The control loses its element identity on the very
first change — the mechanism that would dismiss an OS colour dialog whose owner element is replaced.
`evidence-visual-c.json → hexField`.

**Honest limitation.** The OS colour dialog itself cannot be driven from outside the app, so the closure was
not observed directly. The two facts that stand on their own: a change event re-creates the row subtree, and
the change event immediately moves focus to `<body>`.

**Also here.** `apply()` writes config on **every** `change` event (the native picker fires continuously
while dragging), so this is also unnecessary write amplification.

**Fix direction.** Remove `refresh` from the React keys (or isolate the swatch in a non-keyed child), apply
on `change` (committed value) rather than on every `input` event, and keep the row's DOM identity stable.

---

## 2. Model/tool selection belongs in the composer, not detached at the top — **S2 · source-mapped**

The control is passed to the conversation header, not the composer:

```tsx
// pages/conversation/components/ChatConversation.tsx:443-465
const headerExtraNode = ( <div className='flex items-center gap-8px'> ...
    {modelSelector && <div className='shrink-0'>{modelSelector}</div>} ... </div> );
return ( <ChatLayout ... headerExtra={headerExtraNode} ...> );
```

`modelSelector` renders `KelModelPill`, `KelToolsControl`, `KelMemoryProposalControl`
(`ChatConversation.tsx:395-403`). So the three controls a user reaches while *composing* sit in the window
title/header strip, far from the text they affect. Mobile already moved model choice into the composer's
`+` sheet (`ChatConversation.tsx:373-374`), which is the pattern the desktop should follow.

**Fix direction.** Move the pill/tools/memory controls into the composer row (SendBox), keeping the header
for the conversation title. Keep the invisible `AcpModelSelector` warm-up mount where it is for readiness.

---

## 3. Settings navigation unexpectedly falls back into the main application sidebar — **S1 · reproduced**

**Reproduced output** (`evidence-visual-b.json → settingsNav`, and `evidence-visual-a.json → settingsNav`):

```
#/settings/appearance  hasSettingsSider: true   hasMainNavWork: false
#/team/roster          hasSettingsSider: false  hasMainNavWork: true     <-- clicked "Agents"
#/team/roster          hasSettingsSider: false  hasMainNavWork: true     <-- clicked "Team roles"
#/autonomy             hasSettingsSider: false  hasMainNavWork: true     <-- clicked "Tools"
```

**Root cause.** `Sider` swaps the sidebar by URL prefix only — `pathname.startsWith('/settings')`
(`components/layout/Sider/index.tsx:44`). But the settings sider still advertises entries whose routes
redirect *outside* that prefix (`components/layout/Router.tsx:113-140`):

| Settings entry (label the user sees) | Route | Redirects to |
|---|---|---|
| Agents | `/settings/agent` | `/team/roster` |
| Team roles | `/settings/skills` | `/team/roster` |
| (legacy) Assistants / Capabilities / Skills hub | `/settings/assistants`, `/settings/capabilities`, `/settings/skills-hub` | `/team/roster` |
| Tools | `/settings/tools` | `/autonomy` |

`SettingsSider` still builds menu items for `agent`, `skills` and `tools`
(`pages/settings/components/SettingsSider.tsx:34-40, 88-110`). The user is in Settings, clicks a Settings
row, and the Settings sidebar is replaced by Work/Projects/Permissions/Transcription with no transition or
explanation. There is no back affordance to Settings other than the footer row.

**Fix direction.** Either keep those destinations inside the Settings shell (render the Team/Tools surfaces
at `/settings/team-roles`, `/settings/tools`) or remove/rename the settings rows so no Settings entry
navigates out of `/settings`. Preference: **name the destination, don't silently teleport** — if Team roles
lives in Team, the Settings row should say "Team roles → opens Team", or the page should move.

---

## 4. Dark-mode readability problems — **S2 · measured**

Measured WCAG ratios (all below the AA threshold for their size; `evidence-visual-a.json`):

| Surface | Text | px | Ratio | Need |
|---|---|---|---|---|
| Transcription (light) | "Folders", "Recent Transcriptions" | 12 | **3.24** | 4.5 |
| Transcription (light) | "Group recordings into folders…", "Nothing here yet.", "Practice mode" | 11 | **3.24** | 4.5 |
| Transcription (dark) | "Source" (the key/settings entry point) | 12 | **2.21** | 4.5 |
| Settings → Appearance (light) | "Light" / "Dark" / "Follow System" theme-card labels | 13 | **1.06** | 4.5 |
| Settings → Appearance (both) | "Reset" (colour override) | 14 | 1.7 / **2.13** | 4.5 |
| Settings → Model | "Needs setup" chip | 11 | **2.92** | 4.5 |
| Settings → System | "Back up now" (a **button**) | 14 | **1.23** | 4.5 |
| Settings → System | "Restore from this backup" | 14 | **1.5** | 4.5 |
| Settings → System | "Clear" | 14 | 3.25 | 4.5 |

Contrast failures are **not** in the Kel token system — Work/Projects/Permissions/Team/Providers/Diagnostics
measured **zero** offenders in both themes. They are in donor surfaces that never adopted the Kel palette,
plus the theme gallery's white-on-light preview labels. Details and the mechanism in
`08_DARK_LIGHT_READABILITY.md`.

---

## 5. Hover actions overlap conversation titles — **S2 · reproduced and measured**

```
hover = { rowHeight: 34, rowRight: 252, nameRight: 236, actionLeft: 224, actionWidth: 20,
          overlapPx: 12, rowPaddingRight: "16px" }
```
(`evidence-visual-c.json → hover`)

**Root cause.** `ConversationRow` reserves 16px for its end actions (`pe-16px`,
`GroupedHistory/ConversationRow.tsx:206`) but the action cluster is absolutely positioned at `end-8px` and
is 20px wide (`ConversationRow.tsx:314-318, 370-377`) — occupying 28px. The title's flex box therefore
extends 12px underneath the button. Short titles are unaffected; any title long enough to fill the
available width is covered on hover, exactly when the user is trying to read it.

**Fix direction.** Reserve the real action width (`pe-28px`/`pe-32px`, or a hover-revealed gutter with a
fade mask), so the title ellipsises *before* the button instead of under it.

---

## 6. Transcription UI diverged too far from the standalone Transcriptions app — **S2 · source-mapped**

Full comparison in `06_TRANSCRIPTION.md`. Summary of the divergence: the left column lost its
`Transcriptions` title and its `API Key` entry (replaced by a bottom-of-column `Source` text button that
measures 2.21:1 in dark), section titles became `FOLDERS` / `RECENT TRANSCRIPTIONS`, the main action row
moved to the **top-left** and reordered to `Record · Upload Audio` (donor: `Upload Audio · Record More ·
Record`, right-aligned), the transcript title is 16px body weight with a `Rename` button, and the action
footer grew from 4 actions to **8** (Copy, Download Transcript, Download Audio, Combine with…, Send to chat,
Use as vetting answers, Think out loud, Delete) inside a bordered top rule. Both columns are wrapped in
bordered rounded "cards" over a page background, where the donor used full-height panel surfaces.

---

## 7. Permissions is too technical and too large — **S2 · measured + source-mapped**

Measured text volume per surface (characters of visible text): **Permissions 3,615** · System 2,285 ·
Diagnostics 1,851 · Providers 1,775 · Appearance 695 · **Work 605** · Transcription 401 · Projects 383 ·
Team 333. Permissions is the single most text-heavy surface in the product — **6× Work, 11× Team**.

On screen it contains: `Reload` and `Emergency stop` side by side in the header; a three-line paragraph
explaining emergency stop; "Capability leases" (columns `Job · State · Review · Expires · Scope` showing raw
job ids, `review_ref` values and `kind: value` scope strings); "Boundary requests" with each request wrapped
in a **nested card** (a `kel-card` inside a `kel-card`, `pages/kel/autonomy/index.tsx:190`); "Ask the engine
about a scope" — a policy-checker debug tool with kind tabs (write/repo/browser/tool/destructive), a target
input and an `Ask the engine` button; and "Locked guardrails · digest <12 hex chars>" with `kel-code` test
identifiers. Copy such as *"Issue a lease first; the check needs a scope to test against."* is engine jargon
in a user-facing sentence.

---

## 8. Projects is too vague/large — **S1 (mis-titled, not merely vague) · source-mapped**

`/projects` → `Navigate to /projects/knowledge` → `pages/kel/projects/index.tsx`, which reads
`kelWork('main')` and shows tabs **Knowledge / Map / Recipes** for a single implicit project. The header
renders literally:

> `Projects` — *"General · 0 knowledge records · map — · 5 recipes"*

There is no project list, no project switcher, no way to create or open a project. Meanwhile the **sidebar**
"Projects" section is a different concept entirely (workspace folders — see `04_SIDEBAR_AND_NAVIGATION.md`).
So the same word labels two unrelated things, and the page a user expects (their projects) does not exist.
Confirmed live: `textHead` for `#/projects/knowledge` begins `Projects General · 0 knowledge records · map — · 5 recipes`.

---

## 9. Work is too card-heavy and oversized — **S2 · measured + source-mapped**

The page renders **four stacked bordered cards** unconditionally (`pages/kel/work/index.tsx:150-330`):
`Jobs`, `Verification — …`, `Waiting to continue`, `Team assignments`. Two of them render their empty state
*inside* a card, so a single sentence is framed by two nested rounded rectangles (`kel-card` border 1px +
radius 10 + pad 24 → `kel-empty` dashed border + radius 10 + pad 32).

Font histogram for Work (`evidence-visual-a.json → work`): `{14:127, 16:438, 24:35, 32:4, 48:1}` — 438
characters at 16px body, 3 card headings at 24px, one 32px page title, on a page whose total information
content is one sentence.

---

## 10. Sparse information at enormous visual scale — **S2 · measured**

The scale comes from the token layer, not from individual components: `--kel-type-h1: 32px`,
`--kel-type-h2: 24px`, `--kel-type-body: 16px`, `--kel-space-4: 24px` card padding,
`--kel-space-5/6: 32/48px` page padding, `--kel-gutter: 32px`
(`renderer/styles/kel-tokens.css:51-74`). A desktop app shell with a ~250px sidebar renders an empty
"Waiting to continue" card at 24px heading inside 24px padding and 24px gaps. Projects is the clearest case:
`map —` and `0 knowledge records` occupy a 32px page title with an 8-character 32px heading above a 24px
card heading above a 16px sentence.

---

## 11. New Chat should create a temporary conversation immediately and remove it if abandoned empty — **S3 · reproduced; the premise is wrong**

`New Chat` → `handleNewChat` → `navigate('/guid', { state: { resetAssistant: true } })`
(`components/layout/Sider/index.tsx:54-66`). Measured on a populated profile: `rowsBefore: 5`,
`clicked: true`, `hashAfterClick: '#/guid'`, `rowsAfterClick: 5`, `afterRoundTrip: 5`
(`evidence-visual-c.json → newChat`).

**So nothing is created.** There is no optimistic conversation and therefore nothing to garbage-collect.
The user's *intent* (New Chat should feel like it started something real) is still unmet — the composer
opens with no conversational identity, and the first message is what creates the thread. That is a legitimate
design choice, but it is the opposite of what the user asked for, so it needs an explicit decision rather
than a silent fix. **Recommendation: keep the current behaviour** (no empty conversation is better than a
conversation that must be swept up) and instead make the empty composer read as a real starting point.

---

## 12. Empty abandoned conversations remain in the sidebar — **S2 · reproduced (different cause than #11)**

The engine store in the audited profile holds **9 conversations, 6 of them with zero messages** (including
`main`); the sidebar rendered 5 rows, two of which show the generic robot leading icon and correspond to
seed/empty threads (`evidence-visual-c.json → sidebar.inventory`; store query in
`C:\Users\Nick\Desktop\Kel\ux-audit\visual\dbprobe.py` output).

So empty conversations are not created by New Chat — they exist because something created a conversation
row without content (work/`main` conversations, seeding paths, an aborted first send). The sidebar lists
them with the same weight as real conversations.

**Fix direction.** Decide the rule once: either filter message-less conversations out of the sidebar, or mark
them visually as empty drafts. `reconcileHistory.ts` is the place where engine history becomes sidebar rows.

---

## 13. Conversation robot/agent icons may be redundant — **S3 · source-mapped + measured**

`ConversationRow.renderLeadingIcon` → `resolveConversationLeadingMark`
(`pages/conversation/utils/conversationAssistantIdentity.ts:71-129`) resolves in this order: preset-assistant
emoji → assistant avatar → **`assistant_fallback` (a generic `Robot` icon)** → backend logo → generic
`MessageOne` icon. Measured on a real sidebar: **2 of 5 rows render `i-icon-robot`**, 3 render a round
backend logo image.

In Kel's stated one-assistant framing (`docs/v1.5/11_DESIGN_SYSTEM.md`: "the normal conversation does not
expose model, worker, provider, or agent selection"), the leading mark distinguishes nothing for a normal
chat: it is either the same backend logo on every row or a generic robot/message glyph. It costs 22px of
row width on every row and competes with the unread dot and the hover actions.

**Fix direction.** Keep the mark only where it carries information (an actual different assistant/backend,
or a cron/waiting/generating state that already replaces it). Otherwise drop the leading slot and keep the
row to title + state.

---

## 14. Project/folder semantics are unclear — **S1 · source-mapped**

Three different things are called "project":

| Name in UI | What it is in the code | Where |
|---|---|---|
| Sidebar **Projects** section | workspace groups — a filesystem workspace + its conversations | `GroupedHistory/index.tsx:221-238,416-420` |
| Sidebar **Projects** nav entry (`/projects`) | the single engine project (`project_id: 'default'`, displayed as "General") knowledge/map/recipes console | `pages/kel/projects/index.tsx` |
| `conversation.project_id` | an engine project id used to host the preview panel | `ChatConversation.tsx:229` |

Groups in the sidebar are not user-created folders: they materialise from `workspaceGroup` data, and the
only per-group affordances are expand/collapse, "start a new conversation here" and archive. There is no
"create folder", no rename, no drag-to-move. Full inventory and recommendation in
`04_SIDEBAR_AND_NAVIGATION.md`.

---

## 15. Add Agent / agent management is not discoverable or may not exist — **S2 · source-mapped**

**It does not exist as user-facing creation.** The Team page's only creation path is seeding built-in role
templates (`kelTeam.seed()`), and `kelApi.ts` exposes no create/define/update-role call — only
`office`, `roster`, `seed`, `role`, `history`, `rollback`, `timeline` (`components/kel/kelApi.ts:331-352`).
Studio renders role fields as **read-only text** with a "Locked guardrails — read-only" card and an
append-only version history whose only mutation is rollback (`pages/kel/team/index.tsx:280-350`).

The donor team-creation UI still exists in source (`TeamSiderSection.tsx`, including
`TeamCreateModal` and pin/rename/archive) but **is never mounted** — nothing imports it (`grep -rn
TeamSiderSection` finds only its own definition), and the donor team route is hard-disabled
(`Router.tsx:61` `HIDE_DONOR_AGENT_SURFACES = true`, route `/team/:id` → `Navigate to '/guid'`).

**Defect found while checking this:** in the Office empty state the button labelled **"Seed the default
roster"** calls only `load()` — it can never seed (`pages/kel/team/index.tsx:191-196`). The Roster empty
state calls `kelTeam.seed().then(load)` correctly (`:236-240`). A button that promises an action and does
nothing.

---

## 16. Raw engine errors such as `TypeError: fetch failed` appear in user-facing surfaces — **S1 · reproduced**

Every Kel page passes the raw JS error straight into user copy:

```tsx
// pages/kel/work/index.tsx:55-60
setError({ cause: err instanceof Error ? err.message : 'The engine did not answer.',
           fix: 'Check that the Kel engine is running, then press Reload.' });
```

Same pattern at `projects/index.tsx:50`, `autonomy/index.tsx:58`, `team/index.tsx:81`,
`diagnostics/index.tsx:70`, `providers/index.tsx:76`, `onboarding/index.tsx:75`; and into action notes
(`setNote(`${label} failed: ${...}`)`) at `work:73`, `projects:67`, `autonomy:75`, `providers:91,108,125`.

Reproduced output (`evidence-visual-b.json → engineLoss`), captured verbatim:

```
Work could not be loaded / TypeError: fetch failed / Fix: Check that the Kel engine is running, then press Reload.
Project context could not be loaded / TypeError: fetch failed
Autonomy state could not be loaded / TypeError: fetch failed
Kel could not read the team state / TypeError: fetch failed
Kel could not load the transcript library / TypeError: fetch failed
```

Note also that on Work the error card renders **alongside** the empty-state cards ("Nothing waiting to
continue.", "No specialist has been assigned yet."), so the page simultaneously says "failed" and "nothing
here", which is worse than either alone.

---

## 17. Several engine-dependent screens failed on ordinary launch — **S1 · reproduced with a stated trigger**

**Reproduced:** with the app running and the engine process stopped, all five engine screens show the errors
in item 16 (screenshots `b-030-engine-lost-*.png`). **On a clean launch the engine is fine:** two independent
fresh launches spawned `KelEngine.exe`, wrote `desktop-session.json` (`http://127.0.0.1:50850/`, pid 31296),
and produced **0 console errors and 0 error surfaces across 23 inspected surfaces**.

So this is **not** a deterministic fresh-launch race, and not a stale build. The product defect is the
absence of engine supervision: `initializeKel` validates the descriptor once at boot (`/api/state`), spawns
if needed with a 45s deadline, and thereafter **never re-checks, never re-spawns, and never degrades
gracefully** (`process/services/kel/KelService.ts:23-122`). Any later engine exit — crash, a second instance
quitting and calling `/api/shutdown-idle`, a stale descriptor, a locked database file — leaves a live window
whose every engine request fails with a raw JS error and a "press Reload" instruction that cannot work.

Full mechanism, ranked causes and the fix list: `09_ERROR_STATES.md`.

---

## Severity roll-up

| Sev | Items |
|---|---|
| **S1** | 3 (settings nav leaves the shell) · 8 (Projects is not projects) · 14 (three meanings of "project") · 16 (raw engine errors) · 17 (no engine supervision) |
| **S2** | 1 (picker) · 2 (model/tool placement) · 4 (readability) · 5 (hover overlap) · 6 (transcription divergence) · 7 (Permissions) · 9 (Work cards) · 10 (visual scale) · 12 (empty conversations) · 15 (no agent creation + dead seed button) |
| **S3** | 11 (New Chat premise) · 13 (leading icons) |
| **S4** | — |

**Corrections to the reported list, for the record:** #11's premise is wrong (nothing is created, so nothing
needs removing) and #12's cause is not New Chat. #13 is real but milder than stated — the icon is not
meaningless, it is *undifferentiated* for normal chats. #5 is real and measurable but only bites titles long
enough to fill the row. #4 is not a Kel-palette problem; it is a donor-surface problem.
