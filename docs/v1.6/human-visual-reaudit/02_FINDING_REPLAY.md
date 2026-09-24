# 02 — FINDING REPLAY (HV-01 … HV-14)

Method note: every finding was replayed via (a) the fixing diff's full code review
(`01_DELTA_REVIEW.md`), (b) re-run of the campaign's source matrix gates by this audit, (c) the
audit's independent probe script — 16 check groups + 16 screenshots, zero console/http/page errors
— and (d) the dedicated installed build. Evidence paths are relative to `evidence/`.
Dispositions: VERIFIED_CLOSED / PARTIALLY_CLOSED / STILL_REPRODUCES / REGRESSION_INTRODUCED.
The re-audit instruction's checklist IDs (HVR-01…HVR-14) are cross-referenced per item.

## HV-01 — Global contrast / unreadable surfaces — VERIFIED_CLOSED
- Fix: `arco-override.css` pins `body { color: var(--text-primary) }` and native
  `input/select/textarea { color: inherit }`; `kel-tokens.css` pins `.kel-card` text color.
- Replay: matrix contrast scan (re-run): 3 informational sub-4.5 items — the "Needs setup" chips
  at 4.35, above the disabled/decorative allowance — and **0 below 2.5**. No black-on-dark found;
  independent text dumps of all 11 surfaces render readable; Light/Dark computed backgrounds
  verified (rgb(249,250,251) / rgb(22,32,44)). Evidence: `probes-source/kelvis/kelvis-verify.json`,
  `probes-source/own/reaudit-probes.json` (+ screenshots).
- [Instruction HVR-02]

## HV-02 — Permissions scrolling — VERIFIED_CLOSED
- Fix: `.kel-scope` is the sole scroll owner (`flex:1; min-height:0; overflow-y:auto;
  overflow-x:clip; overscroll-behavior:contain`).
- Replay (independent, 5 sizes — 1366×768, 1440×900, 1440×960, 1920×1080, 1100×800):
  mouse wheel Δ = 150/56/56/56/139; End reaches exact max; Home = 0; PageUp/PageDown each Δ > 0 at
  every size; bottom content row visible after End; html/body never scroll (dual-scroll 0);
  horizontal overflow 0. Evidence: `probes-source/own/reaudit-probes.json` → `permissionsScroll`,
  screenshots `permissions-*`.
- [Instruction HVR-01]

## HV-03 — Work → Open the chat — VERIFIED_CLOSED
- Fix: attention actions navigate through `resolveConversationRoute()`; target normalized from
  `/chat/<id>` to `/conversation/<id>`; resolver maps Kel conversation id → donor id
  (`needsAttention.ts`, `KelNeedsAttention.tsx`, `useConversationListSync.ts`).
- Replay: 3 × "Open the chat" (approval + 2 continuations) each opened
  `#/conversation/3bdaab68` — the mapped donor id of the referenced conversation "main"
  ("Release checklist - build step", message content confirmed). Back → `#/work`;
  forward → conversation (sane history). Second conversation verified: `#/conversation/4d37b815`
  ("Getting started") renders. No Home fallback, no stale id, no wrong conversation.
  Unknown ids fall back to Home via catch-all (sane). Evidence: JSON → `workToChat`,
  `conversationManual`; screenshots `conversation-*`.
- [Instruction HVR-03]

## HV-04 — Sidebar — VERIFIED_CLOSED
- Fix: canonical Kel K brand mark (`assets/logos/brand/app.png`, 1024px) replaces the text-K;
  attention badge offset fixed inside the sider (`KelWorkPanel` → badge `offset:[0,-4]`).
- Replay: sider mark `img src …/app-Bq_S8k2x.png` naturalWidth = 1024; badge "2" bounds
  L230/R250 inside sider (right 250 ≤ sider 261) and also inside at ~1000px width; no SVG
  `<text>K` logo; no plain-text "K" element; footer stable at 1440/1000 widths.
  Evidence: JSON → `sidebar`; screenshots `sidebar-1440`, `sidebar-1000`.
- [Instruction HVR-04]

## HV-05 — Work & context language — VERIFIED_CLOSED
- Fix: plain-language states and state-aware actions in `KelWorkPanel.tsx` / `work/index.tsx`
  ("Kel is holding until you decide.", "Kel can pick this up where it stopped.",
  "N of M steps done"; pause only for RUNNING/QUEUED/READY; resume only for PAUSED).
- Replay: attention rows + text dumps show exactly these strings; no raw enum leakage
  (`AWAITING_USER`, `RUNNING ·`, `· UNCERTAIN` absent); drawer/work gates pass in the matrix;
  permission item correctly reads "Review the request", chat items "Open the chat".
  Evidence: matrix JSON (workLanguage/drawerLanguage), JSON → `workToChat` attentionRows.
- [Instruction HVR-03/05/13 cross-cut]

## HV-06 — Permissions language — PARTIALLY_CLOSED (residual: HVRA-MINOR-001)
- Fix: user-language labels ("Active permissions", "Access requests"), plain-language request
  blocks (Why/Benefit/If denied/Risk), truthful expiry formatting (`formatUntil`), internals
  (Permission check, Locked guardrails) behind "Advanced details".
- Replay: primary view shows the new labels + blocks; expiry renders "in 3d" (no "0s ago");
  lease/snapshot/worker/"prepared review sample" terminology absent; advanced section hidden by
  default (`permCheckHidden: true`, `guardrailsHidden: true`) and fully usable after expanding.
- **Residual:** the raw engine job id (`job_review_summary`) is still rendered in the primary
  "Work" column of the Active-permissions table — see `06_FINAL_FINDINGS.md` HVRA-MINOR-001.
- Evidence: JSON → `permissionsLanguage`, `permissionsRows`; screenshots `permissions-*`.
- [Instruction HVR-05]

## HV-07 — Model page — VERIFIED_CLOSED
- Fix: explicit IA — "Default Kel model" card with truthful availability chips, custom-models
  section with "No custom models configured" empty state; contradictory "No configured models"
  eliminated (`ModelModalContent.tsx`, `KelModelControl.tsx`, `settings.json`).
- Replay: page shows "Default Kel model", "Automatic — Kel picks what is available" marked
  "Current", 2 × "Available" (Claude/Codex built-in), 3 × "Needs setup" (Anthropic/DeepSeek) —
  truthful; "No custom models configured" present, "No configured models" absent; text readable;
  current selection obvious ("Current" + saved-immediately note). Evidence: JSON → `modelPage`;
  screenshot `model`.
- [Instruction HVR-06]

## HV-08 — System page — VERIFIED_CLOSED
- Fix: folders behind an "Advanced — folders" disclosure; meaningful Kel workspace root presented;
  reduced card dependence (single-card sections with dividers).
- Replay: normal view shows Data folder (Kel workspace root, Copy path / Show in folder), Backup,
  Restore; "Advanced — folders" present; "Work Directory" and donor path NOT visible before
  expanding (`hasWorkDir:false`, `hasDonorPath:false`); after expanding, the full physical path
  (including the donor-era subfolder name) appears — **by design** ("full physical path only in
  advanced/copy detail"); Show/Hide toggle functions. Evidence: JSON → `systemPage`; screenshot
  `system`.
- [Instruction HVR-07]

## HV-09 — Appearance — VERIFIED_CLOSED
- Fix: donor theme cover deleted (`themeCovers.ts` + `default-theme.png` removed; `builtinThemes.ts`
  falls back to a neutral layout preview); Light/Dark/Follow System cards; font-size defaults
  raised (Markdown 16, Code 14; `fontSizes.ts` + `markdown.css`).
- Replay: no donor text on the page (`donorText:false`); all three theme cards present; clicking
  Dark → `arco-theme=dark` (bg rgb(22,32,44)), Light → light (rgb(249,250,251)), Follow System
  applies; controls work; font controls show Markdown 16 / Code 14 / Chat 14 / Global 14; effective
  values `--md-font-size:16px`, `--code-font-size:14px`; no donor preview images. Evidence: JSON →
  `appearancePage`, `fontFloors`; screenshot `appearance`.
- Note: "Scale 95%" persisted UI zoom observed (fixture state; see `06_FINAL_FINDINGS.md`
  observations — not a defect).
- [Instruction HVR-08]

## HV-10 — Tools — VERIFIED_CLOSED
- Fix: `aionui-browser` displays as **Kel Browser** (`MCP_DISPLAY_NAMES`, `McpServerHeader.tsx`);
  internal protocol id retained for compatibility; chrome-devtools unchanged.
- Replay: Tools list shows "chrome-devtools" and "Kel Browser"; `aionui-browser` not visible;
  donor scan on the page = 0. Internal id names remain in code by design. Evidence: JSON →
  `toolsPage`; screenshot `tools`.
- [Instruction HVR-09]

## HV-11 — Desktop Pet — VERIFIED_CLOSED
- Fix: failed enable is loud and truthful — persists `pet.enabled:false` and throws with the reason
  (`systemSettingsBridge.ts`); renderer settles the switch OFF and shows the message
  (`PetSettings.tsx`).
- Replay (source + installed): toggle click → switch stays/returns OFF with message "The desktop
  pet is not available in this build, so it stays off."; after a REAL page reload the state reads
  OFF again; persisted `pet.enabled:false` verified in the decoded config file; size radios and
  DND/authorization switches disabled/consistent while off; window count = 1 (no pet window).
  Evidence: JSON → `desktopPet`; screenshot `pet-after-refusal`.
- Note: refusal surfaced as two identical toasts — recorded as HVRA-SUG-002 (cosmetic).
- [Instruction HVR-10]

## HV-12 — Team / workforce exposure — VERIFIED_CLOSED
- Fix: Team/Roster/Office/Studio navigation removed (command palette, settings sider, settings page
  wrapper); `/team*` + legacy donor routes redirect safely; Workforce runtime untouched.
- Replay: `#/team`, `#/team/office`, `#/team/roster`, `#/team/studio`, `#/settings/skills-hub`,
  `#/settings/agent`, `#/settings/assistants`, `#/settings/capabilities` → all `#/guid`; sidebar
  has no team/roster/office/studio words; settings sider shows no Agents/Skills/Team entries;
  palette entries removed (code); workforce page + `kelTeam` runtime calls remain in the bundle;
  engine untouched (scope proof). No runtime Workforce deletion.
- [Instruction HVR-11]

## HV-13 — Installer donor failure strings — VERIFIED_CLOSED
- Fix: user-visible installer strings Kel-branded across messages/smokes/report scripts; legal
  attribution preserved.
- Replay: `installer-messages.nsh` donor tokens = 0, `installer-common.nsh` = 0; remaining donor
  matches in installer material are internal NSIS symbols (`AIONUI_*` vars), internal temp/script
  names and legal LICENSE headers — classified internal/legal (`donor-sweep-static.txt`,
  `donor-contexts-*.txt`); smoke replays: messagebox 12/12 compile-only PASS (missing=Kel.exe),
  self-lock full PASS, rstrtmgr compile-only PASS, report script PASS (`status=skipped code=E1003
  copyTextLength=613`). See also HVRA-MINOR-002 (installer FileDescription metadata).
- [Instruction HVR-12]

## HV-14 — Cross-cutting polish + responsive — VERIFIED_CLOSED
- Fix: radius/style normalization (rd-8) across touched surfaces; grouping retained; single-card
  sections with dividers; spacing/labels raised for readability.
- Replay: narrow 1100×800 → horizontal overflow 0 on 7 screens; 125% zoom emulation at 1366×768
  → overflow 0 on work/autonomy/model; attention items keep grouping; no clipped controls found
  (badge bounds, bottom reachability, screenshots); System/Appearance/Permissions/Tools show
  reduced card repetition with meaningful grouping.
- [Instruction HVR-13 + HVR-14]

## Summary of dispositions

| Finding | Disposition |
| --- | --- |
| HV-01 contrast | VERIFIED_CLOSED |
| HV-02 permissions scrolling | VERIFIED_CLOSED |
| HV-03 work → open the chat | VERIFIED_CLOSED |
| HV-04 sidebar | VERIFIED_CLOSED |
| HV-05 work & context language | VERIFIED_CLOSED |
| HV-06 permissions language | PARTIALLY_CLOSED (HVRA-MINOR-001) |
| HV-07 model page | VERIFIED_CLOSED |
| HV-08 system page | VERIFIED_CLOSED |
| HV-09 appearance | VERIFIED_CLOSED |
| HV-10 tools | VERIFIED_CLOSED |
| HV-11 desktop pet | VERIFIED_CLOSED |
| HV-12 team hidden | VERIFIED_CLOSED |
| HV-13 installer strings | VERIFIED_CLOSED |
| HV-14 polish/responsive | VERIFIED_CLOSED |

Installed-phase confirmation: the dedicated-install battery (campaign matrix re-run by this audit,
plus the audit's independent probes and the installed engine probe) reproduced every finding check
against `C:\Users\Nick\KelVisualReauditInstall` — 25/25 gates, 0 console errors; gate-by-gate
evidence in `05_INSTALLED_REVIEW.md`.
Totals: 13 × VERIFIED_CLOSED + 1 × PARTIALLY_CLOSED = 14/14 replayed.
