# Design Vetting Sessions — greybox workflow

## When greyboxes appear

Some decisions are best answered visually. The visual question (`Q19` in the Product/UI template,
`visual: 1`) offers `Show greyboxes` as an inline action; the same action exists per question in the
Vetting panel and as a chat control (`show greyboxes 19`).

## Directions

`greybox_directions(question, session_traits)` produces a deterministic set of materially different
directions (typically 4–8; **never capped at three**) across four layout axes — navigation, density,
hero treatment, side rail — biased by the session's own answers (sidebar/density/opening answers move
the closest directions first). Each direction carries a name, one-sentence description, and an inline
SVG wireframe.

These are decision-support greyboxes, not final polished comps: flat tones, box structure, labels for
the major zones.

## Comparison surface

The Vetting panel renders the directions as a grid of wireframe cards (index view) and each card's
own detail is the card; the conversation links to the panel ("open the Vetting panel to compare
them"). No separate browser page is required, and the same data is available over the API
(`/api/vetting` `panel` → `greyboxes`, each with its SVG) for future surfaces.

## Feedback

Per direction: **Choose as base** · **Like this part** · **Dislike this part** (feedback rows are
recorded; likes/dislikes are notes, not decisions).

## Combining

The user can mix directions in one line, exactly as in the brief:

```
Direction 4 -> base, Direction 2 -> header, Direction 6 -> category treatment
```

`parse_combine` reads the role → number pairs; `combine_directions` resolves them against the
generated directions, merges the role traits onto the base, records the sources, and Kel generates a
new composite direction ("Composite — … + header 2") as a first-class row. The composite is itself a
candidate for Choose as base.

## Pending state

`17: make greyboxes, I'll decide later` (or the panel button) marks the question
`AWAITING_VISUAL_SELECTION`, generates the directions immediately, and **does not block the batch**:
every other question stays answerable. Choosing a base later records the answer
(`Greybox direction chosen: …`) through the same ingestion path as typed answers, so it appears in
revisions and in the decision ledger with its rationale.

## Determinism

Direction generation, SVG rendering, and composition are provider-free and deterministic: the same
answers produce the same directions. An optional model hook may enrich names/descriptions later;
nothing depends on it.
