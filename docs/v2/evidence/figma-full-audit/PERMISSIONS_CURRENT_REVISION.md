# Current Figma mobile Permissions — scoped package evidence

The live [mobile Permissions frame `299:14218`](PERMISSIONS_CURRENT_FIGMA_299-14218.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). A disposable Windows package used isolated configuration and data. The permission digest came from that engine state; it was not copied from the Figma sample.

| Width | Disposable package | Measured result |
| --- | --- | --- |
| 393 × 852 | [Capture](PERMISSIONS_CURRENT_PACKAGE_393.png) | Active permissions x16/y114, 361×75; Access requests x16/y201, 361×75; Permission check x16/y288, 361×85. These match the current Figma card bounds within 1px. |
| 320 × 852 | [Capture](PERMISSIONS_CURRENT_PACKAGE_320.png) | All cards fit x16–304 with zero document overflow. The digest remains on one line. |

The mobile page hides its desktop header action and uses the digest row to open the existing check controls. The row's `aria-expanded` changed to `true` when clicked. The real digest stayed dynamic. No renderer error appeared. TypeScript, the full desktop suite **54 files / 400 tests**, Electron Vite, and disposable Windows packaging passed. Canonical App and Data were untouched.

This checks the isolated empty state and geometry, not populated permission grants or access requests. Windows titlebar and font rasterization differ from the phone frame. The fifth Kibble tab still awaits a product decision.
