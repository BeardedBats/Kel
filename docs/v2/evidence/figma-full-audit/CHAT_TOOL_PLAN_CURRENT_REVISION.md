# Current Figma Chat tool calls and plan — scoped package evidence

Live frames: desktop tool calls and plan `273:12914`, mobile `299:12459` in the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). This comparison used a disposable Windows package, three synthetic ACP tool updates, and the existing test-only plan stream controller. The canonical `App` and `Data` were not opened or changed.

| State | Live Figma | Disposable package | Measured result |
| --- | --- | --- | --- |
| Desktop, 1440 × 900 | [Frame](CHAT_TOOL_PLAN_DESKTOP_FIGMA_273-12914.png) | [Capture](CHAT_TOOL_PLAN_PACKAGE_1440.png) | Tool group x388–1308, width 920, height 188 across three rows. Figma uses the same 920px width and about 185px total row stack. Collapsed plan is x388–1308, 920×51 versus Figma 920×52. |
| Mobile, 393 × 852 | [Frame](CHAT_TOOL_PLAN_MOBILE_FIGMA_299-12459.png) | [Capture](CHAT_TOOL_PLAN_PACKAGE_393.png) | Three tool rows span x16–377, width 361; group height 186 versus about 185 in Figma. Plan spans x16–377, 361×37, matching Figma. |
| Narrow mobile, 320 × 852 | Same mobile frame adapted | [Capture](CHAT_TOOL_PLAN_PACKAGE_320.png) | Tool and plan surfaces span x16–304, width 288. Document width equals 320px. |

The package shows `Success`, `Success`, and `Executing` on desktop; mobile shortens the active status to `Running`. The synthetic inputs supply `Auto-approved · 14 s`, `3 file changes`, and the search query. A stable assistant reply keeps its four actions visible before the tool rows. The plan shows `3/5` and `Check the build output` while the test runtime is processing. The plan starts collapsed; its button and a tool row both expanded on click. The [expanded capture](CHAT_TOOL_PLAN_EXPANDED_393.png) shows the details. The detail panel has a full neutral border, with no single-side accent rail. No renderer error or document overflow occurred at 1440, 393, or 320px.

At two sampled row points, Figma/package RGB differed by 0–2 per channel. The sampled plan surface differed by 0–1. TypeScript, Electron Vite, disposable Windows packaging, and the full desktop regression passed (**54 files / 400 tests**). These are synthetic visual and interaction checks. They do not prove a live model tool run, real plan updates across reload, physical iPhone rendering, or the full populated Chat frame. The synthetic active turn shows a Stop control in the composer; Figma's illustrative frame shows Send.
