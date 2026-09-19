# Kel V1.6 — Human Visual UX Audit · 00 STATUS

Audit performed by the independent Human Visual UX reviewer thread.
**Production code was NOT modified in this phase.** The only new worktree is the isolated audit worktree below.

| | |
|---|---|
| Audit baseline (source of truth) | `ffeef73` — `feat(lineage): every generated artifact can say where it came from (v1.6)` |
| Audit worktree | `C:\Users\Nick\Desktop\Kel\kel-v16-visual-audit` on branch `audit/v16-visual-ux` |
| Runnable artifact inspected | `C:\Users\Nick\Desktop\Kel\kel-ux-v15\dist\package-final16\win-unpacked\Kel.exe` (built 09:27, i.e. **after** `ffeef73` 03:08 and **before** the Phase 3 commit 09:44 — so it is `ffeef73` + Phase 3 work-in-progress) |
| Immutable checkpoint | `v1.6.0-pre1` → `f24d9c2`. Not touched. |
| `kel-ux-v15` (active main worktree) | **Not written to.** Read only. |
| Status | **VISUAL AUDIT COMPLETE — WAITING FOR PHASE 3 INTEGRATION HEAD** |

## Why this audit exists

Mechanical verification passed repeatedly while obvious human UX problems remained. This audit therefore
optimises for *what a person sees*, not for whether a check went green. Findings are split into:

* **Reproduced** — observed in the running packaged app, with a measurement or DOM text capture.
* **Source-mapped** — deterministic from code with file:line (a read of the code that renders it).
* **Judgement** — a design opinion, explicitly labelled, with the reasoning given.

## Method, and one important limitation (stated plainly)

**No vision channel was available to this reviewer.** Screenshots returned as raw base64/artifact data that
could not be perceived as images, so this audit does **not** claim to have "looked at" any screenshot.
Instead it established what the user sees by four measurable routes:

1. **Live DOM measurement** of the running packaged app (geometry, computed styles, font-size histograms per
   surface, WCAG contrast ratios per text node, element identity across interactions).
2. **Source reading** of the exact components that render each surface (file:line throughout these docs).
3. **Reproduction** of the reported failures (engine loss, settings navigation, hover overlap) with the
   observed output pasted in.
4. **Screenshots retained as evidence** for a human reviewer — in `docs/v1.6-visual-ux/screenshots/` (35 files).

Where the mechanism could not be observed end-to-end (e.g. an OS colour dialog closing, which cannot be
driven from outside), the doc says so and gives the measured proxy plus the source-level cause.

**Theme labelling of the retained screenshots:** the app's default theme is **light**. Files suffixed
`-light-1440` were captured in **light**; files suffixed `-dark-1440` were captured after the in-app theme
toggle switched to dark. The shell screenshot `shell-1440-light.png` is the post-onboarding default state.

## Evidence index

| Evidence | Location |
|---|---|
| Full DOM/contrast/geometry sweep, 23 surfaces | `evidence-visual-a.json`, readable digest `evidence-visual-a.txt` |
| Interaction + engine-loss reproduction | `evidence-visual-b.json`, digest `evidence-visual-b.txt` |
| Populated sidebar, hover overlap, hex field | `evidence-visual-c.json` (full), `evidence-visual-c.json` |
| Screenshots (35) | `screenshots/` |
| Probe scripts (scratch, outside the repos) | `C:\Users\Nick\Desktop\Kel\ux-audit\visual\probe-{a,b,c}.cjs`, `summarize.cjs`, `dbprobe.py` |
| Raw probe output | `C:\Users\Nick\Desktop\Kel\ux-audit\runs\visual-{a,b,c}\` |

Reproduction commands (re-runnable, isolated profile, off-screen window):

```bash
export NODE_PATH="C:\Users\Nick\Desktop\Kel\kel-ux-v15\desktop\node_modules"
node probe-a.cjs "<appDir>" "C:/Users/Nick/Desktop/Kel/ux-audit/roots/visual-a" "<outDir>"
```

## Headline results

**Three of the user's reported problems were reproduced exactly; one was corrected against the evidence.**

* **Reproduced:** engine loss produces raw `TypeError: fetch failed` on all five engine screens (Work,
  Projects, Permissions, Team, Transcription). See `09_ERROR_STATES.md`.
* **Reproduced:** Settings → Agents / Team roles / Tools throws the user out of the Settings shell into the
  main application sidebar. See `04_SIDEBAR_AND_NAVIGATION.md`.
* **Reproduced by measurement:** the conversation-row hover action overlaps the title's box by exactly
  **12px**. See `03_CHAT_AND_COMPOSER.md`.
* **Corrected:** New Chat does **not** create a temporary conversation — it creates nothing at all, so there
  is nothing to auto-remove. The *related* complaint (empty conversations linger) is real but has a
  different cause: message-less conversations exist in the store and render as sidebar rows.
  See `01_HUMAN_FINDINGS.md` items 11–12.

**Also measured and worth stating up front:** the Kel "Desk" token system itself is contrast-clean — Work,
Projects, Permissions, Team, Providers and Diagnostics produced **zero** WCAG AA offenders in both themes.
Every contrast failure found sits in **donor surfaces** (settings, theme gallery, transcription page) or in
one native-control case. So the readability problem is *not* the Kel palette; it is the places that never
adopted it. See `08_DARK_LIGHT_READABILITY.md`.

## Files in this set

| File | Contents |
|---|---|
| `00_STATUS.md` | This file |
| `01_HUMAN_FINDINGS.md` | All 17 reported problems, checked one by one, with severity |
| `02_VISUAL_SYSTEM.md` | Token audit vs the stated visual direction; proposed design-system changes |
| `03_CHAT_AND_COMPOSER.md` | Chat surface, composer, model/tool placement, hover actions, New Chat |
| `04_SIDEBAR_AND_NAVIGATION.md` | Sidebar semantics, folders vs Projects, Settings shell, nav inventory |
| `05_WORK_PROJECTS_PERMISSIONS.md` | The three Kel "console" pages |
| `06_TRANSCRIPTION.md` | Donor IA vs current Kel IA, and the exact target structure |
| `07_TEAM_AND_AGENTS.md` | Agent/Team/Roster/Office/Studio terminology and what actually exists |
| `08_DARK_LIGHT_READABILITY.md` | Measured contrast ratios, light and dark |
| `09_ERROR_STATES.md` | Engine launch/reachability audit and error-state design |
| `10_IMPLEMENTATION_OWNERSHIP.md` | Ownership, sequence, Phase-3 conflict analysis, branch plan |
| `AUTO_RESUME.md` | Resume state for whoever picks this up |

## Stop point

Per the brief: **no production-code remediation has started.** The next action is to receive the Phase 3
Integration Coordinator's committed HEAD, re-base `audit/v16-visual-ux` onto it, and begin at the sequence in
`10_IMPLEMENTATION_OWNERSHIP.md`.
