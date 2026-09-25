# Current Figma mobile Ramble vetting — scoped package evidence

The live [mobile Vetting answers frame `299:12871`](RAMBLE_MOBILE_CURRENT_FIGMA_299-12871.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). The disposable package used a synthetic design-vetting session and transcript in isolated `%TEMP%` data. The existing engine's `transcript_preview` returned two requirements and one unresolved question. No preview text or answer was hard-coded into production.

| Width | Disposable package | Result |
| --- | --- | --- |
| 393 × 852 | [Capture](RAMBLE_VETTING_CURRENT_PACKAGE_393.png) | Sheet x0/y400, 393×452; title x17/y428; Accept all x17/y723, 359×44. Figma's sheet starts near y400 and Accept all starts y723. |
| 320 × 852 | [Capture](RAMBLE_VETTING_CURRENT_PACKAGE_320.png) | Sheet and buttons fit x0–320 with no horizontal overflow. |

The More menu now opens this engine-backed preview. The sheet shows dynamic requirements, concerns, open questions, and mapped answers when present. Its edit control opens the existing transcript text editor. Check again reran the read-only preview; Escape closed the sheet. Process batch and Accept all still use the existing engine action, but neither was submitted in this check. No renderer error appeared. The focused engine vetting transcript test passed **1 test**; desktop TypeScript, the full desktop suite **54 files / 400 tests**, Electron Vite, and disposable Windows packaging passed.

This is scoped geometry and preview behavior, **not full pixel parity**. The test phrases differ from Figma's normalized sample copy. The engine returned one low-confidence proposal for the whole text; it did not identify Figma's second row as uniquely needing “Check,” so the package does not invent that badge. Windows font rasterization and native titlebar differ from the phone frame. Physical iPhone/PWA rendering and decision submission remain open. The canonical App remains at `8c67121`, and canonical Data was untouched.
