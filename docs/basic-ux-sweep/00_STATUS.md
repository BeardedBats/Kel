# Basic UX expectations sweep — status

Program: audit the packaged release candidate for the basic behaviours a polished desktop AI app is
expected to have, classify every item, implement only the high-value missing basics, verify in the
packaged app, and leave the rest honestly classified.

## State

| Area | State |
|---|---|
| Packaged audit (pre-fix RC) | done — `sweep-seed`/`sweep-a`/`sweep-b` runs, evidence below |
| Classification of all 40 checklist areas | `01_EXPECTATION_MATRIX.md` |
| Implemented this program | default Kel model + per-chat override; theme foundation colors; drafts survive restart; palette actions; global search (chats/transcripts/vetting); local backup + restore; data-folder actions |
| Final packaged verification | **done** — full as-built battery on `dist/package-final6/win-unpacked`: `sweep2`/`sweep3`/`sweep4`, the regression set, first-run and the a11y probes; results, defects and honest limits in `15_FINAL_VERDICT.md` |
| Defects found by the as-built battery | F11 (blank app on Settings · Model / Kel chats), F12 + F12b (backup, staged restore), F13 (theme section never refreshed), F14–F16 (probe/seeder instruments) — all fixed before the shipped artifact; see `14_FINDINGS_AND_FIXES.md` |
| Journey rules | JR-41..JR-47 + history H22 (see `docs/product/`) |

## Evidence

| Where | What |
|---|---|
| `evidence/audit/ux-sweep-a.json`, `ux-sweep-b.json`, `ux-sweep-seed.json` | pre-fix audit runs (matrix, palette, theme, model, recovery, about) |
| `evidence/final/ux-sweep2.json`, `ux-sweep3.json`, `ux-sweep4.json` | as-built runs of the new behaviours on the shipped artifact |
| `evidence/final/ux-*.json` + `*.png` | regression battery, first-run, a11y probes and the screenshots they captured |
| `C:\Users\Nick\Desktop\Kel\ux-audit\runs\f3-*` | raw run directories behind `evidence/` (scratch, not shipped) |

## Out of scope (per brief)

Permission history, onboarding replay, provider connection wizard, settings import/export between
installs — none were added; adjacent work did not reintroduce them.
