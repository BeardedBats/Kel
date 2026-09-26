# Desktop Chat, task and Tools implementation batch — 2026-09-26

## Source changes

Current Figma references: Chat `185:4284`, task `273:1586`, Tools `313:2441`, Image Model dropdown `146:52` in `BlpVvZGuc9j9HhxUojIiJI`.

- Chat: confirmed mode subtitle, Planning display alias, exact workspace/footer/mode artwork and composer bitmap. Missing mode/usage remains absent or unknown. No runtime or permission request was added.
- Sidebar: 28px rows, 10px gap, working/unread/read/attention colors and pin hover replacement. Mobile working indicators retain the spinner.
- Task: exact picker artwork, time display, bitmap/glass, disabled no-target ongoing conversation and Cancel/Create treatments. Selected assistant uses its name. Existing task callbacks and stored 24-hour time remain.
- Tools: focusable failed-status detail opens below desktop rows. Light uses semantic surfaces. Image Model field/menu now match component dimensions, blur, radius and selected check artwork.

## Checks performed

Source Electron renders passed Dark/Light at 1440/800px. Chat checked confirmed injected mode catalog, loaded assets, truthful missing metrics, stored synthetic messages, turn/list/avatar spacing and last-turn wheel access. Sidebar variant checks mounted the production component with supplied props; Enter/Space and pin hover passed. These are presentation checks, not real worker-status journeys.

Task Dark checks used a supplied assistant catalog and changed an unsaved model draft. No native assistant catalog availability is claimed. No-target ongoing conversation was disabled. Both themes passed 600×614px bounds, 34px fields, 72px prompt, Weekly/Advanced/Manual/Custom and Cancel/reopen/Escape checks.

Tools used a real isolated provider record with a synthetic noncredential and unreachable loopback endpoint. Model selection, MCP enable and reload persistence passed. No image request ran. Both widths/themes passed 34px field, 14px arrow/check, 32px menu rows, 10px radius/24px blur/6px padding, and failed-status 18px blur without viewport or heading overlap. Settings were journaled, restored and compared; the owned provider was deleted.

TypeScript, production source build and full desktop regression passed: 65 files / 448 tests. The existing listener warning appeared without failures. Nine focused tests passed earlier, including two new confirmed-mode subscription tests. Engine behavior did not change; no engine rebuild was needed.

No canonical Data write occurred. Source probes closed; the shared preview remains until milestone verification. Screenshots and logs stay in the bounded temporary stack. Independent review is unavailable.

## Limits and next action

Rebuild one milestone package, verify its normal bundled renderer, and record archive provenance. App remains at 8c67121 until that check and the desktop disposition pass. Exact Light palette requires a supplied Light reference; semantic contrast checks do not prove pixel parity. Live mode/usage, task execution, OAuth-required Tools, worker/provider and remote authentication remain separate acceptance work. Setup Autonomy and Pet enabling need Nick's decisions. Mobile stays paused.
