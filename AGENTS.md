## Independent review checkpoints

Call the `request_review` tool at meaningful decision points only:
- you reached a significant new architectural conclusion
- you're about to make a consequential source change
- you're about to perform a destructive operation
- you found evidence contradicting your current plan
- you're choosing between materially different fixes
- you're about to rebuild/package/deploy
- you believe a bug is fixed
- you believe the task's acceptance criteria are satisfied
- you're about to declare the task complete

Do NOT call it for routine work: ls, grep, file reads, test polling,
ordinary shell commands.

Pass: goal, finding, evidence, next_action, files_changed, risks.

On CONTINUE: proceed.
On CHALLENGE or BLOCK, you may call request_review exactly once more for
the same checkpoint with rebuttal_evidence set. When you do, resend goal,
finding, evidence, next_action, files_changed, and risks EXACTLY as
originally submitted, unchanged -- put any new information only in
rebuttal_evidence. The relay matches a rebuttal to its original checkpoint
by hashing those six fields; reword any of them and it looks like a brand
new checkpoint with no prior review on file, so your rebuttal is rejected
as REVIEWER_UNAVAILABLE instead of being evaluated.
On BLOCK specifically: do not perform the blocked action until you've
resolved it via that one rebuttal call, or until asked to proceed anyway.
On REVIEWER_UNAVAILABLE: say so plainly and proceed with normal caution —
the review could not be performed.

## Kel source and install

- Edit the normal repository at `C:\Users\Nick\Desktop\Kel\Kel` after consolidation.
- Keep `main` synchronized with GitHub. Push each coherent commit before calling an increment complete.
- Install the current product at `C:\Users\Nick\Desktop\Kel\App`.
- Keep durable user state at `C:\Users\Nick\Desktop\Kel\Data`.
- Use `App` for normal installed checks. Use `Temp\Candidate-<short-id>` only for a bounded comparison.
- Remove each temporary candidate after its check. Never create permanent `.rXX` installs.
- Start only the stack a check needs. Stop it, close its database, and remove its test root afterward.
- Keep real data, screenshots, transcripts, and credentials out of Git.
