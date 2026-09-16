# UX program — continuation record

Status: **batch 1 + batch 2 complete and verified; program parked at a clean checkpoint** · recorded 2026-09-16
Owner: user-journey auditor (this record is written for whoever resumes the UX program).

## Where things live

- Worktree/branch: `C:\Users\Nick\Desktop\Kel\kel-ux-v15` on branch **`ux/v15-journeys`**
  - batch 1: `147a455` (41 files) → continuation record `574bd40`
  - Design Vetting Sessions feature + bridge fix: committed next (see `git log`; docs in `docs/vetting/`)
  - batch 2 (this record's scope): committed together with the vetting program's close-out
- Frozen release (baseline, never modified): `C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.5-Frozen`
- Main repo `Kel-Repo` stayed on `main` @ `5e76b21`, clean (only the pre-existing untracked `Agents.md`)
- Rebuilt package (current): `kel-ux-v15\dist\package\win-unpacked` (fresh renderer + fresh PyInstaller
  `KelEngine`, `scripts/build-runtime.ps1`)
- Audit scratch: `C:\Users\Nick\Desktop\Kel\ux-audit\` — seeds `roots/seeded3`; runs used by this record:
  `runs/b2-{vetting-live,settings,sider,maintext,readability}`, `runs/final-sider`,
  `runs/final{,2,3}-readability`, `runs/paneldump`, `run-batch2.sh`
- Harness: `packaging/ux-audit.cjs` — scenarios now include `vetting`, `vetting-live`, `paneldump`, `peek`;
  readable offenders now record class/trail/background and measure SVG `fill`

## Batch 2 — fixes complete and verified

Evidence: `docs/product/evidence/v15-ux-fixes/fixed2/` (run JSONs + screenshots + readability data).

1. **O8 — one settings registry.** `BUILTIN_TAB_IDS` (the list both the settings sider and
   `SettingsPageWrapper` derive from) listed 2 of the 10 tabs both maps define; the nav rendered a two-item
   shell and extension anchors to the other ids silently fell to "unanchored". The registry now carries the
   full ordered set; browser-mode hides desktop-only tabs. Verified: `b2-settings` visits every tab with
   **zero console errors**. H15 / JR-30.
2. **O9 — workspace label.** `getWorkspaceDisplayName` resolved neither namespace path
   (`conversation.workspace.*` vs the bundle's `workspace.*`), so unnamed workspaces showed a raw key.
   The helper now tries both paths and never returns a raw key; keys added next to their sibling in the
   conversation bundle (en-US, zh-CN) and to the common bundle. Verified: `final-sider` shows "Workspace",
   no raw key. H16 / JR-17.
3. **O10 — 13 px "Kel" at 2.72:1.** Root cause found with the widened readability probe: the **selected**
   assistant chip let Arco's `.arco-btn-text` override its `text-t-primary` on the dark chip background
   (the inactive chip had the same disease). Both states now paint through module-CSS classes using the
   theme-aware tokens (`--aou-9`, `--color-text-1`); the probe was also fixed to measure SVG `fill` so the
   white-on-black logo is no longer reported as black-on-black. Verified: `final3-readability` reports
   **zero offenders on `/guid`**. H17 / JR-25.
4. **JR-34 (found by the vetting live pass).** A new engine route must be added to the renderer bridge
   whitelist (`KelService.ts` `kel:request`); `/api/vetting` was missing and every Vetting panel call was
   rejected as "Unknown Kel action" and swallowed. Fixed; the panel now renders the live session in the
   packaged app. H14 / JR-34 (new rule).

## Verification passed (explicit)

- `b2-vetting-live`: panel booleans true (`panelTopic/State/Progress/Decisions`), `errors=[]`,
  `consoleErrors=[]`; screenshots + `live-databases.txt` in `docs/vetting/evidence/live/`.
- `b2-settings`: every settings tab visits clean (`/settings/model|agent|skills|tools|appearance|webui|pet|system|archived|about`),
  `consoleErrors=[]`.
- `final-sider`: workspace label fixed; `errors=[]`.
- `b2-maintext` / `b2-readability` / `final2-readability` / `final3-readability`: `/guid` offender list empty.
- Engine: `python -m pytest tests -q` → **475 passed, 10 subtests, 0 failed** (2m12s), including 30 vetting tests.
- `bunx tsc --noEmit` → 0 errors after every renderer change.
- Frozen release untouched; `Kel-Repo` still clean on `main`.

## Not verified / open (do not report these as done)

- **O1** Happy-path chat / project work / approval journeys (no usable provider on this machine; codex quota
  exhausted, others unauthenticated). Re-run `ux-audit.cjs … compose` once a model is connected.
- **O2–O6** Donor remnants (About links, WebUI/Pet pages, `acp-temp-<id>` tab label, diagnostics
  confirmations, duplicate "Back to Chat") — see the history ledger.
- **O7** Provider notice not yet mounted inside an open conversation (landing only; the vetting banner +
  panel now cover the vetting path).

## Exact next action (when resumed)

None required to close this program; the ledger marks O8/O9/O10 fixed. Optional follow-ups in priority
order: O7 (conversation-level provider notice), O5 (diagnostics confirmations), O4 (`acp-temp-<id>` tab
label). Rebuild + verify with the same harness commands; do not tag or release (these are not release
events).
