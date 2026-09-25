# Current Figma Chat approval — scoped package evidence

Live frames: desktop approval `273:1911` and mobile approval `299:11950` in the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). The comparison uses a disposable Windows package with an isolated Kel engine, host database, and profile. The canonical `App` and `Data` were not opened or changed.

| State | Live Figma | Disposable package | Measured result |
| --- | --- | --- | --- |
| Desktop, 1440 × 900 | [Frame](CHAT_APPROVAL_DESKTOP_FIGMA_273-1911.png) | [Capture](CHAT_APPROVAL_PACKAGE_1440.png) | Pending card x388–1308, 920×169; Figma x389–1308, about 919×168. Actions are 34px. The settled strip is 49px, about 1px taller than Figma. |
| Mobile, 393 × 852 | [Frame](CHAT_APPROVAL_MOBILE_FIGMA_299-11950.png) | [Capture](CHAT_APPROVAL_PACKAGE_393.png) | Pending card x16–377, 361×302; Figma x16–377, about 361×301. Approve is 44px. The command, body, and actions stay inside the full card. |
| Narrow mobile, 320 × 852 | Same mobile frame adapted | [Capture](CHAT_APPROVAL_PACKAGE_320.png) | Pending card x16–304, 288×302. Document width is 320px, with no horizontal overflow. |

At three desktop card points, sampled Figma/package RGB values were `(30,51,96)/(30,50,95)`, `(29,49,91)/(29,50,94)`, and `(28,48,90)/(28,48,91)`. The pending and settled cards use a continuous full border and surface gradient. Neither has a single-side accent border.

The isolated engine returned the exact command target `npm run build` and conversation title `Website Redesign`. The card displayed “It wants to run a build command in Website Redesign.” The engine announcement remained durable but was not duplicated above its anchored card. The packaged Details control opened. The settled card had no live decision buttons. No page error appeared at 1440, 393, or 320px.

Focused engine approval tests passed **28/28**; the new renderer approval tests passed **2/2**; TypeScript, Electron Vite, frozen engine build, and disposable Windows packaging passed. The packaged engine matched all **67/67** source modules and its SHA-256 matched the newly frozen engine (`0da29be4…`). The renderer test verified that a double click submits one engine decision with the mapped conversation ID. The packaged check did not submit a live approval or test an expired request. Existing engine approval tests cover resolution and expiry. Figma's sample conversation, phone status chrome, full desktop sidebar, and local fixture content differ from this synthetic chat. Product-wide Chat parity remains open.
