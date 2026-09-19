# 05 — Work, Projects, Permissions

These three surfaces are the heart of “sparse information presented at enormous visual scale”, “too
card-heavy and oversized”, and “Permissions is too technical and too large”.

All three share one page shell (`styles/kel-tokens.css` → `.kel-page`): **padding 32px top / 32px sides /
48px bottom, 24px gap, `h1` at 32px, body at 16px**, then a stack of `.kel-card` sections (24px padding,
1px border, 10px radius, shadow).

## Measured text volume and type mix per surface (light theme, 1440×900)

Character counts of rendered text by font size, from `evidence-visual-a.txt`:

| Surface | 11px | 12px | 13px | 14px | 16px | 24px | 32px | Total |
|---|---|---|---|---|---|---|---|---|
| Work | – | – | – | 127 | 438 | 35 | 4 | **605** |
| Projects | – | 42 | – | 146 | 168 | 18 | 8 | **383** |
| **Permissions** | – | 255 | – | **2037** | **1210** | 101 | 11 | **3615** |
| Team (office) | – | 21 | – | 162 | 139 | 6 | 4 | 333 |
| Team (roster) | – | 6 | – | 162 | 96 | 6 | 4 | 275 |
| Providers | – | 280 | – | 449 | 878 | 158 | 9 | 1775 |
| Diagnostics | – | 279 | – | 1088 | 386 | 86 | 11 | 1851 |
| Settings · System | – | 1259 | 416 | 582 | 3 | 24 | 48→ | 2285 |
| Transcription | 89 | 34 | – | 248 | 29 | – | – | 401 |

Read that as: **Permissions renders ~3,615 characters of prose and table text — 6× Work, 11× Team** — on a
page whose only *actions* are Reload, Emergency stop, Revoke, Allow/Deny. Work and Projects are the
opposite: large type, few words. Both extremes are the same underlying mistake — the page structure is
inherited from an internal console rather than designed around a task.

Contrast note: **every one of these pages measured zero WCAG AA offenders in both themes** (the `kel-*`
tokens are AA-clean). Their problem is scale, density and vocabulary — not colour.

---

## 5.1 Work — `pages/kel/work/index.tsx` (356 lines) · S2

Structure as rendered (verified live; `evidence-visual-a.txt` → `work`):

1. `h1` “Work” (32px) + sub “0 active · 0 waiting to continue · 0 need you” + **Reload**
2. `KelErrorState` (only on failure)
3. `KelEmpty` “No unfinished work in this project.”
4. `KelCard title="Jobs"` → `KelTable`
5. `KelCard title="Verification — …"` — rendered whenever any job exists, with Pause/Resume/Cancel,
   a progress sentence, a milestone table, `note`, and a nested **`KelSection` “Receipt — …”** wrapping a
   `<pre class="kel-code">` of up to 4000 characters
6. `KelCard title="Waiting to continue"` — **always rendered**; when empty it contains a `KelEmpty`
7. `KelCard title="Team assignments"` — **always rendered**; when empty it contains a `KelEmpty`

Defects, in order of how a user feels them:

* **Four cards render unconditionally on an empty account.** Two of them contain nothing but a dashed
  `KelEmpty` box *inside* a bordered card *inside* a page — a rectangle inside a rectangle inside a page,
  for one sentence. This is the literal “never use a card merely because information exists” violation.
  *Fix:* render a card only when it has content; when a section is empty and the page is otherwise empty,
  show **one** page-level empty state that names the two ways to get work (start a task in chat; open Work
  from a running job).
* **Two of the three 24px card headings are for empty sections** (“Waiting to continue”, “Team
  assignments”). Large headings with no content read as broken rather than as calm.
  *Fix:* section headings become 14–15px labels above a divider, not `h2` at 24px.
* **An empty Work page is ~600 characters.** That is not too little information — it is too little
  information delivered at the wrong scale, with a 32px title and a 48px bottom pad.
* **Vocabulary is engine-facing:** “Jobs”, “Current step”, “Budget”, “steps used”, “Milestone”, “Worker
  state”, “Attempts”, “Checks”, “v1 · 8-char digest”, “provider / model”, “blocker”. The subtitle alone
  (“0 active · 0 waiting to continue · 0 need you”) is three numbers the user has no handle on.
* `KelMeter` is a **fixed 180px** progress bar plus “N of M steps used” inside table cells — the widest
  thing in the table, for the least important column.
* Selecting a job is invisible: `activeJob` defaults to `jobs[0]`, so the Verification card silently
  describes the first job. There is no row selection affordance.

**Direction:** Work should answer “what is happening, and does anything need me?” — a single list of work
items ordered by “needs you first”, each row one line: *what it is · what state · when · one action*. The
detail (milestones, attempts, checks, receipts) belongs behind row disclosure, and the receipt belongs
behind a disclosure control, not in a permanently rendered `<pre>`.

## 5.2 Projects — `pages/kel/projects/index.tsx` (292 lines) · S1 (mis-titled)

`/projects` renders a **single implicit project** (`project_id` defaults to `default`) with three tabs:
**Knowledge / Map / Recipes**. The header literally reads “General · 0 knowledge records · map — · 5
recipes” (`work.project_id === 'default' ? 'General' : work.project_id`).

So the nav item is labelled **Projects** but there is no project list, no project chooser, no create, and
no per-project scoping: `kelWork('main')` hard-codes the conversation and `project_id` is never chosen by
the user. What the page actually is: *the knowledge/memory console of one implicit project.*

Additional problems inside the page:

* The page title promises projects; the content delivers memory maintenance. A first-time user cannot
  reconcile them.
* `KelCard "Knowledge"` holds a **7-column table** (Topic, Type, Trust, Status, Source, Updated, Actions)
  where **every row has three buttons** — Confirm / Retract / Forget — as text buttons. That is a database
  admin grid.
* “Trust 7/10 · confirmed”, “type”, “status”, “source_type: source_ref.slice(0,28)” are internal fields.
* **Conflicts** prints raw JSON in a `<pre class="kel-code">`; **Recipes → Preview (dry run)** prints raw
  JSON too.
* Empty state copy is good (“Kel records what it learns while working — with its source and a trust
  score.”) — the *copy* is the strongest part of the page; the *structure* around it is not.

**Direction (do not delete capability):** keep Knowledge/Map/Recipes but (a) re-title the surface to what
it is, or make it genuinely project-scoped with a project chooser; (b) move per-row actions into a hover
menu with the destructive one separated; (c) render conflicts as a sentence (“2 notes disagree about X”)
with the JSON behind a “details” disclosure; (d) make trust a two-word label (“trusted / unverified”)
rather than `7/10`.

## 5.3 Permissions — `pages/kel/autonomy/index.tsx` (305 lines) · S2 (largest offender)

Rendered structure:

1. `h1` “Permissions” (32px) + “0 active permissions · 0 waiting on you”
2. **Two header buttons: `Reload` and `Emergency stop`** — a global destructive action sitting next to a
   refresh control, with no confirmation and no separation.
3. A **3-line `kel-meta` paragraph** explaining what Emergency stop does *before* anything else on the
   page. Explanation of a panic button is not the most important content on a permissions page.
4. `KelCard "Capability leases"` — table: Job / State / Review / Expires / Scope / Actions. Cells hold raw
   job ids, lowercase raw states, `review_ref` literals, and `kind: value · kind: value` scope strings
   truncated at 120 characters — on a line that already carries a `Revoke` button.
5. `KelCard "Boundary requests"` — the approval surface. Each pending request is rendered as a **nested
   `.kel-card` inside the outer `.kel-card`**, containing what/why/benefit/if-denied/risk lines and three
   buttons (Allow once / Allow for this project / Deny).
6. `KelCard "Ask the engine about a scope"` — an **engine policy checker**: kind tabs
   (`write/repo/browser/tool/destructive`), a free-text “Scope target” input, and “Ask the engine”. Above
   it, a 5-line paragraph (“The policy checker Kel exposes for a scope. It fails closed on its inputs…”).
7. `KelSection "Locked guardrails · digest <12 hex chars>"` — rule/meaning/test table with `kel-code` test
   identifiers.

Defects:

* **A developer tool is a first-class, always-visible panel** (item 6). It is the clearest example of “too
  technical”. Nothing on the page tells a user which of these five check kinds they would ever want.
* **Card-in-card** at item 5 (a bordered request box inside a bordered section box) — for a single
  approval. The pending approval is also the one thing that must be *loud*, and it is currently the most
  nested.
* **Jargon without a definition:** lease, scope, boundary request, guardrail, digest, revoke, fails closed.
  Even the empty state explains leases with a 51-word sentence
  (`Autonomy state could not be loaded` / “A lease is created only after a reviewed plan is approved…”).
* **`Emergency stop` placement** (item 2): adjacent to Reload, before any context. It is also described as
  not undoing completed effects — information a user needs *in* the confirmation, not in a paragraph above.
* **Permissions duplicates Phase 3.** Phase 3 (`85e99fb`) puts approvals in the conversation. This page
  renders the same `boundary_expansion_requests` with Allow/Deny. Two surfaces, two vocabularies, one
  decision — a user who approves in chat and then opens Permissions sees a second, differently-worded
  instance of the same thing. **This must be resolved deliberately, not left to coexist.**
* **Scope strings are the product's core promise** (“Kel only does what you allowed”) and they are the
  least readable thing on the page: `write: C:\… · repo: …`.

**Direction:** Permissions should read like a receipt of trust, not a policy console:

* Row = **one sentence**: “Kel can write files in *this project* until *4:20 pm* (you allowed this 12 min
  ago)” + one **Revoke**.
* Pending requests go **above** everything else, as the only card on the page, with plain-language
  consequences short enough to read in one glance; “Allow once / Allow for this project / Deny” stays.
* The policy checker becomes a “Why was this blocked?” detail reachable from a decision or from a job —
  not a permanent tab of buttons.
* Locked guardrails move behind “What Kel will never do” — same content, plain framing, JSON/test ids
  behind disclosure.
* Emergency stop moves into an overflow (⋯) with a confirm dialog that states the consequence plainly.
