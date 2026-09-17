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

## Precedence

- **Commit truth is authoritative over prose or status metadata.** Repository state, remote refs,
  and frozen-release hashes always override what a status file claims when they disagree.
- A gate result is accepted only when its status file matches the requested range/HEAD, states an
  explicit verdict, and reports no production writes and no writes to the Main worktree.

## Preserved rules

All existing ownership rules, worktree isolation, frozen-release immutability, stop conditions and
autonomous coordination behavior remain in force; this document adds only the watch cadence and
clarifies polling discipline.
