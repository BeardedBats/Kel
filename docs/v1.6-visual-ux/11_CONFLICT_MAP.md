# 11 — Conflict Map (per-file, measured against the live integration worktree)

All statements below were **measured read-only** on `C:\Users\Nick\Desktop\Kel\kel-ux-v15` at the moment of
writing. They are not assumptions.

## 11.1 What Main has actually changed since the audit baseline

Integration worktree HEAD at recon time:

```
70d68e4 docs(v1.6): Phase 4 recon notes + continuation state (from the Phase 3 thread)
85e99fb feat(approvals): decisions answer in the conversation, on one durable record (v1.6)
ffeef73  <- audit baseline
```

**Committed since `ffeef73` (21 files):**

| File | Δ | Region |
|---|---|---|
| `desktop/.../common/chat/chatLib.ts` | +19 | approval message kind |
| `desktop/.../process/services/kel/KelService.ts` | +34 | hunks at `@@ -245` (inside `initializeKel`) and `@@ -338/370` (route allowlist) |
| `desktop/.../process/services/kel/reconcileHistory.ts` | +3 | history reconciliation |
| `desktop/.../renderer/components/chat/KelWorkPanel.tsx` | +104 | approval surface in the Work & context panel |
| `desktop/.../renderer/components/kel/KelApprovalCard.tsx` | **new** (291) | in-chat approval card |
| `desktop/.../pages/conversation/Messages/MessageList.tsx` | +11 | renders the approval card |
| `desktop/.../pages/conversation/Messages/hooks.ts` | +8 | approval wiring |
| `runtime/kel/{apply_changes,authorize,coding,core,engine,service}.py` | small | approval engine |
| `runtime/kel/chat_approvals.py` | **new** (314) | approvals |
| `runtime/tests/{test_v15_authorize,test_v16_approvals}.py` | +13 / **new** 403 | approvals |
| `docs/in-chat-approvals/**`, `docs/v1.6/AUTO_RESUME.md`, `docs/product/**` | — | records |

**In-flight, uncommitted (this is the P1 capability remediation):**

```
runtime/kel/acp_host.py
runtime/kel/capabilities.py
runtime/kel/research.py
```

→ **The P1 remediation currently touches the Python runtime only. No renderer file.** That is why nothing in
the visual plan is blocked *today* by P1 — but the coordinator's instruction stands: resolve against a clean
Main HEAD, because P1 is not finished and the renderer may be touched before it lands.

**Declared next Main phase (Phase 4 = i18n / donor-string cleanup)** will touch, per its own recon note:

* `renderer/services/i18n/locales/<12 languages>/*.json` (~20 files each)
* the **Butler** entry points in *Model / Tools / Skills / Assistants / Cron* settings (flagged for likely
  **removal**)

## 11.2 Measured status of every file this audit plans to edit

Every one of these was scanned against `ffeef73` and against the working tree:

```
TOUCHED committed=… uncommitted=… : <file>        -> printed for nothing below
```

**Result: none of the 18 planned files has changed since `ffeef73`.** They are clean today. The map below
therefore distinguishes *today's* state from *risk before landing*.

| # | Planned change | Exact file(s) | Components / functions | Main may touch? | Risk & rule |
|---|---|---|---|---|---|
| 1 | Design tokens + density | `renderer/styles/kel-tokens.css`, `styles/arco-override.css` | `:root`, `[data-theme='dark']`, `.kel-*` primitives | **No** (Phase 4 is i18n; no token work declared) | Low, but **global blast radius**: every Kel surface reflows. Must be its own commit and re-measured before anything else. |
| 2 | Settings shell fix | `renderer/components/layout/Router.tsx`, `components/settings/SettingsSider.tsx` | `SettingsSider` `BUILTIN_TAB_IDS`/`builtinMap`, `Routes` (`/settings/agent`, `/settings/skills`, `/settings/tools`, `/settings/capabilities`, `/settings/skills-hub`, `/settings/assistants`) | **YES — Phase 4** targets the *same settings entries* (Butler removal in Tools/Skills/Assistants; `settings.json` strings) | **Coordinate before editing.** Decide with the coordinator: does the settings entry keep existing? If Phase 4 removes Butler from Tools/Skills, do it in the same pass as the nav fix so the sider is edited once. |
| 3 | Hover overlap | `pages/conversation/GroupedHistory/ConversationRow.tsx` | row padding (`pe-16px`), action cluster (`absolute end-8px`, `size-20px`) | No | **Isolated, safe, cheap.** |
| 4 | Error translation | `components/kel/kelApi.ts` (new classifier), `pages/kel/{work,projects,autonomy,team,transcription}/index.tsx` error sites | `call<T>()` in `kelApi.ts`; `setError(...)` in each page; `KelErrorState` | **No** (Phase 4 owns *locale catalogs*; these strings are hard-coded English, see 11.3) | Renderer-only except the raw string's origin. Coordinate only on copy style with Phase 4. |
| 5 | Engine supervision / readiness | `process/services/kel/KelService.ts` (+ main entry) | `kelRequest()`, `initializeKel()`, descriptor handling, `before-quit` drain | **YES — Phase 3 already edited this file** (+34, `@@245`, `@@338`) | **Lifecycle-sensitive. Serialize.** My target regions (`kelRequest` at 12–21, descriptor/readiness at 43–122) are *different* hunks from Phase 3's, so a merge should be clean — but the file must be taken from the clean HEAD and re-read first. |
| 6 | Work de-carding | `pages/kel/work/index.tsx`, `components/kel/KelPrimitives.tsx` | 4 unconditional `KelCard`s, `KelEmpty` inside cards, `KelSection` nesting | No | Isolated. Interacts with the approval work only via **card policy** (agreement needed so the Phase 3 approval card stays a deliberate special card). |
| 7 | Projects de-carding + retitle | `pages/kel/projects/index.tsx` | 7-column table w/ 3 row actions, raw-JSON `<pre>`, page title | No | Isolated. Title change is a **semantics flag** (see `15_SEMANTICS_FLAGS.md`). |
| 8 | Permissions rebuild | `pages/kel/autonomy/index.tsx` | header actions, nested `.kel-card`, policy-checker card, guardrails `KelSection` | **Adjacency risk:** Phase 3 puts approvals *in chat*; this page renders the same requests | Agreement needed on which surface owns approvals, or the two will diverge in wording. Content work is independent; **the overlap decision is not**. |
| 9 | Transcription IA | `pages/kel/transcription/index.tsx`, `index.module.css` | whole page shell, key modal, action row, bottom actions | No | **Isolated renderer-only** (engine API untouched). Watch the E2E `data-testid` set. |
| 10 | Composer relocation | `pages/conversation/components/ChatConversation.tsx`, `components/chat/SendBox/index.tsx`, `KelModelPill`/`KelToolsControl` | `headerExtraNode` (`ChatConversation.tsx:443-465`), `sendbox-tools` row | **YES — adjacent:** Phase 3 added `KelApprovalCard` into `MessageList` and the Work panel; the header/pill area itself is untouched | Do it **after** Phase 3/4 land. Preserve the invisible warm-up `AcpModelSelector`. |
| 11 | Readability sweep | `pages/settings/AppearanceSettings/CssThemeSettings.tsx`, `pages/settings/SystemSettings.tsx`, `components/kel/ThemeColorsSection.tsx`, transcription CSS | theme-gallery card label, backup buttons, colour rows | **No Butler in these files** (verified: Butler appears in `ModelModalContent`, `ToolsModalContent`, `AgentSettings`, `AssistantSettings`, `SkillsSettings`, `FeedbackReportModal`, `WebuiModalContent`, `LocalAgents` — none of which this item touches) | Safe. But the **theme-gallery fix is the colour-picker file** — items 11 and 12 overlap each other and should be one commit. |
| 12 | Colour-picker remount | `components/kel/ThemeColorsSection.tsx` | `ThemeColorRow` keys `${token}:${hexValue}:${saved}:${rev}`, parent `key={`${themeId}:${refresh}`}`, `apply()` | No | Same file as item 11 → **one commit**. |
| 13 | Team terminology + no-op seed | `pages/kel/team/index.tsx`, `components/settings/SettingsSider.tsx` (shared with item 2), i18n | Office empty `onAction`, tab labels | **YES — Phase 4**: locale catalogs + Butler in Skills/Assistants settings | Coordinate the sider part with item 2 and Phase 4; the Office-button fix is independent. |

## 11.3 New finding from this recon (for Main, not for me to fix)

**The five Kel console pages are not localised.** Their user-facing copy — `"Work could not be loaded"`,
`"Autonomy state could not be loaded"`, `"Project context could not be loaded"`, `"Your transcripts live
here"`, `"Seed the default roster"`, `"No specialist has been assigned yet."` — is **hard-coded English
inside `pages/kel/**`**. Verified: none of these strings exists in
`renderer/services/i18n/locales/en-US/*` (20 catalog files).

Consequence for sequencing: Phase 4's "audit ALL supported locales and every normal user-facing surface" will
**not** reach these pages through the catalogs. Either Main adds them to the catalogs (making my copy edits a
locale-key change instead of a literal change), or the Kel pages stay English-only by decision. **The
coordinator should choose, because it decides whether my copy work lands inside or outside Phase 4's lane.**

## 11.4 Safest implementation order (conflict-aware)

1. **Isolated, zero-overlap, highest severity first:** items 4 (error translation) → 3 (hover overlap).
2. **Coordinated once, never twice:** items 2 + 13's sider half + Phase 4's settings/Butler decisions
   → single coordinated edit of `SettingsSider.tsx` + `Router.tsx`.
3. **Global token/density pass:** item 1 alone, its own commit, re-measure before proceeding.
4. **Page rebuilds:** items 6, 7, 8 (Work, Projects, Permissions) — independent of Main, but the
   approvals-ownership question (item 8) must be answered first.
5. **Transcription:** item 9 — independent, largest single-file rewrite, do when nothing else is in flight.
6. **Shared-file items last, from the clean HEAD:** item 5 (`KelService.ts`) and item 10 (composer), each
   re-read and re-validated against the HEAD before editing.
7. **Readability/contrast gate:** items 11 + 12 together, then wire the gate.

**Never in parallel with Main:** `KelService.ts`, `KelWorkPanel.tsx`, `MessageList.tsx`, `Messages/hooks.ts`,
`common/chat/chatLib.ts`, and (new) the 12 locale directories.
