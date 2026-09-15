# KEL V1.4 — INTERACTION PATTERNS

Status: v1 (2026-09-15) · Companion to `KEL_V1.4_DESIGN_SYSTEM.md`. Applies to every surface, new and
inherited. Where this document and the donor shell disagree, this document wins and the donor surface
is refactored at G7/G9.

## 1. Navigation model

Primary navigation (rail): **Chat · Work · Team · Projects · Recipes · Search · Settings**.
Team: **Office · Roster · Studio** (segmented tabs). Projects: **Overview · Knowledge · Map · Work ·
Team · Recipes · Settings** (contextual tabs inside the project). Settings: General · Appearance ·
Providers · Team · Projects · Autonomy · Permissions · Memory · Notifications · Updates · Privacy ·
Diagnostics · Advanced · About.

Rules:
- A destination is visible only when its backing state exists (no dead navigation). Unavailable
  destinations render as a disabled item with a one-line reason, never an empty page.
- Full page for primary destinations; **right-side sheet** for object detail (job, specialist, role,
  approval, recipe preview) and for settings sub-forms. Never both a page and a sheet for the same
  object.
- The work drawer remains available from Chat as a glanceable companion; it mirrors the same
  components as the Work page (no separate visual language).

## 2. Global keyboard and focus

- First tab stop: “Skip to main content”. Then rail → page content → open sheet → back.
- Focus ring always visible (`design system §10`); chips/static text never tabbable.
- `Ctrl+K` command palette (navigation, actions, recent jobs); `/` focuses search in lists.
- Escape closes the top layer (sheet → dialog → drawer) and returns focus to the invoker.
- Sheets/dialogs trap focus; background is inert (`aria-hidden`), and never loses scroll position.
- No focus stealing: background updates never move focus; a job state change never opens a layer.

## 3. Dense data (tables)

- Row select → sheet detail; row actions appear on hover/focus and stay keyboard reachable.
- ≤3 filters render as pill toggles; more filters open a filter sheet with a summary chip.
- Column priority (Work Center): Job · State · Current step · Progress · Budget · Updated —
  columns drop right-to-left at narrow widths (Updated → Budget → Current step), never horizontal scroll.
- Compact density engages automatically ≤1279px and for >10 rows; both modes are screenshot-verified.
- Empty, loading (static skeletons), and error states render inside the table body.

## 4. Work lifecycle

State → primary action mapping (exactly one primary action per view):

| State | Primary action | Secondary | Copy |
|---|---|---|---|
| Running | Pause | Cancel job | “Running… step 2 of 3 · 4m” |
| Waiting on you | Review approval | Open detail | “Waiting on you — 1 decision” |
| Uncertain | Provide evidence | Open detail | “Uncertain — needs evidence” |
| Verified | Open receipt | Open artifacts | “Verified — 3 of 3 checks passed” |
| Failed | See cause | Retry (repair-only) | “Failed — see cause” |
| Blocked | See guardrail | Open scope | “Blocked by guardrail” |

- **Frozen steps**: accepted milestones show a lock glyph + `Frozen` label; they are never re-run
  (repair-only touches non-accepted steps). Timestamps + digest on hover.
- **Wait reasons**: every waiting state names why and what would unblock, in one line.
- **Recovery banner** after restart: “Work resumed after restart — 1 job continued” + evidence link;
  dismissible; never a modal.
- **Parent-child map** is a tabular indentation, not a node-graph toy; children fold inline.
- Duplicate cards for one job are impossible: one job = one row/card, updated in place.

## 5. Approvals (trust centerpiece)

Sheet anatomy, in order: what Kel wants to do (plain language) · the exact command/action in mono ·
scope chips (folder/repo/domain/tool) · expiry · **Allow once** (primary) · **Allow for project**
(secondary, states the expiry) · **Deny** (quiet) · a one-line consequence note (“If you allow, Kel
runs this once and records a receipt. Nothing else is unlocked.”). Required decisions are never
toast-only; the approval badge counts pending items. After resolution: receipt line
(“Approved by you · 11:42 · action digest 4f2a…”).

## 6. Team — Office, Roster, Studio

- **Office** shows only real assignments (job-backed). Row: specialist · role version · assignment ·
  state · elapsed · tools · budget. No decorative or fictional workers, ever.
- **Why this specialist**: one line under the row (reason + inputs considered), expandable to the
  staffing explanation; no hidden reasoning, no chain-of-thought text.
- **Activity timeline**: meaningful events only (started step, produced artifact, check failed,
  escalated), each linking to evidence; raw streams are never shown.
- **Roster vs assignments are visually distinct**: templates = neutral outline cards with an
  “Available” tag; live work = status chips and elapsed timers.
- **Studio**: structured role editor; editable vs locked sections are visually distinct (locked
  sections use a lock glyph and muted surface, never an editable-looking field); version diff +
  rollback in a sheet; model/tool/budget controls are per-role with inherited defaults shown.

## 7. Evidence and verification

- Two-step language everywhere: “Worker reported ✓” (worker result) then “Kel verified” (independent
  verification). The two are never merged into one checkmark.
- Evidence viewer: evidence class label, freshness, source digest, and link to the artifact; stale
  evidence is marked `Stale` with what invalidated it.
- Reviewer independence is shown as a badge (`independent reviewer`), with disagreement → repair loop
  visible in the job timeline.
- Completion receipt: what was done, evidence list, checks, coverage, and what was not attempted.

## 8. Memory and context

- Knowledge panel: type + trust badges (`decision · trust 2`), source links, and actions
  Confirm / Edit / Retract / Forget; conflicts render two candidates with a resolver, never an
  auto-winner.
- Recall indicator is truthful: it lists what was actually included and nothing else; empty is stated
  as “No saved project knowledge yet.”
- Context preview shows the packet, why-included reasons, size and source mix; project isolation is
  stated when relevant (`from this project only`).

## 9. Continuation

- Continue last: single candidate resumes directly; multiple candidates render a numbered chooser and
  require an explicit pick; wrong-project requests are refused with the reason and the correct project.
- Resume summary states what will continue, what is frozen, and what changed (source-changed warning
  with affected-only revalidation).
- Idempotent resume: an already-verified job refuses politely (“already verified”) and offers the
  receipt; nothing re-runs.

## 10. Recipes

Library rows (name · inputs · last run) → preview sheet with steps, required-input checklist,
permission preview, and **dry run**. Progress uses the same job state language; completed steps freeze;
retries and escalations are visible; terminal states are explicit (done / abandoned / blocked).

## 11. Providers and autonomy

- Provider cards distinguish four independent facts: installed · authenticated · healthy · quota
  (green/amber/gray/`unknown — not reported`). “Test connection” shows the probe result with latency,
  never a fake green.
- Fallback is explained when it happens (`fallback: quota exhausted → Codex`) with the exact session
  status; role model preferences have an explicit inherited/override indicator.
- Autonomy: capability lease viewer (roots · repositories · domains · tools · external actions ·
  expiry), boundary-expansion approvals use the approval sheet with **Allow once / Allow for project**,
  and locked guardrails render as locked (lock glyph + “locked by Kel’s safety policy — not editable
  here”) with a plain explanation of why.

## 12. Settings, diagnostics, notifications

- Settings use a two-pane layout with inline save (no modal confirmation for ordinary fields);
  destructive actions sit in a labelled danger section with explicit confirm + rollback note.
- Diagnostics: export produces a sanitized bundle with a visible receipt (what was included/excluded);
  health, startup timeline, provider latency, orphan detector, and DB compaction each show real
  measurements and state their limits; issue reports are drafted locally, never posted automatically.
- Notifications are restrained: interrupts only for approval-required, failed, or guardrail-blocked;
  verified/progress wait in the app. Tray + pet states reflect real engine state only; pet never
  fakes activity.

## 13. State matrix — every surface must render these states

empty · loading · populated · active work · waiting · approval required · success · uncertain ·
failed · blocked · offline · provider unavailable · no project · first run · dense content ·
long content. Wireframe copy for each comes from the status language table; review gates check that
no state is missing or indistinguishable (color-only) — evidence in the acceptance matrix.
