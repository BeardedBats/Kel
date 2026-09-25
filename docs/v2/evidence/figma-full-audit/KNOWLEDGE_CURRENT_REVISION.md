# Current Figma mobile Knowledge — scoped populated package evidence

The live [mobile Knowledge frame `299:14371`](KNOWLEDGE_CURRENT_FIGMA_299-14371.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). The [earlier empty-state gap](KNOWLEDGE_CURRENT_GAP.md) led to a bounded engine fixture with two proposals and five real project-map sections. The fixture used only disposable data.

| Width | Disposable package | Measured result |
| --- | --- | --- |
| 393 × 852 | [Capture](KNOWLEDGE_CURRENT_PACKAGE_393.png) | Suggestions card x16/y114, 361×265, 2px shorter than Figma. Map begins y391, 2px above Figma; its five real sections make it taller than Figma's three sample rows. |
| 320 × 852 | [Capture](KNOWLEDGE_CURRENT_PACKAGE_320.png) | Populated cards fit x16–304 with zero document overflow. |

The mobile layout uses the current Figma card, suggestion actions, map rows, and map icon. It reads proposal summaries, reasons, status, and sections from the engine. It does not insert Figma's sample choices as user data. The isolated **Not now** action deferred a proposal; **Refresh** reran the map. No page error appeared. TypeScript, the desktop suite with the updated source assertion, Electron Vite, and disposable Windows packaging passed. Canonical App and Data were untouched.

This remains scoped. The fixture yielded five sections rather than Figma's three, and the two proposals appeared newest first. Accept and Reject were not submitted in the package. Windows titlebar, font rasterization, and Kibble navigation still differ from the phone frame.
