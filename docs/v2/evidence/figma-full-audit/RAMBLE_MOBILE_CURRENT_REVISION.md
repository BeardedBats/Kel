# Current Figma mobile Ramble — scoped package evidence

The live [Ramble list `299:12588`](RAMBLE_MOBILE_CURRENT_FIGMA_299-12588.png), [transcript `299:12782`](RAMBLE_MOBILE_CURRENT_FIGMA_299-12782.png), and [vetting sheet `299:12871`](RAMBLE_MOBILE_CURRENT_FIGMA_299-12871.png) were read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System) on 2026-09-25. The first two frames were compared with a disposable Windows package and five synthetic engine recordings. The third frame is **not verified**: no live vetting preview was opened from this route.

| State | Disposable package | Measured result |
| --- | --- | --- |
| List, 393 × 852 | [Capture](RAMBLE_MOBILE_CURRENT_PACKAGE_LIST_393.png) | Search x16/y115, 361×44; folder card x16/y218, 361×64; recording card x16/y342; New recording x16/y712, 361×44. These match the Figma bounds. |
| List, 320 × 852 | [Capture](RAMBLE_MOBILE_CURRENT_PACKAGE_LIST_320.png) | Cards and the fixed record action stay within x16–304. No horizontal overflow. |
| Transcript, 393 × 852 | [Capture](RAMBLE_MOBILE_CURRENT_PACKAGE_DETAIL_393.png), [More open](RAMBLE_MOBILE_CURRENT_PACKAGE_MORE_393.png) | Status begins x18/y109; document x16/y142, 361×558; Copy x16/y712, 307×44; More x333/y712, 44×44. Figma places the card at y143 and Copy at y713. |
| Transcript, 320 × 852 | [Capture](RAMBLE_MOBILE_CURRENT_PACKAGE_DETAIL_320.png) | Document x16–304, actions x16–304. Text scrolls inside the card. No horizontal overflow. |

The mobile list now uses the current menu, search, folder, and microphone icons. Folder and recording rows use the current glass cards and stacked metadata. New recording uses the existing recording path. The menu opens the existing navigation drawer. The transcript uses the current Saved row, scrollable card, blue Copy transcript action, and More menu; its existing rename, upload, API key, record-more, and combine actions remain reachable. No microphone recording, clipboard write, rename, merge, or vetting decision was submitted. The package reported no renderer errors.

This is scoped geometry and interaction evidence, **not exact pixel parity**. The synthetic library has five recordings; Figma shows four with different names, dates, durations, and transcript text. Existing mobile folder rename/delete icons remain visible where the frame has no controls. The canonical fifth Kibble tab remains pending Nick's placement decision. The disposable Windows package has native titlebar controls where the Figma phone frame has iOS status chrome. Its font rasterization appears heavier than Figma despite loading the specified local Instrument Sans and SF Pro Text faces. Real phone/PWA rendering and the vetting sheet still need direct acceptance.

Desktop TypeScript, focused Ramble tests (**2 files / 7 tests**), the full desktop suite (**54 files / 400 tests**), Electron Vite, and disposable Windows packaging passed. The canonical App remains at `8c67121`. All synthetic data stayed under `%TEMP%`; canonical Data was untouched.
