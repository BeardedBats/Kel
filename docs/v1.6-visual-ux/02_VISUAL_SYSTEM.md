# 02 — Visual System: current state vs the stated Kel V1.6 direction

Source of truth today: `desktop/packages/desktop/src/renderer/styles/kel-tokens.css` (429 lines).
It is genuinely good work — one token file, one focus ring, a global reduced-motion fallback, a skip link,
and it measures **AA-clean on every Kel page in both themes** (see `08`). The problem is not its quality; it is
its **reach** and its **scale**.

## 2.1 There are two design languages in the product

| Language | Consumed by | Variable family | Radii seen |
|---|---|---|---|
| **Kel "Desk"** | `pages/kel/**` (Work, Projects, Permissions, Team, Transcription shell), `components/kel/**` | `--kel-*` | 10px card, 8px control, 999px chip |
| **Donor / Arco** | sidebar, chat, settings shell, appearance, system, transcription internals, dialogs | `--color-*`, `--bg-*`, `--fill-*`, `text-t-*` | 6px, 7px, 8px, 12px, 16px |

Evidence of the split:

* `components/layout/Sider/SiderNav/KelNavEntries.tsx:47` — the primary nav uses Arco utilities
  (`h-34px`, `rd-8px`, `text-t-primary`, `bg-fill-3`), not Kel tokens.
* `pages/kel/transcription/index.module.css` — the transcription page uses `--color-border-2`, `--color-bg-2`,
  `--color-text-3`, `--color-fill-1/2`, `--color-primary-light-*` (donor), **never** `--kel-*`.
* `components/settings/SettingsModal/contents/AppearanceModalContent/index.tsx:73,82,109` — settings blocks are
  `bg-2 rd-16px`.
* `components/kel/ThemeColorsSection.tsx:190` and `components/kel/KelDataCard.tsx:32` — even *Kel*-owned
  components adopt the donor `bg-2 rd-16px` block instead of `--kel-radius-*`.

**Measured consequence:** six distinct radii are in live use — **6, 7, 8, 10, 12, 16px** (plus pills). The user's
direction asks for *approximately 8px* button radius. Today the "New Chat" button measures **7px**
(`shell-1440-light.png`; DOM `border-radius: 7px`), Kel buttons 8px, Kel cards 10px, theme cards 12px, settings
blocks 16px, colour swatch 6px.

## 2.2 Direction → gap, one line each

| Direction (user) | Current | Verdict |
|---|---|---|
| dim navy / bluer slate-navy foundation | dark = `#101418 / #161b22 / #1c232c` — near-neutral charcoal with a faint blue cast | **Needs shift** to a deliberate bluer slate-navy |
| slightly off-white primary text | dark text-1 `#e6edf3` | Close (slightly cool white) — keep, do not go pure `#fff` |
| restrained pale sky/red/orange/pink/green/purple, semantic use | accent is a **saturated** green `#2fa37c`; chips pair *three* colour signals per chip | **Needs restraint** (see 2.4) |
| avoid rainbow visual noise | Kel pages: 6 chip variants × (bg + fg + dot) + dashed borders | **Violated in chips** |
| compact controls | h1 **32px**, body **16px**, rows 44px, card pad 24px, page padding 32/48px | **Violated** — see 2.3 |
| ~8px button radius | 6/7/8/10/12/16px in use | **Needs one rule** |
| strongly reduce rectangles/cards | `KelCard` + `KelSection` wrap every block; cards nested inside cards; empty states inside cards | **Violated** — see 2.5 |
| never a card merely because information exists | `KelSection` is *always* a card; Work renders 4 cards unconditionally | **Violated** |
| typography/spacing/dividers/hierarchy/disclosure first | partly there (`.kel-divider`, `.kel-meta`) but always inside a bordered box | **Partially met** |
| no single-side coloured accent borders | only instance is a blockquote rule (`styles/markdown.css:81`) | **Met — keep it** |
| normal assistant prose not in cards | chat renders assistant rows full-width (`MessageList.tsx:158` skeleton `bubbleWidth: '100%'`), user rows 78–84% | **Met in chat** |
| special interaction cards only for meaningful structure | approvals cards (Phase 3) + `KelCard` everywhere | **Partially met** |
| hover-reveal secondary actions | already the pattern (conversation rows, project rows, section "+") | **Met — keep** |

## 2.3 Scale is the single biggest visual problem

Measured per surface (`evidence-visual-a.json`, font-size histogram = characters rendered at each px):

| Surface | 11px | 12px | 13px | 14px | 16px | 24px | 32px | Total chars | Reading |
|---|---|---|---|---|---|---|---|---|---|
| Work | 0 | 0 | 0 | 127 | **438** | 35 | 4 | 605 | sparse content, large type |
| Projects | 0 | 42 | 0 | 146 | 168 | 18 | 8 | 383 | same |
| Team (office) | 0 | 21 | 0 | 162 | 139 | 6 | 4 | 333 | same |
| Team (roster) | 0 | 6 | 0 | 162 | 96 | 6 | 4 | 275 | same |
| Transcription | **89** | 34 | 0 | 248 | 29 | 0 | 0 | 401 | uneven |
| Settings · Appearance | 0 | 177 | 128 | 386 | 3 | 0 | 0 | 695 | donor scale |
| Settings · Model | 171 | 0 | 434 | 233 | 23 | 22 | 0 | 884 | donor scale |
| Providers | 0 | 280 | 0 | 449 | **878** | 158 | 9 | 1775 | large |
| Diagnostics | 0 | 279 | 0 | 1088 | 386 | 86 | 11 | 1851 | large |
| Settings · System | 0 | **1259** | 416 | 582 | 3 | 24 | 0 | 2285 | dense small |
| **Permissions** | 0 | 255 | 0 | **2037** | 1210 | 101 | 11 | **3615** | **largest, most technical** |

So: **Permissions renders 6× the text of Work and 13× Team**, at 12–16px, on a 32px-titled page with 48px of
bottom padding. The pages with the least information (Work, Team, Projects) are laid out at the largest scale;
the page with the most information (Permissions) is the least scannable. That is the "sparse information at
enormous visual scale" complaint, quantified.

Concrete cause: `--kel-type-h1: 32px`, `--kel-type-h2: 24px`, `--kel-type-body: 16px`, `--kel-gutter: 32px`,
`--kel-space-5/6: 32/48px`, `--kel-card-pad: 24px`, `--kel-row-height: 44px`. Those are marketing-web values
applied inside a desktop shell with a ~250px sidebar.

## 2.4 Status chips carry three colour signals

`components/kel/KelPrimitives.tsx:23-30,49-56` + `kel-tokens.css` render, per chip: a tinted **background**, a
coloured **text**, and a coloured **dot** — plus a dashed border for `uncertain` and a red border for `blocked`.
Seven states (`running, waiting, verified, uncertain, failed, blocked, queued`) × 3 signals = visual noise that
competes with the accent colour, and the copy inside them is a sentence, not a state
("Uncertain — needs evidence", "Failed — see cause", "Blocked by guardrail").

**Proposed:** one signal (a 6px dot or a single-colour text), the state word in plain language, and the
explanatory clause moved out of the chip into the row's meta line. Reserve the tinted pill for the two states
that actually need attention (`waiting`, `failed`).

## 2.5 Card policy (the biggest structural change)

Today: `KelCard` = bordered + shadowed + 24px padding + 10px radius; `KelSection` = *always* a card; `KelEmpty`
= dashed bordered box with 32px padding. Consequences seen in source:

* Work renders **four** cards unconditionally, two of which contain only an empty state
  (`pages/kel/work/index.tsx:146-330`).
* Permissions nests a `.kel-card` **inside** another `.kel-card` for each boundary request
  (`pages/kel/autonomy/index.tsx:174`).
* Work nests `KelSection` (a card) inside a `KelCard` for the receipt (`pages/kel/work/index.tsx:296`).
* Empty states are rendered *inside* cards, so a single sentence is drawn inside two nested rectangles.

**Proposed rule set (to be encoded in `kel-tokens.css` and the primitives):**

1. A page has **one** primary surface. Everything else is typography + dividers.
2. `.kel-card` is reserved for *interactive or self-contained* content (a form, a receipt, an approval). A list
   or table is **not** a card — it gets a section heading and dividers.
3. **No nesting.** `.kel-card` inside `.kel-card` is forbidden; use a divider and a label.
4. Empty states never render inside a card, and never render two nested boxes: empty = one line of muted text
   plus, at most, one quiet action.
5. A section that is empty is **not rendered at all** on a page whose whole purpose is that section; on a
   mixed page it collapses to a single line.
6. Shadows: keep `--kel-shadow-card` only for surfaces that float (menus, popovers, modals). Flat pages get
   borders only, or nothing.

## 2.6 Proposed token changes (concrete)

```css
/* Suggested direction — dim navy / bluer slate-navy. Values are proposals, to be judged on screen. */
[data-theme='dark'] {
  --kel-surface-0: #0f1620;   /* app background: slate-navy, not charcoal */
  --kel-surface-1: #16202c;   /* panels */
  --kel-surface-2: #1d2a38;   /* raised / hover */
  --kel-border:    #26374a;
  --kel-border-strong: #35485f;
  --kel-text-1:    #e9eef5;   /* slightly off-white, cool, never #fff */
  --kel-text-2:    #a7b6c8;
  --kel-text-3:    #7f8fa3;
  --kel-accent:    #6ea8d8;   /* restrained pale sky — replaces saturated green as the primary accent */
  --kel-accent-soft: #16283a;
  --kel-accent-ink: #0f1620;  /* text sitting ON the accent */
}

/* Scale: desktop-app scale, not marketing scale */
:root {
  --kel-type-h1: 24px;   /* was 32 */
  --kel-type-h2: 16px;   /* was 24 — card headings should read as labels, not headlines */
  --kel-type-body: 15px; /* was 16 */
  --kel-space-5: 24px;   /* was 32 */
  --kel-space-6: 32px;   /* was 48 */
  --kel-gutter: 24px;    /* was 32 */
  --kel-card-pad: 16px;  /* was 24 */
  --kel-row-height: 36px;/* was 44 */
  --kel-radius-card: 8px;/* was 10 — one radius for surfaces and controls */
}
```

**Semantic accent use.** The direction asks for restrained pale sky/red/orange/pink/green/purple *used
semantically*. Proposed mapping, with pale (not saturated) values in both themes:

| Meaning | Token | Use |
|---|---|---|
| neutral / informational | sky `--kel-accent` | links, quiet buttons, selected tab underline |
| needs you | orange | `waiting` chip, the one attention colour |
| failed / destructive | red | `failed`, destructive buttons (text-coloured, not filled) |
| verified | green | `verified` chip only |
| blocked by rule | purple | `blocked` chip only |
| uncertain | pink/amber | `uncertain` |

Red/orange/green/purple should appear as **text or a dot**, and be filled only when they are the primary action
on that surface (e.g. "Emergency stop" confirmation, "Allow once" in an approval).

## 2.7 Radii — one rule

* Controls (buttons, inputs, rows, tabs): **8px**.
* Surfaces (cards, panels, modals): **8px**. Menus/popovers may use 10px.
* Chips/pills: 999px (unchanged) **or** 8px — but not both across surfaces.
* Retire 6px, 7px, 12px, 16px from the product. The 16px settings blocks
  (`AppearanceModalContent`, `ThemeColorsSection`, `KelDataCard`) become 8px and lose the `bg-2` fill in favour
  of a section heading + divider.

## 2.8 What to keep (do not regress)

* `kel-tokens.css` single-file token discipline; components must not hard-code values.
* The global focus ring (`:where(a, button, …):focus-visible`) — verified present.
* `.kel-skip` skip link as the first tab stop on every Kel surface.
* The global `prefers-reduced-motion` fallback.
* The AA-clean text/border pairs measured in `08_DARK_LIGHT_READABILITY.md`.
* Hover-reveal for secondary row actions (fix the geometry, keep the pattern).
* The blockquote's `border-inline-start` — it is semantic, not decorative chrome.

## 2.9 Deliverable for this section

A single `DESIGN.md` is *not* requested here; the concrete proposal is: **edit `kel-tokens.css` in place** (it is
already the designated source of truth, and its header comment still says "Direction Desk" — it should be
re-labelled to the V1.6 direction), then migrate the donor-language surfaces listed in 2.1 to `--kel-*` tokens
in the order given in `10_IMPLEMENTATION_OWNERSHIP.md`.
