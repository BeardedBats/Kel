# Kel motion language

**Status:** approved by Nick (D-78, 2026-09-29) and built into the renderer (stage 2, §11). Later rules
from Nick are §2.1 (the settling fade) and §8.1 (no layout shift); D-79 simplified the detail panel.
**Prototype:** `C:\Users\Nick\Desktop\Kel\Tools\motion\kel-motion-prototype.html` (outside Git; rebuilt by
`Tools\motion\src\build.py`). Every moment below is a live, clickable demo there. The page has a
reduced-motion switch and a ×4 slow-motion switch. Key-frame contact sheets are in `Tools\motion\keyframes\`.

Kel's interface should move the way good physical objects do. One element changes into the next rather
than being swapped. It settles on a spring with only a trace of overshoot. It never makes Nick wait for
information. Motion explains where something came from and where it went. It is never decoration.

Today almost nothing in the Kel shell or the work cards animates. Cards, the detail panel, the done
card, the scoping collapse, menus and new sidebar rows all mount and unmount instantly, and progress
fills and state colours jump. The only motion is two loops on the Thinking indicator, a few 120–200 ms
hover and rotate transitions, and Arco's own dropdown and toast animations. This document replaces all
of that with one system.

---

## 1. Springs

All movement uses closed-form damped springs. A value at time *t* is computed from a formula, not
stepped frame by frame, so it is exact, frame-rate independent and interruptible. An interrupted
spring re-seeds from its current position **and velocity**, so retargeting mid-flight never jolts.

A preset is written as a perceptual **duration** and a **bounce** (bounce = 1 − damping ratio ζ). For
mass 1, stiffness *k* = (2π / duration)² and damping *c* = 2ζ·√k.

| Preset | Duration / bounce | Stiffness *k* | Damping *c* | ζ | Overshoot | Settles (0.2%) | Use |
|---|---|---|---|---|---|---|---|
| `micro` | 0.22 s / 0.10 | 815.7 | 51.41 | 0.90 | 0.15% | 229 ms | press, hover, check and icon swaps, leading edge of indicators |
| `snappy` | 0.34 s / 0.18 | 341.5 | 30.31 | 0.82 | 1.1% | 450 ms | indicators, chips, menus, rows, sibling FLIPs, label rolls |
| `morph` | 0.48 s / 0.15 | 171.3 | 22.25 | 0.85 | 0.6% | 617 ms | shared-element morphs (card ↔ panel, tile ↔ menu, section ↔ line) |
| `gentle` | 0.62 s / 0.10 | 102.7 | 18.24 | 0.90 | 0.15% | 642 ms | long travel: the hand-off flight, sidebar list shifts |

Rules:
- **Overshoot never exceeds about 1%.** Nick kept the tiny overshoot (D-78). Nothing bounces visibly. The overshoot only makes an element feel
  like it arrived rather than stopped.
- A value that changes target several times keeps one spring and is retargeted, which is the same as summing one
  spring per change. It is never restarted from rest.
- Where CSS must do the work (hover, `:active`, `aria-*` state), the same presets are exported as CSS
  `linear()` easings sampled from the closed form, with the matching duration. Example, `snappy` at 16
  points: `linear(0, 0.1015 6.3%, 0.3045 12.5%, 0.5147 18.8%, 0.6906 25%, 0.8206 31.3%, 0.9079 37.5%,
  0.9615 43.8%, 0.9912 50%, 1.0055 56.3%, 1.0105 62.5%, 1.0108 68.8%, 1.0090 75%, 1.0067 81.3%, 1.0045
  87.5%, 1.0027 93.8%, 1)` over 450 ms. The library generates these strings; they are never typed by hand.
- The existing tokens `--kel-ease`, `--kel-dur-state` and `--kel-dur-enter` (`kel-tokens.css:83-85`) are
  replaced by `--kel-spring-{micro,snappy,morph,gentle}` plus `--kel-spring-*-ms`.

## 2. Durations (the non-spring parts)

Opacity and blur are timed tweens, never springs, because a fade cannot overshoot.

| What | Duration | Curve |
|---|---|---|
| Content **exit** | 110–130 ms | ease-in (cubic) |
| Content **enter** | 180–220 ms | ease-out (cubic) |
| Stagger between siblings | 25–40 ms each, **capped at 200 ms total** | — |
| Surface colour change during a morph | 240 ms, starting 30 ms after the move | ease-out |
| Backdrop in / out | 200 ms / 200 ms (out starts 80 ms late) | ease-out / ease-in |
| Toast stay | 2.6 s, then exit 140 ms | — |
| Reduced-motion cross-fade | 100 ms out, 140–150 ms in | linear |
| **Settling fade** (§2.1), token `--kel-settle-ms` / `MOTION.settleMs` | **520 ms**, opacity plus a 3 px blur-to-sharp | ease-out (cubic) |
| Settling fade under reduced motion | 360 ms, opacity only | linear |

### 2.1 The settling fade (Nick, 2026-09-29)

When something changes state in the same place, it never snaps. When the new state is **both** the
resting end of its chain **and** will stay on screen for more than about five seconds, it arrives with the
longer **settling fade**: 520 ms, eased out, opacity plus a 3 px blur clearing to sharp. Intermediate
states, and anything gone within five seconds, keep the quicker enter (§4). Reduced motion keeps a
gentle 360 ms cross-fade for it, never an instant swap.

It applies to: a card reaching Done, Failed or Stopped (label, icon, finish time, the remove ×); the
done check; "Complete" (was "Done and checked") on the result card; "You answered: … · Kel is
continuing"; the scoping summary after Start; the Staff fallback note; the last step's tick;
"Undone — the earlier files are back."; the Review Team's Passed or Failed. It does not apply to
Working → In review, a middle step's tick, Thinking, a toast (gone in 2.6 s) or a menu opening. The
rule is code: `classifyTransition({ final, staysMs })` in `renderer/motion/settling.ts`, with DOM tests.

The whole of any transition, from the trigger to the last element settling, stays under about 650 ms.
The only exceptions are the reply streaming in and the hand-off flight (about 900 ms, because it
crosses the window).

## 3. The shared-element morph (the core pattern)

When one thing becomes another, **one surface travels**. It is never a cross-fade between two boxes and
never a cut.

1. **Measure** box A (source) and box B (destination, laid out in its final place but hidden).
2. **Surface.** One out-of-flow element starts exactly on A with A's fill, border and radius. Its
   geometry is `translate(x, y)` plus width, height and radius, each on its own spring. It sits in an
   overlay layer with `contain: strict`, so writing its size lays out nothing else.
3. **A's content leaves first** (exit, 110 ms). Its container has already started moving, so the eye
   follows the container.
4. **The surface morphs** to B's box: position, size, radius, fill and border colour. Edges can ride
   different presets so the shape stretches. When a card drops into its panel, for example, width
   uses `morph` and height uses `gentle`, so it widens first and then falls open.
5. **B's content enters** 110–150 ms after the move starts, while the surface is still travelling. Its
   blocks are staggered in reading order. Content is anchored at its final size inside the surface and
   clipped by it, so text never reflows or overlaps.
6. **Hand-over.** Within 0.3 px of B, the surface removes itself and the real B appears in the same
   pixels. B stays hidden until then, even when B already exists (closing back into a card or tile).
   The surface carries B's content in on the way.

**Accent elements move; they never fade in from dark.** A blue status dot, a check, a "Now" label, a
picked chip's gradient or a selection highlight travels, stretches or grows from the pressed point.
Navy never cross-fades to the accent.

## 4. Enter and exit choreography

- Content enters **after** its container starts moving and leaves **before** the next move.
- **Enter:** opacity 0→1, blur 6 px→0 and translateY 6 px→0 over 200 ms ease-out, staggered.
- **Exit:** opacity →0, blur →4 px and translateY →−4 px over 110–130 ms ease-in, all at once (exits never
  stagger).
- **Label swaps roll.** The old words leave upward and the new ones arrive from below (7 px, blur 3 px).
  If the width changes, the neighbours FLIP to their new places on `snappy`.
- **Icon swaps:** the old icon shrinks to 0.4 and blurs out (110 ms); the new one grows from 0.5. A check
  **draws on** (stroke-dashoffset, 240–260 ms, ease-out).
- **In-flow inserts:** the new element takes its full size in one layout pass. Its siblings FLIP from
  their old places with transforms. The new element reveals from an edge with a clip-path spring
  (top edge for cards, leading edge for one-line rows), and its content enters as above.
- **Removals** are the reverse: content exits, then siblings FLIP into the gap.

## 5. Blur

Blur is only a transition aid, never a resting style.
- Entering content: 6 px → 0. Exiting content: 0 → 4 px. Rolling labels: 3 px. Streamed words: 3 px.
- Popovers opening: 4 px → 0 on the whole panel during the first 140 ms.
- Blur is never applied to the Kel logo (canonical-logo rule), to a surface's own fill, or to anything
  at rest.

## 6. Indicators that stretch

Every selection highlight and progress fill has **two edges on two springs**. The leading edge (toward
the target) rides `micro`; the trailing edge rides `snappy` and starts 30–35 ms later. The indicator
stretches toward its new place and the tail catches up. This applies to:
- tab and segmented indicators (horizontal edges);
- list selection (Settings nav, sidebar current chat, the project menu's highlighted row: vertical edges);
- progress fills. The fill's right edge follows on `gentle` while a slightly brighter **lead segment** runs
  ahead on `micro` and then collapses into it. When the state colour changes, the new colour sweeps in
  from the left as a clip-path edge on `snappy`, over the old fill. Colour arrives by moving.

Indicators are drawn with transforms or clip-path on one element that spans the track. The selected
row's own background and border (`aria-current`, `.is-picked`, `[aria-selected]`) become that one moving
element, so there is never a second, fading highlight.

## 7. Reduced motion

When `prefers-reduced-motion: reduce` is set (or Kel's own setting, if one is added):
- **Cross-fades only.** Nothing moves, scales, stretches, flies or blurs.
- A morph becomes: A fades out (100 ms) while B fades in, in place (150 ms, starting 60 ms later).
- Indicators blink across: out 70 ms at the old place, in 110 ms at the new.
- FLIPs are skipped; siblings simply take their new places.
- Checks appear drawn; labels swap with a 140 ms fade; streamed words appear without blur.
- The Thinking indicator is static (already true today: `kel-shell.css:4042-4044`).
- The existing global kill-switches (`kel-tokens.css:173-178`, `kel-shell.css:455-456`) stay as the
  backstop, but the JS library must check the media query itself, because it does not use CSS
  transitions.

## 8. Performance

- Animate only `transform`, `opacity`, `filter` and `clip-path`. The single exception is the morph
  surface, whose width, height and radius are written each frame. It is out of flow and has
  `contain: strict`, so no other element lays out.
- **Measure once, then only write.** All `getBoundingClientRect` reads happen before a transition starts
  (FLIP "first" and "last"). The per-frame loop never reads layout.
- One `requestAnimationFrame` loop drives every spring. Surfaces get `will-change: transform` only while
  moving.
- Target 60 fps at 1440×900 on Nick's PC. At most one blur layer per element, radius 6 px or less.
- Streaming text must not re-run enter animations on words already shown (animate only the new chunk).
- Polling re-renders (the card row every 3–30 s) must not replay entrances. Motion is keyed to real
  state changes (new id, new state, new step), never to a re-render.

### 8.1 No layout shift; nothing changes after the motion settles (Nick, 2026-09-29, hard rule)

1. **Final layout first.** The final layout (size, words, line positions) exists before the animation
   starts; motion only carries the eye from the old to the new (FLIP or a morph). An element never
   reaches its final size and then re-lays out or swaps its words.
2. **Words change inside the motion.** A title or label change is a roll or cross-fade of old and new in
   the same slot, already sized to the new words (`RollText`). It never happens after the container
   settles.
3. **Rows own their parts.** Icons, ticks and loaders are drawn in their own row from the first frame, in
   a fixed slot (`SwapIn`); only their state animates (opacity, scale, draw). Nothing moves between rows
   — so a step's "Now" no longer flies to the next row: the finished row's "Now" rolls away in place
   and the next row's "Now" rolls in, in the same beat (§10.5).
4. **Reserve space.** Fixed icon slots (the card's and the line's 16 px lead in every state), stable line
   heights, one-line steps.
5. **Checked mechanically.** `renderer/motion/layoutProbe.ts` records the boxes and words of key
   elements on every frame of a capture: after a transition ends nothing may move by more than 1 px or
   re-word; during it, a frame-to-frame jump much larger than its neighbours is a snap. The capture
   script (`Tools\motion\capture-app.ts`) runs it on all fifteen moments in the packaged app.

## 9. Where motion is forbidden

- **Never delay information Nick needs.** State changes, errors, questions and results appear at once.
  Motion decorates their arrival and never gates it. No choreography waits for a previous animation
  before showing new data. If new state arrives mid-transition, the springs retarget.
- **Nothing loops forever except the Thinking indicator.** No pulsing work dots, spinning step
  loaders, breathing buttons or shimmer placeholders. This also means the existing
  `.sendbox-stop-button.bg-animate` breathe and `.kel-work-card__mark--active` pulse should be retired
  or limited.
- No motion on typing, scrolling, text selection or window resize. When the card row reflows on resize
  (`ResizeObserver`), it snaps.
- No motion on first paint of a page or chat; entrances are for things that arrive while Nick watches.
- Errors never shake or bounce; they arrive like any other content.
- Never animate the Kel logo's colour or shape. It may move, scale uniformly and fade.

---

## 10. Kel's moments

Each moment names the real component and classes, what exists today, and the proposed motion.

### 10.1 Sending a message → Thinking → the reply
*Today:* the user row is pushed into `MessageList` instantly, `KelThinkingIndicator`
(`.kel-thinking`, directly above the composer) mounts and unmounts instantly, and replies grow in
~150 ms chunks with no transition (D-75.1).
1. **Send:** the send button presses (`micro` to 0.94). The sent words themselves fly from the composer
   input to their place as Nick's message (`gentle` on x, `morph` on y, a gentle arc). Their colour moves
   from primary to the user-message warm `#f2d4a6` over 360 ms. The time "9:12 AM" enters. The
   placeholder returns. Earlier messages FLIP up (`snappy`).
2. **Thinking** enters above the composer as an in-flow insert, with the mark, "Thinking…" and "0s"
   staggered 40 ms. Its pulse and shimmer are the one permitted loop.
3. **Reply:** "Thinking…" and the seconds exit (110 ms). The **mark flies** from the Thinking row to the
   new message's avatar slot (`morph` x, `gentle` y) and stops pulsing. The row collapses while messages
   FLIP. The time enters. Words **stream**: each ~150 ms chunk fades in out of a 3 px blur (180 ms,
   25 ms stagger), with no vertical movement so the lines never jiggle.

### 10.2 The hand-off
*Today:* the in-thread `KelWorkCard` shows "Getting started…" and then swaps to `KelWorkLine` (`.kel-wl`)
instantly. The top row (`KelWorkCardRow`) picks up the new card on its next poll (up to 30 s when idle)
and pops it in.
1. The line reveals from its leading edge (clip-path, `morph`). Its parts enter in order: lead dot,
   "Handed to the team", title, state, pointer, chevron (25 ms stagger).
2. After a beat (~400 ms) **the card lifts out of the line**. A surface starts on the line with the line's
   fill and radius 8, flies up (`gentle` x, `morph` y), and becomes the new `.kel-wc--row` card in slot 1
   (radius 10, card fill). The line's content leaves; the card's title, bar and state row enter
   mid-flight.
3. The **blue working dot flies separately** (`gentle` x, `snappy` y) and lands as the card's status dot.
   This is the accent moving between states.
4. The row makes room. Existing cards FLIP right (`snappy`). If a card no longer fits, **it morphs into
   the "+N more" tile** (card surface → tile surface), and the tile's label and dots enter.
5. The line re-forms in the thread 160 ms after the card leaves it, as the one-line pointer ("— follow it
   above", chevron up).
*Needs from the app:* an immediate row refresh on hand-off (`refreshWorkCards()`), because a 30 s wait
breaks the shared element.

### 10.3 Clicking a work card: card ↔ detail panel
*Today:* the backdrop (`.kel-wc-backdrop`) and `KelOfficeDetail` (`.kel-wd` in `.kel-wc-detail-slot`)
mount and unmount instantly.
- **Open:** the backdrop fades in (200 ms). A surface starts on the card with the card's look and
  **grows into the panel**: x, y and width on `morph`, height on `gentle`, radius 10→12, fill to the
  panel's `rgba(11,26,61,.97)`, border to `rgba(221,233,255,.5)`, and the panel shadow. The card's
  content exits at once. From 120 ms the panel's blocks enter in reading order, 40 ms apart: head,
  (needs-you section), progress, Team, Steps, Review and checks, footer. The card underneath takes
  `.is-selected` as the surface leaves it.
- **Close** (outside click, Esc, or the card again): the panel content exits together (100 ms). The
  surface **shrinks back into the card** (width on `snappy`, height on `morph`) and carries the card's
  content in on the way. The card is hidden until the surface lands. `.is-selected` clears on landing.
  The backdrop fades out, starting 80 ms after close.
- **Switching** from one card to another closes into the first card, then opens from the second.

### 10.4 Card state changes (working → in review → needs you → done)
*Today:* the class `kel-wc--{state}` flips and every colour jumps.
- **Label rolls** (`.kel-wc-state-label`: old up and out, new up and in). Neighbours FLIP if the width
  changes. The count rolls the same way ("2 of 5" → "4 of 5").
- **Icon swaps:** the status dot shrinks out and the new dot grows in. For **done**, the dot shrinks and
  the green check (`icon-check.svg` path) **draws on**.
- **Colour moves:** the new state colour sweeps along the progress track from the left as a new fill
  (clip-path edge on `snappy`). The old fill is removed once covered. Nothing cross-fades blue to amber.
- **Avatar rings** (`.kel-wc-avatar--{tone}`) change left to right, 45 ms apart, each with a
  `snappy` 1.12 scale pulse.
- **Done:** the avatars exit (scale 0.6, blur), and the finish time and the remove × enter.
- The detail header (`.kel-wd-state`) and the in-thread line (`.kel-wl__state`) do the same on their own
  labels and icons at the same moment.

### 10.5 Progress bars and step ticks
- The fill's **right edge follows on `gentle`** while a brighter lead segment runs ahead on `micro` and
  collapses into it. The bar stretches edge by edge instead of growing linearly.
- **Step tick** (`.kel-wd-step`): the finished row's loader shrinks out and its check draws on (260 ms).
  **"Now" moves down** to the next row — by §8.1, not as a flight: each row owns its words, so the
  finished row's "Now" rolls away and the next row's "Now" rolls in, in the same beat. The next row's
  lead grows in as the loader (turning once) and its label gains weight; "Next" appears one row further
  down. The header meta ("Step 2 of 5") and the card's own count and bar roll or stretch in the same
  beat. (D-79 removed the per-step times and the Steps "1 of 5", so the finished row's slot empties.)
- The loader turns **once** when its step starts (D-78), then stays static. It never spins forever (§9).
- The last step's tick is a resting end state: it settles (§2.1).

### 10.6 A "Needs you" answer sent from the card
*Today:* on success, `.kel-na` is swapped for `.kel-na-answered` instantly, and the card updates on the
next poll.
1. **Picking a chip:** the chip presses (`micro`). The primary gradient **grows from the press point**
   (clip-path circle, `snappy`), then `.is-picked` takes over. Navy never fades to blue.
2. **Send** presses. The section's content exits. **The question section's surface morphs into the
   "You answered" line** (height on `morph`, amber-tinted border `rgba(252,172,81,.35)` → neutral). The
   line's parts enter: check, words, ·, mark, "Kel is continuing", time. Everything below FLIPs up, and
   the panel's own height eases down on `morph`.
3. 180 ms later, the card, the panel header and the bar change from Needs you to Working exactly as in
   10.4. The amber hands over to blue by sweeping along the bar.

### 10.7 Scoping card → Start → top card
*Today:* on Start, `.kel-sc` is swapped for `.kel-sc-collapsed` in one render, and the Scoping top card
updates on the next read.
1. Start presses. The card's content exits all at once.
2. **The scoping card's surface collapses into the one-line summary** (height on `morph`, width on
   `snappy`, radius 12→8). The messages above FLIP down into the space. "Scoped", the answers and
   "Started 9:12 AM" enter, and the check draws on.
3. From 260 ms the **top card**, which already shows "Scoping" under D-70.4, **starts**. The chat icon
   swaps to the working dot and the label rolls Scoping → Working. The track appears (the
   `kel-wc-progress--none` class is removed) and the count rolls "2 questions" → "0 of 5". The team
   avatars pop in one by one (scale 0.6→1, 60 ms apart). Then the first step's fill stretches to 1 of 5.
   (Nick's brief said "the top card appearing"; the real flow per D-70.4 already has the card, so it
   *starts* rather than appears.)

### 10.8 The result, or done card, arriving
*Today:* `KelDoneCard` (`.kel-dc`) renders `null` until its first read, then appears instantly.
1. The top card goes to Done (10.4, check draws on). In the thread, the line's dot becomes a check. Its
   state rolls "In review · 4 of 5" → "Done and checked" and its pointer rolls to "— result below". Its
   chevron turns from up to down (`snappy`).
2. Kel's result message arrives as a reply (10.1; no Thinking row, because the engine posts it).
3. The **done card unfolds from its top edge** (clip-path bottom inset on `morph`). The messages above
   FLIP up. Its rows enter in order, 40 ms apart: head (the check draws on), result sentence, "Applied
   to Mic mute app · 2 files · you can undo it", then actions.

### 10.9 Undo (as changed by D-79)
*D-79 removed the Undo buttons from the panel and the done card; Nick asks Kel instead.* What remains is
the moment the files come back: the applied line **rolls** to "Undone — the earlier files are back."
with the settling fade (§2.1). "Open" (the project folder) stays. The notes below describe the
prototype's Undo button and are kept for reference only.
*Today:* the buttons dim to 0.55 while busy. Afterwards Undo and Open folder vanish and the applied line
reads "Undone — the earlier files are back." (`changeApplication.ts:53`). There is no toast and no
confirmation.
- Undo presses. Its arrow **turns once**, −360° on `gentle` (not a loop; it runs while the request is
  in flight, up to one turn). The buttons take the busy state.
- On success, the applied line **rolls** to "Undone — the earlier files are back." Undo and Open folder
  step away (scale 0.92 + blur, 120 ms), and "Details" FLIPs to its place.
- On failure, `.kel-dc__notice` enters like any content. Nothing shakes.

### 10.10 The overflow "+N more" menu
*Today:* `.kel-wc-menu` mounts instantly, and the chevron rotates 180° over 120 ms.
- **Open:** the tile takes `.is-open` and its chevron turns on `snappy`. **The menu grows out of the tile**,
  from the tile's surface (radius 10, tile fill) to the menu's (radius 10, panel fill, lit border), with
  height on `gentle`. The "Running" and "Finished" labels and the menu cards enter, 30 ms apart.
- **Close:** the menu content exits, and the surface **folds back into the tile**, carrying the tile's
  label and dots in. The chevron points down again.

### 10.11 Segmented controls and tab indicators
None have a moving indicator today; selection is an instant background swap.
- **Model picker scope tabs** ("This chat" / "Kel's model", `.kel-desktop-model-menu__scope`): the amber
  pill `rgba(255,183,100,.08)` is one element whose left and right edges ride §6's springs. The text
  colour moves to `#ffb764` over 160 ms. The same applies to the **workspace tabs** (`.kel-workspace-tabs`).
- **Settings nav** (`.kel-in-chat-frame__nav-row[aria-current]`): the selected background and border
  become one vertical indicator whose top and bottom edges stretch between rows. When the page swaps,
  the old pane exits (120 ms, −6 px, blur) and the new one enters (220 ms, 8 px, blur).
- **Checklist filters:** *no checklist filters exist in the renderer.* The closest real tabs are
  **Kibble's status tabs** (`.kel-tabs`/`.kel-tab`: Open · Batched · Fixed · Dismissed) and the Recipe
  filters (`.kel-recipe-desktop-tabs`). They get the same stretching indicator. Their list contents
  exit and re-enter shifted 16 px toward the direction of travel.

### 10.12 The project switcher dropdown
*Today:* the header menu (`.kel-desktop-picker.kel-workspace-menu`) and the composer's project picker
(`.kel-desktop-project-menu`) mount instantly with no motion. The chevron snaps to 180°.
- **Open:** the chevron turns (`snappy`). The popover **grows from its trigger's corner** (scale
  0.94→1 on `snappy`, 140 ms fade, 4 px blur clearing). Its rows enter 18 ms apart.
- **Pick:** the pressed-row highlight (`aria-pressed`) stretches to the new row (§6), and **the check
  travels** to it (`snappy`). Then the menu closes (120 ms: opacity, scale 0.97, 3 px blur). The
  breadcrumb label **rolls** to the new project name, and the chevron FLIPs.
- The same grammar covers the model picker, which today uses Arco's `slideDynamicOrigin` (scaleY 0.9,
  200 ms). That animation is replaced so all of Kel's popovers move alike.

### 10.13 Toasts
*Today:* Arco `Message`, re-skinned and placed at the bottom centre (`bottom: 120px`), with Arco's own
fade in (100 ms linear) and fade and height out (300 ms).
- **Enter:** rises 10 px out of a 6 px blur and scale 0.96 (220 ms). Toasts already showing FLIP up to
  make room (`snappy`).
- **Exit:** after 2.6 s, opacity, 4 px blur and scale 0.97 over 140 ms. The others FLIP into the gap.
- This is implemented by overriding Arco's `fadeMessage` keyframes with the shared easing, rather than
  building a second toast system.

### 10.14 A new chat appearing in the sidebar
*Today:* the row (`.chat-history__item.conversation-item`) appears at the top of Recent instantly.
- New Chat presses. The rows below **FLIP down** (`gentle`, so the list settles calmly). The new row
  enters from 8 px to the left out of a 5 px blur.
- **The selection travels.** The `aria-current` background and border stretch from the previous chat
  (even across the Pinned and Recent sections) to the new row (§6).
- The chat area swaps: the thread exits (120 ms), and the title and empty state ("Kel", "Hi! Tell me what
  you need and I'll get started.") enter.

### 10.15 The Staff & models fallback note
*Today:* `p.kel-staff-row__last` ("Fell back to {ran} last time (asked for {asked}): {why}.", amber
12 px) renders or doesn't. It never animates. The work-card detail's "Asked for X · ran Y" in
`.kel-wd-model` is the same.
- The rows below FLIP down (`snappy`) while the note enters from −4 px out of a 6 px blur (220 ms). If
  the model line changes at the same time, it rolls.

---

## 11. Stage 2: what was built

As built (2026-09-29), in `desktop/packages/desktop/src/renderer/motion/`:
- `spring.ts` — the closed-form solver, presets, `spring()` handles that retarget with velocity,
  `tween()`, one `requestAnimationFrame` loop that runs only while something moves and batches writes
  (`frameWrite`), and `motionClock` (manual stepping for tests and captures; `window.__kelMotion`).
- `easing.ts` — `linear()` easings and `--kel-spring-{micro,snappy,morph,gentle}(-ms)` written at startup.
- `reduced.ts` — `useReducedMotion()` / `isReducedMotion()` from the OS setting only (D-78).
- `fx.ts` — enter, exit, `settleIn` (§2.1), draw-on, press, `turnOnce`, pulse, the chip bloom; one
  running effect per element, taken over from its current opacity when interrupted.
- `flip.ts` — `useFlip(ref, key)` (measures during render, before React touches the DOM; plays after
  commit; resizes snap) and `glide()` for the thread following new content.
- `morph.ts` — the surface, `morph()`, `morphInto()`, `fly()`, exit ghosts, shared elements.
- `indicator.ts` + `EdgePill` — the two-spring indicator (transform plus its own size, `contain: strict`).
- `components.tsx` — `RollText`, `SwapIn`, `ProgressFill`, `useEntrance`, `EdgePill`.
- `popover.ts`, `messageArrival.ts`, `streamFade.ts` (Custom Highlight API; no DOM is wrapped),
  `arrival.ts` (first-paint guard, scenes marked by the layout), `settling.ts`, `layoutProbe.ts`.
- The row's choreography is `components/kel/workCards/workCardMotion.ts`.

The original plan follows.

A small renderer library, `renderer/motion/`:
- `spring.ts`: the closed-form solver, presets, retargeting with velocity, and `settle()`.
- `easing.ts`: generates the `linear()` strings and durations. It also writes the `--kel-spring-*`
  custom properties once at startup.
- `useSharedMorph` / `morph()`: the §3 surface in a portal overlay. FLIP measure once, write-only per
  frame, clone-free content handover (render B's React subtree into the surface).
- `useFlip(listRef, key)`: sibling FLIP keyed to real ids, so polling re-renders never replay.
- `EdgeIndicator`: a two-spring indicator with clip-path.
- `useReducedMotion()`: reads the media query and switches every helper to §7.
- No new dependency. React 19.1 and Arco 2.66 are enough, and nothing like Framer Motion is needed.

The prototype's `kel-motion.js` is the reference implementation of the solver, the surface, FLIP, the
edge indicator and the reduced-motion path.

## 12. Questions for Nick (answered 2026-09-29, D-78)

Answers: keep the tiny overshoot; the hand-off waits ~0.4 s; a step's loader turns once when the step
starts; Kibble's tabs are fine as the filter example; reduced motion follows the Windows setting only.
The original questions:

1. **Overshoot:** 0.15–1.1% (as prototyped). Is that "tiny" enough, or should the presets be fully
   critically damped?
2. **Hand-off timing:** the flight waits ~400 ms after the line appears. Is that long enough to read
   "Handed to the team", or should it wait longer?
3. **"Now" loader:** it stays static per the no-loop rule. Is a single turn when a step starts wanted?
4. **Kibble tabs** stand in for "checklist filters". Was a different control meant?
5. **App-level reduced-motion switch** in Settings → Appearance, in addition to the OS setting?
