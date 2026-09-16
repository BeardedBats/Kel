# UX program — continuation record

Status: **checkpointed (batch 1 complete, batch 2 not started)** · recorded 2026-09-16
Owner: user-journey auditor (this record is written for whoever resumes the UX program).

## Where things live

- Worktree/branch: `C:\Users\Nick\Desktop\Kel\kel-ux-v15` on branch **`ux/v15-journeys`**
- Base commit (batch 1): **`147a4552de09cc91a29984c01b230a20ae5e0462`** (`147a455`), parent = release `5e76b21`
  (this continuation record is the next commit on the same branch)
- Frozen release (baseline, never modified): `C:\Users\Nick\Desktop\Kel\Kel Releases\Kel-V1.5-Frozen`
- Main repo `Kel-Repo` stayed on `main` @ `5e76b21`, clean (only the pre-existing untracked `Agents.md`)
- Rebuilt package (stale — see warning): `kel-ux-v15\dist\package\win-unpacked`
- Audit scratch (harness runs, profiles): `C:\Users\Nick\Desktop\Kel\ux-audit\` (`roots/{fresh,seeded3,fresh-fixed}`, `runs/{fresh,seeded3,fixed3}`)
- Harness: `packaging/ux-audit.cjs` (scenarios `first-run | tour | settings | palette | keyboard | readability | sider | maintext | compose`)
- Docs: `docs/product/USER_JOURNEY_STANDARD.md` (rules JR-1…JR-30, authoritative),
  `USER_JOURNEY_HISTORY.md` (ledger + open items O1…O10), `UX_AUDIT_V1.5.md` (baseline + batch-1 status),
  `UX_DONOR_SIMPLICITY_MATRIX.md`, `docs/product/evidence/v15-ux-fixes/{baseline,fixed}/`

**⚠ Warning:** the packaged build at `dist/package/win-unpacked` was produced *before* the SettingsSider revert,
so it still contains the settings-registry crash that was fixed-back-in-source. Rebuild before any further
verification; do not treat that artifact as the batch-1 deliverable.

## UX fixes complete and verified (committed in `147a455`)

Verified by re-running the harness against the rebuilt packaged app (fresh + seeded profiles); evidence in
`evidence/v15-ux-fixes/fixed/`:

1. **Landing:** onboarding (completed or skipped) now ends at the chat composer `#/guid`; fresh first-run reaches
   the composer in ~12.7 s total (5 steps). H1 / JR-1.
2. **Onboarding copy:** all five steps use plain language (no engine versions, registry counts, quotas,
   "scope/grant/guardrails/Agents"); statuses read "ready, usage not reported" / "needs you to sign in". H2 / JR-4/5.
3. **Failure surfaced in chat:** the chat landing shows "None of your connected models is available right now…"
   with an **Open Providers** action when no provider is usable. H3 / JR-8/9/10. (Landing only — O7.)
4. **Work page:** human counts (`0 active · 2 waiting to continue · 0 need you`), task-text titles (UUID titles gone),
   no "verdict:"/"durable state only" strings, no fabricated "Updated" timestamp, human waiting-state reasons,
   single empty state. H4 / JR-11/12.
5. **Primary nav:** `New Chat / Work / Projects / Permissions` (Team, Providers, Diagnostics removed from the
   primary sider; routes + palette still reach them; Autonomy page titled Permissions with a human count). H5 / JR-14/19.
6. **Palette:** "Search or jump to…", plain hints, human job-state hints; Enter/Escape verified keyboard-only. H7 / JR-23.
7. **Projects:** single "Refresh map" action; default project shown as "General". H9(part)/H10 / JR-17/29.
8. **Readability:** providers/projects/work/settings-appearance measure 0 offenders < 4.4:1. H8(part) / JR-25.
9. **Containing a regression:** the Settings-sider expansion was reverted after it crashed (donor keeps a second
   registry) — the source no longer contains the crash. H6 / JR-30 (new rule).

## Verification passed (explicit)

- `fixed3/first-run`: `hashAfterOnboarding=#/guid`, `timeToComposerMs≈12700`, `forwardClicks=5`, `errors=[]`,
  `consoleErrors=[]`.
- `fixed3/tour`: nav clicks land (`Work→#/work`, `Projects→#/projects/knowledge`, `New Chat→#/guid`; removed entries
  absent), `consoleErrors=[]`; `/work` and `/projects/map` text verified.
- `fixed3/palette`: label + hints + Enter/Escape verified.
- `fixed3/maintext`: `/guid` notice; `/work` counts; `/autonomy` = "Permissions".
- `fixed3/sider`: sider shows `New Chat / Work / Projects / Permissions`; UUID gone.
- `fixed3/readability`: zero offenders on providers/projects/work/settings-appearance.
- Frozen release untouched (all mtimes predate the session); `Kel-Repo` still clean on `main`.

## Not verified / open (do not report these as done)

- **O1** Happy-path chat / project work / approval journeys — no usable provider on this machine (codex quota
  exhausted, others unauthenticated). Needs a connected model, then run `ux-audit.cjs … compose`.
- **O7** Provider notice not yet mounted inside an open conversation (landing only).
- **O8** Settings-sider expansion (Providers/Team/Diagnostics/System entries) — **reverted**; root cause =
  second registry in `SettingsPageWrapper.tsx`. Fix both registries (or unify) per JR-30, then rebuild.
- **O9** Workspace label renders the raw i18n key `conversation.workspace.unnamedSpace` — add the key to
  `en-US/common.json` under `conversation.workspace` (or return a literal when `t` cannot resolve).
- **O10** One 13 px "Kel" on `/guid` still measures 2.72:1 — element unidentified; extend the readability probe to
  record a DOM selector for the offender.
- **O2–O6** Donor remnants (About links, WebUI/Pet pages, `acp-temp-<id>` tab label, diagnostics confirmations,
  duplicate "Back to Chat") — see the history ledger.

## Exact next action (batch 2, when resumed)

1. Fix **O8**: extend `SettingsPageWrapper.tsx`'s registry for the new ids (or unify the two registries), re-apply
   the sider expansion from `147a455^..147a455` history notes; fix **O9** (locale key) and **O10** (locator) in the
   same pass if small.
2. Rebuild: `cd kel-ux-v15/desktop && bun run package && ELECTRON_BUILDER_COMPRESSION_LEVEL=1 bunx electron-builder --config kel-builder.json --win --x64 --publish never`
   (packaging inputs `dist/runtime/KelEngine` + `LICENSE` must exist at the **worktree root**).
3. Re-run the harness on the new package (`settings,sider,maintext,readability` minimum; full set preferred),
   archive as `evidence/v15-ux-fixes/fixed2/`, then update `USER_JOURNEY_HISTORY.md` statuses (O8/O9/O10) and this
   record. Do not tag or release; batch 2 is not a release event.
