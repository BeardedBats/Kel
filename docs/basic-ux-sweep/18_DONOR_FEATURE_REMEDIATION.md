# Donor feature remediation (2026-09-17)

What this pass changed, how each change was proven in the **packaged app**, and what is deliberately
left for later. Audit evidence: `16_DONOR_PATTERN_MATRIX.md`, `17_DONOR_FEATURE_FINDINGS.md`.

## 1. Keep this computer awake (item 6) — ADAPT, implemented

**Before.** `system.keepAwake` existed as a small switch on the donor *Scheduled tasks* page. It
wrote the setting to local config and to the backend KV, but **nothing consumed it**: no caller of
`powerSaveBlocker`/`preventSleep` existed anywhere in the tree, so the switch was inert. Its tooltip
also named the donor ("AionUi prevents your computer from going to sleep") in all 13 locales, and the
control lived on a page outside Kel's navigation.

**Now.**

- `process/utils/keepAwake.ts` (new) owns Electron's power-save blocker:
  `prevent-app-suspension` — sleep is prevented, the screen may still dim. The blocker id lives in
  the main process, so closing or crashing Kel releases the inhibition with the process; nothing on
  disk can keep a machine awake.
- The stored choice is applied once at startup (`index.ts` → `initKeepAwake()`), reading local config
  first and falling back to the older backend KV.
- `system-settings:get-keep-awake` / `set-keep-awake` report `{ enabled, active }` where `active`
  comes from the live blocker, so the surface states the truth instead of mirroring the switch.
- `renderer/components/kel/KelKeepAwakeCard.tsx` (new) is the one Kel-native control, mounted in
  **Settings · System** (Kel's advanced home): plain title, plain description ("prevents sleep only —
  your screen can still dim… stops when Kel closes"), and a live state line.
- The donor toggle is removed from the Scheduled-tasks page in the same change (JR-40 — superseded
  donor controls are swapped, not duplicated); its banner ("Scheduled tasks only run while your
  computer is awake.") stays.

**Files:** `process/utils/keepAwake.ts` (new), `process/bridge/systemSettingsBridge.ts`,
`common/adapter/ipcBridge.ts`, `index.ts`, `renderer/components/kel/KelKeepAwakeCard.tsx` (new),
`renderer/pages/settings/SystemSettings.tsx`, `renderer/pages/cron/ScheduledTasksPage/index.tsx`,
`desktop/tests/unit/keepAwake.test.ts` (new).

**Tests:** `bunx vitest run tests/unit/keepAwake.test.ts` → 4/4 (sleep-only type, idempotent enable,
released on disable, local-first with backend fallback). `bunx tsc --noEmit` → 0 errors.

**Packaged verification** (`ux-audit/runs/kaw/out/ux-keepawake.json`, scenario `keepawake` on
`dist/package-final8/win-unpacked`):

| Step | Result |
|---|---|
| Card + switch present in Settings · System | `cardPresent: 1` |
| Off by default | `initialState: "Off — the computer sleeps normally."`, `initiallyOff: true` |
| Enable | `stateAfterEnable: "Active — this computer will not sleep while Kel is open."`, `activeAfterEnable: true`, toast shown |
| Restart | switch still on, `stateAfterRestart` Active, `activeAfterRestart: true` (stored choice re-applied at startup) |
| Disable | `stateAfterDisable: "Off — the computer sleeps normally."`, `inactiveAfterDisable: true` |
| Console errors | `[]` |

## 2. Long-conversation stress (item 11) — verified, no change needed

`ux-audit/seed-large.py` (150 extra turns → 314 messages in one conversation) and
`ux-audit/diag-longchat.cjs` against `dist/package-final8`:

| Measure | Result |
|---|---|
| Time until the first message node renders after opening the chat | **259 ms** |
| Mounted message nodes with 314 messages in the list | **100** (the list windows instead of rendering everything) |
| Scroll height / JS heap after open | 5,065 px / **61 MB** |
| Scroll to top and back | returns to the bottom; 0 layout stalls observed (timings sleep-bounded) |
| Ctrl+F find-in-conversation over the long list | search input focused, results return ("#138 … Stress turn 129 …") |
| Console errors | `[]` |

No virtualization or paging work is required; the existing windowed list already meets the contract.

## 3. Verified as already present (no change made)

Queue while working, composer prompt history, find in conversation, conversation timeline/jump rail,
side-by-side preview rail, compact tool activity, work inspector, session evidence (diagnostics),
cross-runtime project knowledge, workflow checkpoints, runtime auto-detection, and unified tool/MCP
configuration — each with its code path, UI location and packaged evidence in
`17_DONOR_FEATURE_FINDINGS.md`.

## 4. Deliberately not implemented (with reasons)

| Item | Why not now |
|---|---|
| Session-scoped tool controls (7) | Needs a per-conversation capability contract in the engine; global policy (`Autonomy` + Tools) is the only honest model in this build. Release-docket item, not a UI-only change. |
| Interactive in-chat approvals (9) | Permission prompts already exist on Work; moving them into the transcript is a work-lifecycle change. Vetting already proves the inline-UI pattern. |
| Capability suggestions (8) beyond the provider notice | No reliable task→capability detector; the risk of nagging outweighs the value. The provider case is already covered by the plain "Open Providers" notice. |
| Memory change proposals (16) | The engine already refuses silent overwrites and records supersession with trust levels; the missing piece is a review surface over existing records. |
| Artifact lineage UI (18) | Records exist (`artifacts/<job>/<run>/<file>`, team `assignment_artifacts`); a "Where did this come from?" surface belongs with the preview rail work. |
| Advanced worker view (12), profiles (21), remote status/approval (22) | Optional/future. Projects already provide the isolation Profiles would add (see 16 for the Projects-vs-Profiles comparison). |

## 5. Residuals recorded honestly

- The donor tooltip strings (`cron.page.keepAwakeTooltip`, 13 locales) are no longer mounted anywhere;
  the strings remain in the locale files. Cleaning them is part of the next i18n sweep rather than
  churn in this pass.
- Item 10's packaged evidence is the component contract plus the earlier Work/text dumps: this
  environment has no provider, so no tool-heavy conversation could be produced to render a live
  "View Steps" group.
- `dist/` is gitignored; the build is reproducible from the committed tree, and the artifact hashes
  are recorded in `15_FINAL_VERDICT.md`.

## 6. Release docket (after this pass)

1. Session-scoped tool controls — engine contract + chat surface.
2. Memory change proposals — review surface over the existing engine records.
3. Artifact lineage — "Where did this come from?" on the preview surface.
4. In-chat approval cards — Work prompts moved beside the transcript.
5. i18n cleanup — unused donor strings (`keepAwake*`) across locales.
6. Independent review of this pass, then the frozen-release decision.
