# Current Figma mobile approval details — scoped package evidence

The live [mobile Approval details frame `299:12281`](CHAT_APPROVAL_DETAILS_MOBILE_FIGMA_299-12281.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). A disposable Windows package used an isolated engine approval. The canonical App and Data were untouched.

| Viewport | Disposable package | Measured sheet | Result |
| --- | --- | --- | --- |
| 393 × 852 | [Capture](CHAT_APPROVAL_DETAILS_PACKAGE_393.png) | x0–393, y419–852, 393×433 | Matches Figma's sheet bounds, 20px top radius, 24px blur, and Approve button at x17/y723. |
| 320 × 852 | [Capture](CHAT_APPROVAL_DETAILS_PACKAGE_320.png) | x0–320, y419–852, 320×433 | No document overflow; content remains inside the sheet. |

The detail uses Figma's glass material, full top outline, amber shield/title, three plain-language sections, Always allow for this project, Approve, and Deny. The synthetic build-command approval rendered the same action, reason, and refusal copy as the frame. Decision buttons use the existing durable approval request path. Escape closed the sheet; no renderer error occurred. Decisions were not submitted during this visual check, so packaged approval resolution remains unverified. The desktop dialog remains separate.

TypeScript, the focused approval tests (**2 passed**), Electron Vite, and disposable Windows packaging passed. The underlying approval engine suite previously passed **28 tests**. Windows chrome and synthetic conversation content behind the scrim differ from the iPhone frame; physical iPhone rendering remains unverified.
