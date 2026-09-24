# 01 — DELTA REVIEW (production changes `05a076b..6d957ee9`)

Scope: every production diff between the pre-repair production target `05a076b` and the immutable
re-audit target `6d957ee9aad7200fb2fcff9b505e0771e2dfdcda`.

Result of scope probe: **all production changes are confined to `desktop/` — 47 files (45 modified,
2 deleted) across 8 fix commits.** Every other commit in the range is documentation/evidence only.
Baseline equivalence: `git diff --name-only 05a076b..eb4da52` is docs-only, so the repair branch
started from a production tree identical to `05a076b`.

Evidence: `evidence/delta-desktop.diff` (full diff, 2254 lines), `evidence/delta-desktop-files.txt`
(name-status). Commit chain: `05a076b → dbe42aa → ea61003 → 7cf6030 → eb4da52 → 3be6b18 → 14fc254 →
3df2176 → d934a60 → 393640e → 6b4e40d → 092409b → 9ad8a08 → 250597e → 65bcaa3 → 6d957ee`
(+ completion-doc commits up to `37b1f27`).

## Commit → finding map

| Commit | Subject | Findings |
| --- | --- | --- |
| `14fc254` | shell + navigation + readability cluster | HV-01…HV-07, HV-12 |
| `3df2176` | pet truth + system page + installer branding | HV-08, HV-11, HV-13 |
| `d934a60` | appearance + tools + radius | HV-09, HV-10 |
| `6b4e40d` | conversation resolution + Work states | HV-03 (probe found `/conversation/<kel-id>` 404) |
| `9ad8a08` | pet settle (RA-MINOR-003) | HV-11 |
| `250597e` | pet deadline reconcile | HV-11 |
| `65bcaa3` | pet TS7011 + test pins | HV-11 (regression pin) |
| `6d957ee` | report status/fallback paths (support script only, 2 lines) | HV-13 (finishes naming sweep) |

## File-by-file review

Each row: file → what changed (verified from the diff) → finding → adjacent-risk note.

| # | File (`desktop/packages/desktop/src/...`) | Change | Finding | Adjacent risk check |
| --- | --- | --- | --- | --- |
| 1 | `common/config/fontSizes.ts` | defaults: markdown 13→16, code 12→14 (min 12→12/10→12) | HV-09 | spec/clamp unchanged; only defaults |
| 2 | `process/bridge/systemSettingsBridge.ts` | pet enable refusal now throws + persists false (both branches) | HV-11 | IPC contract change is intentional; getPetEnabled provider exists (verified line 80) |
| 3 | `renderer/assets/themes/default-theme.png` | deleted (donor cover) | HV-09 | no remaining references (grep clean) |
| 4 | `renderer/components/chat/KelWorkPanel.tsx` | plain-language job maps; attention-first order; state-aware actions (pause RUNNING/QUEUED/READY, resume PAUSED, cancel guards); badge offset `[0,-4]`; footer wrapper; text ≥14px | HV-05 (+HV-14) | engine actions unchanged; only UI gating + labels |
| 5 | `renderer/components/kel/KelCommandPalette.tsx` | team/roster entries removed; `kelTeam` import dropped | HV-12 | other palette entries untouched |
| 6 | `renderer/components/kel/KelDataCard.tsx` | three stacked Cards → single `kel-card` + `kel-divider` sections | HV-08/HV-13 | content preserved; layout only |
| 7 | `renderer/components/kel/KelKeepAwakeCard.tsx` | text 13/12 → 14px | HV-01/HV-14 | copy unchanged |
| 8 | `renderer/components/kel/KelModelControl.tsx` | availability chips use `--kel-ok-fg/bg` tokens; wording; default-model card language | HV-07 | data flow unchanged (`/api/model`) |
| 9 | `renderer/components/kel/KelNeedsAttention.tsx` | action navigates `resolveConversationRoute(...)` | HV-03 | derived-only view, no new mutations |
| 10 | `renderer/components/kel/KelPrimitives.tsx` | `formatUntil()` added | HV-06 | pure formatter |
| 11 | `renderer/components/kel/needsAttention.ts` | action target `/conversation/<id>` (was `/chat/<id>`) | HV-03 | fail-closed scoping unchanged |
| 12 | `renderer/components/layout/Layout.tsx` | black-square text-K SVG → canonical `brandMark` asset (`assets/logos/brand/app.png`); size-32 overflow-hidden | HV-04 | fallback renders unchanged |
| 13 | `renderer/components/layout/Router.tsx` | `HIDE_WORKFORCE_SURFACES`: `/team*` → `/guid`; legacy donor routes → `/team/roster` (which itself → `/guid`) | HV-12 | KelTeam page + Workforce runtime still bundled; only routing |
| 14 | `.../SettingsModal/contents/AppearanceModalContent/index.tsx` | rd-16px → rd-8px radius pass | HV-14/HV-13 | cosmetic |
| 15 | `.../SettingsModal/contents/ModelModalContent.tsx` | empty-state wording → "No custom models configured" + explanatory sub + description | HV-07 | custom-provider CRUD untouched |
| 16 | `.../SystemModalContent/BrowserDataSection.tsx` | radius rd-8 | HV-14 | cosmetic |
| 17 | `.../SystemModalContent/DevSettings.tsx` | radius rd-8 | HV-14 | cosmetic |
| 18 | `.../SystemModalContent/VoiceInputSection/index.tsx` | radius rd-8 | HV-14 | cosmetic |
| 19 | `.../SystemModalContent/index.tsx` | working-folder overrides behind "Advanced — folders" disclosure (hidden by default); radius/spacing | HV-08 | controls unchanged; only disclosure |
| 20 | `renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync.ts` | added `getRouteConversationIdForKelId` + `resolveConversationRoute` | HV-03 | read-only resolution against the in-memory conversation mirror; fallback = original arg |
| 21 | `renderer/pages/kel/autonomy/index.tsx` | "Active permissions"/"Access requests" language; `formatUntil`; advanced gating (permission check + guardrails); copy rewritten; emergency-stop explanation | HV-06 | mutations (revoke/allow/deny) unchanged; gating shows `disabled` on non-ACTIVE revoke |
| 22 | `renderer/pages/kel/work/index.tsx` | `VERDICT_TEXT`/`MILESTONE_STATE_TEXT` maps; state-aware actions; progress text | HV-05 | same |
| 23 | `renderer/pages/settings/AppearanceSettings/themeCovers.ts` | deleted | HV-09 | builtinThemes no longer references covers |
| 24 | `renderer/pages/settings/ModeSettings.tsx` | wrapper `flex-col gap-20px` (composes KelDefaultModelCard + custom models) | HV-07 | composition only |
| 25 | `renderer/pages/settings/PetSettings.tsx` | settle() re-reads authoritative state after any outcome; 900ms deadline reconcile; error message with reason; local value settled to truth | HV-11 | dependent controls `disabled={!enabled}` (size/dnd/confirm) unchanged; no pet window creation path touched |
| 26 | `renderer/pages/settings/ToolsSettings/McpServerHeader.tsx` | `MCP_DISPLAY_NAMES: {'aionui-browser': 'Kel Browser'}`; internal id kept | HV-10 | chrome-devtools branch untouched (lines 96/125) |
| 27 | `renderer/pages/settings/components/SettingsPageWrapper.tsx` | nav entries for `agent`/`skills` removed | HV-12 | tab render map updated consistently |
| 28 | `renderer/pages/settings/components/SettingsSider.tsx` | builtin tabs agent/skills removed; legacy anchor remaps dropped | HV-12 | unknown tab id → falls back to default view (verified at runtime in replay) |
| 29 | `renderer/services/i18n/locales/en-US/settings.json` | `noConfiguredModels` → "No custom models configured"; `modelDescription`, `customModelSupportNote` wording | HV-07 | strings only |
| 30 | `renderer/styles/arco-override.css` | `body { color: var(--text-primary) }`; `input,select,textarea { color: inherit }`; `--code-font-size` 13→14 | HV-01 | theme-boundary repair; no specificity wars found in replay |
| 31 | `renderer/styles/kel-tokens.css` | `.kel-scope` = single scroll owner (flex:1, min-height:0, overflow-y:auto, overflow-x:clip, overscroll-behavior:contain); `.kel-card` color pin; type scale 16/14 | HV-01/02 | checked: no competing `overflow:hidden` chain remains for Kel pages |
| 32 | `renderer/styles/markdown.css` | markdown default 15→16; code 13→14 (fallbacks) | HV-09 | fallback values only |
| 33 | `renderer/theme/builtinThemes.ts` | donor cover removed → generated neutral preview | HV-09 | theme apply logic unchanged |
| 34 | `resources/windows/installer-messages.nsh` | 47 bilingual dialog strings → Kel naming (EN+ZH); define **names** keep `AIONUI_` prefix for compat | HV-13 | strings only; compile verified by smoke replay |
| 35 | `resources/windows/installer-observability.nsh` | fallback log name → kel-installer-*.jsonl | HV-13 | internal artifact name |
| 36 | `resources/windows/installer-process-control.nsh` | locker text/JSON names → "Kel installer" | HV-13 | strings only |
| 37 | `resources/windows/installer-remove-registry.nsh` | locker pattern `AionUi installer(*)` → `Kel installer(*)`; DetailPrint | HV-13 | pattern update matches new window title; no removal logic change |
| 38 | `resources/windows/installer-repair-heal.nsh` | two summary strings → Kel | HV-13 | heal LOGIC unchanged (still reads registry InstallLocation) |
| 39 | `resources/windows/support/query-lockers.ps1` | fallback known-files `AionUi.exe` → `Kel.exe`; self-lock name | HV-13 | enumeration unchanged |
| 40 | `resources/windows/support/report-installer-failure.ps1` | fallback log path, status path, copyText "Kel installer failure", URL → BeardedBats/Kel | HV-13 | empty-DSN behavior unchanged (status=skipped, no network) |
| 41 | `scripts/build-with-builder.js` | DetailPrint text "Kel-bundled-uninstaller override source." | HV-13 | build logic untouched |
| 42 | `scripts/smoke-installer-failure-messagebox.js` | expectations → Kel strings (incl. `Kel.exe`, title, copyText) | HV-13 | harness only |
| 43 | `scripts/smoke-installer-report.ps1` | expectations → Kel | HV-13 | harness only |
| 44 | `scripts/smoke-installer-rstrtmgr-ui.js` | expectations → Kel; `AIONUI_APP_EXECUTABLE_FILENAME=Kel.exe` | HV-13 | harness only (some TEMP artifact names keep donor strings — internal, not user-visible) |
| 45 | `scripts/smoke-installer-self-lock.js` | expectations → Kel | HV-13 | harness only |
| 46 | `tests/unit/donor-policy.test.ts` | added pet-truthfulness pins + installer-branding gate (scans `.nsh` for donor names) | HV-11/HV-13 | test-only |
| 47 | `tests/unit/needs-attention.test.ts` | expectation corrected to `/conversation/conv-a` | HV-03 | test-only |

## Unrelated-change analysis

No unrelated behavioral change was found. Two deliberately adjacent passes were reviewed and are
in-scope:

1. **Radius pass (rd-16px → rd-8px)** on touched settings surfaces — part of the HV-14/HV-13
   control-polish scope; cosmetic only, no layout logic.
2. **Installer log/script renames** (DetailPrint, smoke expectations, internal artifact names) —
   part of the HV-13 naming sweep; no installer control flow changed (verified against
   `installer-repair-heal.nsh` / `installer-remove-registry.nsh` semantics).

Flagged for runtime scrutiny during replay (recorded up front, not assumed harmless):

- `autonomy` primary table still renders `lease.job_id` (the "Work" column) — the human finding
  HV-06 cited `job_review_summary` as an internal string; the fix relabeled the surface but did
  not remove/relocate the id. Runtime capture recorded in `02_FINDING_REPLAY.md` (HV-06).
- `Router` legacy donor routes (`/settings/agent*`, `/settings/skills*`, `/settings/capabilities*`,
  `/settings/skills-hub`, `/settings/assistants`) redirect to `/team/roster`, which — with
  `HIDE_WORKFORCE_SURFACES` — redirects again to `/guid`. Double-hop is by design; verified at
  runtime.
- `SettingsSider` removal of `agent`/`skills` tabs: unknown stored tab ids must fall back
  gracefully (verified at runtime).
- Pet dependent controls (`size`, `dnd`, `confirmBubble`) are `disabled={!enabled}` — replay
  confirms they are unusable while the pet is off (no contradictory configuration).

## Test-surface changes

`needs-attention.test.ts` expectation was corrected (old expectation pinned the broken `/chat/…`
target); `donor-policy.test.ts` gained the RA-MINOR-003 truth pins and the installer-branding
grep gate. Both suites pass in this audit (see `03_REGRESSION.md`).

## Delta verdict

The production delta is coherent, bounded, and maps 1:1 to the 14 human findings plus RA-MINOR-002 /
RA-MINOR-003 acceptance criteria. No unexplained production change, no engine change, no new IPC
surface beyond the intentional pet refusal rejection, no authorization/routing semantics weakened
at source level. Behavioral replay results: `02_FINDING_REPLAY.md`.
