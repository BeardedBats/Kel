# Memory proposals — product spec

## What the user gets

Important project knowledge is not silently overwritten when Kel believes it changed. Kel-detected
changes arrive as a review:

- the chat offers a quiet **Review** pill only while something is waiting;
- the card shows **Current** (what is saved), **Proposed** (what would be saved), **Why** (one plain
  sentence), and the actions **Accept / Reject / Defer** plus **Review details**;
- the Work panel's Project knowledge tab hosts the full queue and a plain-language **What changed**
  history answering "what changed in Kel's understanding of this project?".

Nothing technical is shown by default: no ids, no topics, no trust numbers in the card; the details
modal says where a proposal came from in words ("Your latest Design Vetting decisions", "Two saved
choices in this project", "The file README.md changed").

## States

PENDING → (ACCEPTED | REJECTED | DEFERRED | SUPERSEDED); DEFERRED can later be accepted or rejected.

- **Accept** applies the change through the trust model and keeps the previous value in the record's
  history chain.
- **Reject** keeps what is saved and stops the identical question from re-appearing.
- **Defer** keeps the item queued (visible in Work, quiet in chat) until the user acts.
- **Superseded** is automatic: a newer proposal for the same topic replaces older pending ones; a
  proposal whose target moved is retired instead of being applied blindly.

## Where it appears

- **Chat**: a pill (Review · N) beside the model/tools pills, only when pending items exist for this
  conversation's project; the card opens from it. Pending only — deferred items stay out of the way.
- **Work → Project knowledge**: the queue (pending + deferred), the existing records list, and What
  changed. The pill background-refreshes every 8 s, so a new proposal appears without a reload.
- **All runtimes**: the engine layer is project-scoped and runtime-independent; any surface that can
  call `/api/memory` or read `/api/work` gets the same queue.

## What it must never do

- Never change memory before an accept (reject/defer leave memory untouched).
- Never ask the same unchanged question twice after a rejection.
- Never leak across projects (cross-project leakage is a release blocker).
- Never surface low-confidence noise: proposals are generated only for the wired triggers (see
  03_TRIGGERS.md), not for wording, temporary state or ephemeral chat.
