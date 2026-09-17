# V1.6 GitHub synchronization policy (adopted for autonomous Main operation)

Adopted from the external policy prepared during the 2026-09-17 synchronization
(`ux-audit/github-sync-recon/05_PERMANENT_SYNC_POLICY.md`; execution evidence in
`06_EXECUTION_RESULT.md` / `07_REMOTE_VERIFICATION.md`). Repository:
`https://github.com/BeardedBats/Kel` (public). Integration branch `ux/v15-journeys`; stable branch
`main`.

## Non-negotiable invariants

1. **Publication is never verification.** A push records that work exists; acceptance stays with the
   project's own gates and the independent review relays.
2. **Never publish dirty WIP.** Publication requires a clean worktree and a committed checkpoint.
   Uncommitted or stashed work is never transmitted; `refs/stash` is permanently local-only.
3. **No history rewrite, ever.** No `--force`, no `--force-with-lease`, no `+refspec`, no
   rebase-onto-published-history, no tag moves. A refused push is a correct outcome to diagnose.
4. **Explicit refspecs only.** Every push names each destination ref fully. `git push --all`,
   `--tags`, `--mirror` and bare `git push` are forbidden.
5. **Frozen releases are immutable.** Published release tags are never moved, deleted, or
   re-annotated; a correction is a new tag.
6. **Public-safety scan is a gate.** Anything newly published must pass a history-aware
   secret/private-artifact scan over the complete transmitted range before the push.

## Integration branch (development checkpoints)

Publish a clean, verified, committed checkpoint on `ux/v15-journeys`:

```
git push origin refs/heads/ux/v15-journeys:refs/heads/ux/v15-journeys
```

Never publish a dirty worktree, a mid-verification commit, or a scratch/worker/audit branch.

## Checkpoint tags

Push the exact annotated tag object by name and identity
(`git push origin refs/tags/<tag>:refs/tags/<tag>`), only when `git cat-file -t` is `tag`, the
`(tag object SHA, peeled commit SHA)` pair is recorded, the remote does not hold a different object
under that name, and the tagged tree passed the public-safety scan. A published checkpoint tag is
immutable.

## Stable release (`main`)

`main` advances only by fast-forward to a verified, frozen stable release commit whose annotated tag
is published in the same operation window, after an ancestry check
(`git merge-base --is-ancestor origin/main <target>`). If ancestry fails, stop — never force. `main`
must never carry unfinished development from the next version.

## Temporary branches

Audit, scratch, worker, spike and experimental branches stay local. A branch whose tip is not inside
the published integration range is, by default, not published.

## Public-safety scan

History-aware over the transmitted range (`<current-remote-tip>..<new-tip>` per ref): provider/API
keys, tokens, credentials, private keys, `.env` contents, credential stores, cookies/session state,
local databases, personal transcripts, backups/diagnostics, private URLs, accidental binaries and
files deleted later but still in history. Findings classify as `CONFIRMED_SECRET` /
`PRIVATE_ARTIFACT` / `PUBLIC_SAFE` / `FALSE_POSITIVE` / `NEEDS_REVIEW`; `CONFIRMED_SECRET` or a new
`PRIVATE_ARTIFACT` blocks the push. The scanner never rewrites history.

## Post-publication verification

Re-fetch and confirm exact SHAs: every intended ref holds its intended SHA, no other ref moved, none
was deleted, no force occurred, and frozen refs are byte-identical to their recorded identities.
Publication is not done until the remote has been re-read.

## Recording

Each publication records, outside the production worktree (`ux-audit/github-sync-recon/`): the exact
command sequence, refs before/after by SHA, the scan result for the transmitted range, and the
no-force / no-frozen-change confirmations.
