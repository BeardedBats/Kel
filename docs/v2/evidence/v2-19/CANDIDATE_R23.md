# Kel V2 candidate r23 — setup path, narrow Dark Settings, native color picker

**Source:** `integration/v2` @ `407f5a3c3313e0fd99ca14c20baeb734657350b2` (pushed). One new pack from that source on 2026-09-23: `bun run package`, then `npx electron-builder --config kel-builder.json --x64 --dir` (exit 0, signed). Staged at `C:\Users\Nick\KelV2Candidate.r23`; it was not promoted. Its launcher points to `C:\Users\Nick\KelV2Runs\prepared\r23\`, separate from the running r20 root. Packaged UI checks used another fresh root, `...\r23-ui\`.

## Source repair

| Finding | Repair | Proof |
| --- | --- | --- |
| Settings bounced silently to onboarding before setup completed; onboarding's own Add Model link did the same | The route guard allows the setup page and its configuration routes. It still redirects main pages to onboarding with a visible explanation. Configuration pages show **Continue setup**. The completion flag is written before entering the main app; a failed write stays on setup and shows an error. | r23 packaged clicks: Settings → Appearance, Continue setup → onboarding, Add Model → Model, Projects → knowledge, Kibble → onboarding with explanation, Start using Kel → home. Store has `kel.onboardingCompleted_v1=true` only after completion. |
| Theme colors collide at 800px; 200px theme cards leave unused width at 390px | At narrow panel widths, color rows use a two-column grid and the Restore action enters normal flow. At phone width, one theme card fills each row. | At 800px, header title ends y=672 and Restore begins y=676; color row is 198px wide with its input inside it. At 390px, the three cards are 292×116 within a 292px panel; document width remains 390px. Screenshots below. |
| Native color picker closed on the first saved adjustment | Color rows no longer remount on each override save. Their draft field syncs when the effective color changes. | Focused DOM test pins the same picker node across two saves. In packaged r23, the native Chromium color popup opened, one keyboard adjustment saved `#0b1732`, and the popup remained visible after that save (`picker-first`, `picker-second`). A second CDP ArrowRight did not change the value; further native adjustment remains unproved. |

Figma authority checked: [Screens FINAL `185:2`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=185-2), [Foundations `139:2`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=139-2), [Components `136:2`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=136-2). The final Appearance frame is `186:1097`: 1440×900 with a 920×760 Settings card. r23 measures the same card at x=388, y=112, and keeps the three theme cards on one row at desktop (198×116). No narrow Appearance frame exists in the inspected final page; the narrow changes adapt the same components.

## Checks and archive gate

| Check | Result |
| --- | --- |
| `bunx tsc --noEmit -p tsconfig.json` | PASS |
| `npx vitest run tests/unit/kel-theme-color-input.dom.test.tsx tests/unit/kel-setup-route.test.ts` | 2 files, 8 tests PASS |
| `npx vitest run tests/unit` | 43 files, 294 tests PASS |
| `C:\tmp\verify_asar.py` | ARCHIVE SOUND: manifest, renderer bundles, main and index byte equality |
| `app.asar` | one, 300,588,834 B, SHA-256 `1c3bde1f4ab0b162716560a4fdc5547e5a209d067fd9315667ffe019a6831a2d` in both build and staged candidate |
| `Kel.exe` | one, SHA-256 `69a2efd0c6247b0f0acb6dac2cc86136acf1380cc9b9724f4733e23c073ca600` |
| frozen engine / donor aioncore | `00846a7e64fdaa95` / `67eb02774bab3855` SHA-256 prefixes; unchanged from r22 |
| DLL set / stray executables | 15 DLLs at the same relative paths as r22; zero `electron.exe`; no stray unpacked directories |

## Bounded V2-19 packaged pass — **[UI]**

Playwright connected through CDP to the staged r23 app on a fresh isolated profile, store, and engine. Navigation, setup completion, picker input, and Reset used browser input events. DOM reads measured geometry. Store reads used SQLite read-only mode. The r23 process tree was stopped and restarted after the pass: it reopened `#/guid`, then Settings showed Dark active and the default App background. The store showed `theme.overrides={}` after Reset. Routes for Projects, Work, Activity, Recipes, and Kibble opened their headings without an engine failure card. This is a navigation slice, not a full V2-19 completion claim.

Saved views: [desktop](r23-ui/desktop.png), [800px](r23-ui/tablet.png), [390px](r23-ui/narrow.png), [picker after first save](r23-ui/picker-first.png), [picker after second key](r23-ui/picker-second.png). At 800px, the narrow color layout removes the prior title/Restore overlap. At 390px, all three theme cards use the available row width without document overflow.

**Review:** `request_review` was unavailable. No independent review occurred.

**Protected state after checks:** r23 test processes are stopped. r20 remains running from `C:\Users\Nick\KelV2Candidate` (root PID 6356, engine PID 10848) and its archive is still `baaab70ae30b6462`. Stable engine PID 26544 remains under `C:\Users\Nick\KelDogfoodCandidate` (`4f23c9ae` archive). r22 remains staged (`f1b68169` archive). Astra's `ux/v2-shell` remains at `0052075`. No candidate was renamed, promoted, or installed over another.

**Remaining:** Light-mode faint labels are outside this Dark pass. Full V2-19 functional regression and V2-16 conversation-open/project-switch/remote timings remain. Google sign-in and live services need account access; fresh Muse audio needs a recording; physical iPhone checks need the device. The web-host suite was not run while r20 was live, because its setup requires all Kel instances stopped.
