# Memory proposals — UI and copy

## Chat pill (`KelMemoryProposalControl`)

Renders only when pending proposals exist for this conversation's project. Label: `Review · N`.
Background-refreshes every 8 s; disappears when the queue empties (also right after an action).
Clicking opens the review card in a popover. `data-testid`: `kel-memory-pill`, `kel-memory-more`
("and N more waiting for review in Work").

## Review card (`MemoryProposalReview`)

Used in the popover and in the Work panel (same component). `data-testid`: `kel-memory-proposal`,
`kel-memory-current`, `kel-memory-proposed`, `kel-memory-why`, `kel-memory-accept`, `kel-memory-reject`,
`kel-memory-defer`, `kel-memory-details`, `kel-memory-details-body`.

Copy inventory (Kel-native English; no donor locale keys — the release program's locale pass owns
translations, same call as the session-tools control):

| Element | Copy |
| --- | --- |
| Headline (vetting) | Kel thinks this project decision changed. |
| Headline (conflict) | Two saved choices disagree. |
| Headline (stale) | This knowledge may be out of date. |
| Headline (other) | The project files suggest an update. / Kel suggests updating saved knowledge. |
| Labels | Current / Proposed / Why: <one sentence> |
| Actions | Accept / Reject / Defer / Review details |
| Accept toast | Updated what this project knows. (chat) · Saved knowledge updated. (Work) |
| Reject toast | Kel will keep things as they are. · Kept what was saved. |
| Defer toast | Postponed — Kel will not ask again until something changes. |
| Details | What this would change (old → becomes → new), Why, Where it came from ("Your latest Design Vetting decisions", "Two saved choices in this project", "The file README.md changed", "The state of the project"), and "Nothing changes about this project's saved knowledge until you accept." |

No ids, topics, trust numbers, kinds or runtime words appear in the card; the details modal explains
provenance in words only.

## Work panel (`KelWorkPanel`, Project knowledge tab)

- Waiting for review: pending + deferred proposals, each a full review card (`data-testid`:
  `kel-work-proposal`), above the records list.
- Records list: unchanged (confirm / edit / retract / forget).
- What changed: the plain-language history (`kel-memory-history-entry` / `kel-memory-history-empty`),
  loaded when the drawer opens and refreshed after each decision. Replaces nothing — the raw open
  conflicts block stays for pre-existing conflicts that have no review item.
