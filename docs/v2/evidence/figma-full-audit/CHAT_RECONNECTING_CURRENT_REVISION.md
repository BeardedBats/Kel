# Current Figma Chat reconnecting — scoped package evidence

Live frames: [desktop `273:12681`](CHAT_RECONNECTING_DESKTOP_FIGMA_273-12681.png) and [mobile `299:12515`](CHAT_RECONNECTING_MOBILE_FIGMA_299-12515.png) in the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). Both were read directly. A disposable Windows package used an isolated conversation. A test-only renderer event supplied `reconnecting`, then `connected`; it did not stop or restart the engine. The canonical App and Data were untouched.

| Viewport | Disposable package | Measured notice | Result |
| --- | --- | --- | --- |
| 1440 × 900 | [Capture](CHAT_RECONNECTING_PACKAGE_1440.png) | x388–1308, y786–846, 920×60 | Matches the desktop frame bounds. |
| 800 × 900 | [Capture](CHAT_RECONNECTING_PACKAGE_800.png) | x200–600, 400×60 | Text stays in the notice; no document overflow. |
| 393 × 852 | [Capture](CHAT_RECONNECTING_PACKAGE_393.png) | x16–377, y708–756, 361×48 | Matches the mobile frame width and height; top is 1px above Figma. |
| 320 × 852 | [Capture](CHAT_RECONNECTING_PACKAGE_320.png) | x16–304, 288×48 | No document overflow. |

The desktop notice has Figma's amber full outline, 12px radius, frosted surface, exact text, and Restart engine action. The mobile notice has the neutral full outline, 14px radius, shorter text, and Restart action. No single-side accent border appears. In both packaged states, the composer and duplicate global notice were hidden. Sending `connected` removed the notice and restored the composer. No renderer error occurred. Restart was not clicked, so this check does not prove a real engine outage, restart, queued-message delivery, or recovery of durable work. The desktop fixture has no Figma-style Project metrics footer; broader populated Chat parity remains open.

TypeScript, Electron Vite, disposable Windows packaging, and the full desktop suite passed (**54 files / 400 tests**). The installed App still packages `8c67121` pending broader current-Figma acceptance. Physical iPhone rendering remains unverified.
