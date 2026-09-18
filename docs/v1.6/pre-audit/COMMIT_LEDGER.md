# COMMIT_LEDGER — production-affecting commits, audited point → PRE_AUDIT_V1_6_HEAD

updated: 2026-09-18T16:05Z
range opens at: `8a2b25d` (last independently audited production point; increment 24 CONTINUE)
range ends at: PRE_AUDIT_V1_6_HEAD (TBD; recorded at RC)
rule: EVERY production-affecting commit in this range must appear here. Docs-only commits are
listed for completeness with `priority: LOW / docs-only`.

Columns: SHA | parent | date (local) | phase | increment | intent | production files | tests |
migrations | UI? | packaged impact? | sec/privacy? | persistence? | priority | evidence | known concerns

## Commits above the audited point at corpus open (docs-only, verified per-commit)

| SHA | parent | date | intent | class | priority | evidence |
|---|---|---|---|---|---|---|
| `c4ae724` | `8a2b25d` | 2026-09-18 | Phase 5.6 remediation record + delta re-audit request | docs-only | LOW | `git show --stat` = 3 docs files |
| `5127bac` | `c4ae724` | 2026-09-18 | Phase 5.6 accepted — audit 24 CONTINUE; 5.7/5.8 decisions deferred | docs-only | LOW | `git show --stat` = 5 docs files |
| `fd98cc4` | `5127bac` | 2026-09-18 | record published integration tip; visual slice complete | docs-only | LOW | `git show --stat` = MAIN_STATUS only |

## Campaign A production commits (the intentionally-unaudited range)

| SHA | parent | date | phase | intent | production files | tests | migrations | UI? | packaged | sec/priv | persistence | priority | evidence | concerns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | *no production commit yet — the first one opens this table* | | | | | | | | | | |

## Visual branch commits pending integration (NOT covered by any independent audit)

Branch `ux/v16-visual-fix` (worktree `kel-v16-visual-fix`). These carry production changes that
have automated (79/79 vitest, tsc 0) and packaged (`package-visual5` probes a/b/c) acceptance only.
When integrated into `ux/v15-journeys` they enter the Commit Ledger range above as NEW commits
(integration commit(s) + preserved lineage), and their original SHAs remain traceable.

| SHA | date | batch | intent | production files (summary) | evidence | concerns |
|---|---|---|---|---|---|---|
| `8dd21f9` | 2026-09-17 | Batch 1 | Kel design tokens (slate-navy foundation, compact density) | renderer styles/tokens | 39/39 contrast checks; tsc 0; 76/76 | human pixel gate open |
| `3d9202c` | 2026-09-17 | Batch 2 | Settings shell: `/team/*` stays in Settings; `/settings/tools` shows Tools | settings renderer | tsc 0; 76/76 | — |
| `04151c8` | 2026-09-17 | docs | visual plan docs onto the branch | docs | — | — |
| `83af16f` | 2026-09-18 | Batch 4 | Transcription standalone IA | transcription renderer | tsc 0; 76/76 | finding 2/3 baselines pending |
| `ac85eb3` | 2026-09-18 | Batch 5 | Sidebar rows: action gutter + leading-mark semantics | ConversationRow, tests | tsc 0; **79/79**; packaged probe c | human pixel gate open |

## Maintenance rules

- Append a row when a production commit lands; never rewrite history in this file.
- Priority definition: LOW (docs/tests-internal), MEDIUM (localized behavior), HIGH (user-journey
  or engine behavior), CRITICAL (security/privacy/persistence/lifecycle).
- `packaged` column: name the packaged evidence (see PACKAGED_EVIDENCE_INDEX.md) or `-`.
- Keep the count current: at RC, `production commit count in range` = number of rows in the
  Campaign A table + integration commits (cross-checked against `git log`).
