# KEL V2.0 — DECISIONS

Meaningful product/architecture decisions, newest first. Each one records the decision, the reason, and
what it forbids so a later run cannot quietly undo it.

## V2-00 (setup)

1. **V2 is a worktree of the existing repository, not a clone.** `C:\Users\Nick\Desktop\Kel\kel-v2` is a
   worktree on branch `dev/v2` of the shared object database in `Kel-Repo\.git`, based exactly on
   `a471e17ac25590369e74824ebed0dd7b54e4b00b`. *Reason:* one history, no duplicate object database, and
   `dev/daily-driver` stays untouched as the predecessor line. *Forbids:* clones, manual copies, a second
   object database, any change to `main` (`5e76b21…`) or to historical refs.

2. **V2 development data and installs live outside the source trees.** Test data goes to
   `C:\Users\Nick\KelV2Runs\prepared`; the V2 candidate, when a checkpoint needs one, goes to
   `C:\Users\Nick\KelV2Candidate`. *Reason:* the stable dogfood build is in daily use and must never be
   the V2 scratch surface. *Forbids:* pointing V2 runs at `KelDogfoodCandidate` or
   `KelDogfoodRuns\prepared`, and installing a candidate per phase.

3. **Disk hygiene is a program rule, not advice.** Temporary review/audit worktrees are created only
   when isolation materially helps, and are removed once their findings are committed; obsolete
   `node_modules`/build/dist copies, duplicate installers and accumulating data roots are not allowed to
   pile up; temporary trees are recorded in `MARATHON_STATE.md`. *Reason:* the predecessor program
   accumulated >80 GB of disposable trees. *Forbids:* indefinite temporary worktrees and generated bulk
   treated as durable.

4. **"Connections" is the product term** for "Kel has credentials for this service and can use its API".
   *Forbids:* plugin marketplaces, one mini-app/database/worker/workflow system per service.

5. **Gmail and Slack are out of V2 scope.** Removed from the intended connection list by the directive.
   *Forbids:* re-adding them without a recorded decision.

6. **V2 mobile is a PWA tether, desktop may stay on.** iPhone → Remote/WebUI → Nick's desktop Kel;
   cloud Kel is V2.5 and desktop-as-execution-node is V3.0. *Forbids:* implementing cloud or V3 scopes
   during this marathon, native apps, phone uploads, camera, share sheet, push notifications.

7. **Fix Capture is done and stays as built.** Four statuses (OPEN/BATCHED/FIXED/DISMISSED), never Jira,
   never rebuilt. Its feedback is an *external* input that outranks synthetic tests and may change V2
   priorities (recorded in `DOGFOOD_FINDINGS.md`).

8. **The visual rule is absolute**: never single-side coloured borders or accent rails; use typography,
   spacing, background tone, subtle full-perimeter neutral borders, restrained icon/state differences.
   Floors: body/conversation 16px, navigation/metadata/settings 14px, code 14px; ~8px geometry.

9. **Transcription stays shared, not re-invented.** V2 keeps the single Muse path (with the credential
   read from the copied Transcriptions app) and the explicit-only practice mode; no new provider, key
   field, setup flow or migration.
