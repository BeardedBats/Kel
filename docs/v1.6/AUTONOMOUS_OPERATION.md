# Autonomous Main — dependency watch and coordination cadence

Adopted 2026-09-17; supersedes any previous slower waiting cadence for Main 1.6.

## Dependency watch cadence

When Main is blocked **only** on another Kel program thread or an independent gate:

1. Re-read the relevant authoritative status file **every 30 seconds**.
2. Never poll faster than 30 seconds (no hot-looping); slower only when the bounded check
   justifies it.
3. Stop polling that dependency **immediately** when the required state/change is detected, and
   resume autonomous work.
4. Do not poll while useful independent work can proceed, unless the dependency check remains
   safely bounded (a single file read per bounded interval).
5. Nick is never required to wake the thread or relay a result manually.

## Authoritative status sources

| Thread / gate | Status file |
|---|---|
| Independent code Audit 1.6 | `C:\Users\Nick\Desktop\Kel\kel-v16-code-audit\docs\code-audit\AUDIT_STATUS.md` |
| Visual UX program | `C:\Users\Nick\Desktop\Kel\kel-v16-visual-audit\docs\v1.6-visual-ux\VISUAL_STATUS.md` |
| Main (this thread) | `docs/v1.6/status/MAIN_STATUS.md` (in the Main worktree) |

## Visual readiness is orthogonal to Main's state

Main's global `state` field describes **Main's own activity only** (e.g. `IMPLEMENTING` while Phase 5.0
proceeds). It never represents Visual readiness, and no consumer may infer Visual readiness from it.
Visual readiness lives in its own fields in `MAIN_STATUS.md`:

```
visual_state: NOT_READY | READY_FOR_VISUAL | IMPLEMENTING | READY_FOR_INTEGRATION | INTEGRATED | VERIFYING | COMPLETE | BLOCKED
visual_clean_head: <commit or NONE>
visual_required: true | false
```

Field meanings:

- `visual_state: READY_FOR_VISUAL` — Main has published a clean checkpoint and Visual is cleared to
  begin. Main may simultaneously be `IMPLEMENTING` on unrelated work.
- `visual_state: IMPLEMENTING` — set by the Visual thread once it is working from `visual_clean_head`.
- `visual_state: READY_FOR_INTEGRATION` — Visual finished a batch and its commits are ready to bring
  into Main; Main integrates them (never a force update).
- `visual_state: INTEGRATED` / `VERIFYING` / `COMPLETE` — integration done / verification running /
  closed.
- `NOT_READY` — no clean checkpoint exists; `visual_clean_head` must be `NONE`. `BLOCKED` — Visual
  cannot proceed (reason must be recorded).

**Gate — Visual may begin only when BOTH hold:**

1. `visual_state: READY_FOR_VISUAL`, and
2. `visual_clean_head` is a valid, clean, non-`NONE` commit (exists, is reachable from the integration
   branch, and no production file differs above it — docs-only commits may sit above it).

`visual_clean_head` is preserved exactly until repository truth shows it revoked or superseded; a
later Main HEAD does not revoke it, and Main's global `state` can never revoke it.

**Ownership protocol (no races).** Before Main edits any user-facing Workforce/desktop surface while
Visual is active, Main must read `VISUAL_STATUS.active_owned_files` and must not edit any file listed
there. Visual worktrees are never written by Main. If `visual_state` is `READY_FOR_VISUAL` or
`IMPLEMENTING`, treat the listed files as Visual-owned until Visual reports back.

**Commit truth remains authoritative over all of these fields.**

## Precedence

- **Commit truth is authoritative over prose or status metadata.** Repository state, remote refs,
  and frozen-release hashes always override what a status file claims when they disagree.
- A gate result is accepted only when its status file matches the requested range/HEAD, states an
  explicit verdict, and reports no production writes and no writes to the Main worktree.

## Disk-backed review handoffs (adopted 2026-09-17, permanent)

A large reviewer brief, artifact bundle, diff dump, test transcript or evidence corpus is **never**
emitted inline in one model message. The chat transcript is control-plane communication, not
durable evidence storage: large state lives on disk and is referenced by path.

Before each independent review, a package is written under the audit worktree
(`kel-v16-code-audit/docs/code-audit/increment-NN/`):

```
review-manifest.md   increment id, base/target commits, requested range, requirement refs,
                     changed files, status files, artifact paths, carry-forward findings,
                     explicit reviewer questions, verdict schema
requirements.md      verbatim requirement extracts (never a paraphrase by the implementer)
changed-files.txt
diff-01-core.patch   split by semantic section, never by arbitrary token chunk
diff-02-tests.patch
test-focused.txt  test-full.txt  collect-results.txt  demo-evidence.txt
carry-forward.md
```

Rules:

1. The reviewer receives only the manifest path, the exact commits/range, and the instruction to
   read the referenced artifacts from disk. Artifact contents are never duplicated into the prompt.
2. Reviewer output is bounded: verdict, confidence per axis, findings (blockers/majors first) with
   exact evidence references, a closure table, and explicit "not verified" limitations. Detailed
   analysis goes to the audit record on disk (`NN_..._AUDIT_DETAIL.md`), not into the conversation.
3. An artifact that is itself too large is split into bounded files by semantic section.
4. When the reviewer child cannot write (read-only tool policy), the Program Director persists the
   reviewer's returned schema to the disk detail file so the review still lands in the record.
5. A model **output-length limit is not a human stop condition**: stop expanding prose, persist the
   remaining material to disk, continue execution from those artifacts, and do not terminate the
   autonomous program because a response would be long.
6. Recovery: if a reviewer child completed while the parent response truncated, recover its result
   from disk or child state instead of re-running it.

## Preserved rules

All existing ownership rules, worktree isolation, frozen-release immutability, stop conditions and
autonomous coordination behavior remain in force; this document adds only the watch cadence and
clarifies polling discipline.
