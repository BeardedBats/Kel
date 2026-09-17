# AUTO_RESUME — V1.6 Visual UX Audit

State file for whoever picks this up next. Read this first, then `00_STATUS.md`.

## CURRENT STATE: VISUAL UX HOLD READY — implementation frozen by the coordinator

**Audit worktree:** `C:\Users\Nick\Desktop\Kel\kel-v16-visual-audit`
**Branch:** `audit/v16-visual-ux` **Baseline:** `ffeef73`
**Status:** audit accepted as the current Visual UX evidence set; **implementation NOT started** on the
coordinator's instruction. The **Human Visual UX gate remains OPEN** (see the vision limitation below).

### Hold conditions in force

* Do **not** create the implementation worktree yet (proposed name, for later: `kel-v16-visual-fix` /
  `ux/v16-visual-fix`).
* Do **not** write to `kel-ux-v15` (the authoritative integration worktree).
* Do **not** cherry-pick, merge, rebase, or port production changes.
* Do **not** touch frozen releases (`Kel Releases/*`, tag `v1.6.0-pre1`).
* Do **not** edit the shared files (`KelService.ts`, `KelWorkPanel.tsx`, `MessageList.tsx`,
  `Messages/hooks.ts`, `chatLib.ts`) against a stale HEAD.

## Measured state of Main at the time of writing (read-only recon)

| Fact | Value |
|---|---|
| Main integration worktree HEAD | `70d68e4` — `docs(v1.6): Phase 4 recon notes + continuation state` (on top of Phase 3 `85e99fb`) |
| Committed since `ffeef73` | 21 files: `chatLib.ts`, `KelService.ts` (+34, hunks at `@@245` and `@@338`), `reconcileHistory.ts`, `KelWorkPanel.tsx` (+104), **new** `components/kel/KelApprovalCard.tsx` (291), `MessageList.tsx` (+11), `Messages/hooks.ts` (+8), `runtime/kel/{apply_changes,authorize,coding,core,engine,service}.py`, `runtime/tests/*`, docs |
| In-flight P1 remediation (uncommitted) | **`runtime/kel/acp_host.py`, `runtime/kel/capabilities.py`, `runtime/kel/research.py` only** — Python runtime, no renderer files |
| Main's next phase (Phase 4) | **i18n / donor-string cleanup** across 12 locales × ~20 JSON files, plus a possible **removal of the Butler entry points** in Model / Tools / Skills / Assistants / Cron settings |
| My 18 planned files | **unchanged since `ffeef73`** (verified file by file) |
| `KelWorkPanel` mount point | still `Sider/index.tsx:198` — must be preserved by any sidebar work |
| `TeamSiderSection` | still **unmounted** (no importer outside its own file) — the dead-code finding holds at the new HEAD |

**Do not assume `70d68e4` is the base.** Wait for the coordinator's `CLEAN_MAIN_HEAD=<commit>`.

## Next action when the hold lifts

1. `git rev-parse <CLEAN_MAIN_HEAD>` == the coordinator's value.
2. Create the fresh worktree from that exact commit; carry `docs/v1.6-visual-ux/` across as the spec.
3. Run the re-validation checklist in `13_IMPLEMENTATION_DEPENDENCIES.md` §13.4 (re-read every shared file,
   re-validate every root cause, refresh the baselines with a new `probe-a` run).
4. Execute batches 1→8 from that document; **batch 1 is the settings-shell routing fix** (S1).

## Preparation documents added during the hold (all read-only work)

| File | Purpose |
|---|---|
| `11_CONFLICT_MAP.md` | Per-file conflict map: shared with Main / independent / lifecycle-sensitive / renderer-only, with the measured evidence |
| `12_ACCEPTANCE_CRITERIA.md` | Per-finding acceptance: observable behaviour + automated + packaged + DOM + human/pixel evidence, and the evidence gaps |
| `13_IMPLEMENTATION_DEPENDENCIES.md` | Dependency classes, edges, the 8 implementation batches, and what must stay isolated |
| `14_SCREENSHOT_REVIEW_INDEX.md` | All 35 screenshots: finding(s), route, what to inspect, expected corrected state, plus the capture gaps |
| `15_SEMANTICS_FLAGS.md` | Proposals that change behaviour/capability/vocabulary rather than presentation — for coordinator decision, not silent implementation |

## Hard constraints carried forward

See the hold conditions above. In addition: coordinate (never race) the shared files listed in the recon
table, and treat the **engine-loss behaviour as a PRODUCT defect** — it must not be dismissed because clean
startup passes.

## Vision limitation — the gate is still open

This reviewer had **no visual perception** of the 35 captured screenshots. Every finding is derived from
measured DOM geometry, computed styles, contrast maths, source inspection, and live reproduction. Those
measurements remain valid evidence, but **they do not replace a pixel-level human review**. The eventual
Visual UX gate must include a human (or vision-capable) review of the rendered pixels in
`docs/v1.6-visual-ux/screenshots/`, using `14_SCREENSHOT_REVIEW_INDEX.md` as the checklist.

## Verification that already exists and should be re-run after every batch

```bash
export NODE_PATH="C:\Users\Nick\Desktop\Kel\kel-ux-v15\desktop\node_modules"
cd C:/Users/Nick/Desktop/Kel/ux-audit/visual
node probe-a.cjs "<appDir>" "C:/Users/Nick/Desktop/Kel/ux-audit/roots/visual-a" "<outDir>"   # surfaces, contrast, geometry, screenshots
node probe-b.cjs "<appDir>" "C:/Users/Nick/Desktop/Kel/ux-audit/roots/visual-a" "<outDir>"   # colour control, New Chat, engine-loss
node probe-c.cjs "<appDir>" "C:/Users/Nick/Desktop/Kel/ux-audit/roots/visual-c" "<outDir>"   # populated sidebar, hover overlap
node ../../visual/summarize.cjs <outDir>/visual-a.json <outDir>/summary.txt
```

Baselines recorded by this audit: `work` text 605 chars · `permissions` 3615 chars · hover `overlapPx` 12 ·
`newChat` rows 5/5/5 · transcription light 3.24:1 · theme-gallery label 1.06:1 · System `Back up now` 1.23:1 ·
sidebar rows 5 vs 9 conversations (6 with zero messages).

## Known gaps — do not treat as verified

* **No `/conversation/<id>` screenshots** (the header pills for finding 2 and the Phase 3 approval card were
  never captured). Capture these **before** the composer batch.
* Dense/populated states not exercised; widths below 1024px not captured; `Follow system` and third-party
  themes untested.
* The OS colour-dialog closing was inferred from a measured focus loss plus the source-level remount; confirm
  once with a real mouse on Windows.
* `desktop.log` from a failed-engine session was not collected; add it to the #17 acceptance pack.

## Scratch artifacts (outside both repos, safe to delete)

`C:\Users\Nick\Desktop\Kel\ux-audit\visual\` (probes + summariser + dbprobe),
`C:\Users\Nick\Desktop\Kel\ux-audit\runs\visual-{a,b,c}\`, `C:\Users\Nick\Desktop\Kel\ux-audit\roots\visual-{a,c}\`.
No root belonging to other work was modified; `visual-c` is a copy of `final11-sessiontools`.
