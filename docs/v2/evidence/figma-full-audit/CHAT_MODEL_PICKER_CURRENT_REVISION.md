# Current Figma mobile Chat model picker — scoped package evidence

The live [mobile Model picker `299:12372`](CHAT_MODEL_PICKER_MOBILE_FIGMA_299-12372.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). A disposable Windows package used isolated data and an existing test conversation. The canonical App and Data were untouched.

| Viewport | Disposable package | Measured sheet | Result |
| --- | --- | --- | --- |
| 393 × 852 | [Capture](CHAT_MODEL_PICKER_PACKAGE_393.png) | x0–393, y442–852, 393×410 | Matches Figma's sheet bounds, handle, title, tabs, 20px top radius, 24px blur, and Add model button at x17/y773. |
| 320 × 852 | [Capture](CHAT_MODEL_PICKER_PACKAGE_320.png) | x0–320, y442–852, 320×410 | No document overflow; choices scroll inside the sheet. |

The sheet uses Figma's 60% navy scrim, 40% blue glass layer, 8% ice wash, full top outline, and no accent rail. The composer menu and Chat error action open this picker. The tabs switch between this chat and the default for new chats. Escape closes the sheet. The package showed live options from the isolated engine, so its labels and Automatic selection differ from Figma's illustrative DeepSeek V3 selection. This is a data difference, not a fabricated screenshot match.

The isolated conversation resolved to its engine record. Choosing Claude (built-in) set the per-chat choice, and choosing Automatic restored it. No model request was sent. Add model opened `/settings/model`. Default-choice persistence was not exercised. The package still shows Windows chrome behind the scrim; physical iPhone rendering remains unverified.

TypeScript, Electron Vite, disposable Windows packaging, and the full desktop suite passed (**54 files / 400 tests**). No renderer error occurred.
