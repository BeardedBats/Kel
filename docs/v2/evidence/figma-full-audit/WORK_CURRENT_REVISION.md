# Current Figma mobile Work — scoped package evidence

The live [mobile Work frame `299:13910`](WORK_CURRENT_FIGMA_299-13910.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). A disposable Windows package used an isolated engine with zero jobs and zero continuation rows. The canonical App and Data were untouched.

| Width | Disposable package | Measured result |
| --- | --- | --- |
| 393 × 852 | [Capture](WORK_CURRENT_PACKAGE_393.png) | Jobs card x16/y114, 361×75; Waiting x16/y201, 361×75; Team x16/y288, 361×75. Figma's third card starts about y289. |
| 320 × 852 | [Capture](WORK_CURRENT_PACKAGE_320.png) | The three cards fit x16–304 with zero document overflow. |

The disabled Save as a recipe control no longer takes space in this empty mobile state. It remains available when an active job can use it. The back control uses the current mobile Figma arrow and returned to `/projects`. Card copy, padding, gap, border, radius, shadow, and fill use the current Figma component values. No renderer error appeared. TypeScript, the full desktop suite **54 files / 400 tests**, Electron Vite, and disposable Windows packaging passed.

This is scoped empty-state geometry and navigation evidence, **not full mobile parity**. The package uses Windows titlebar and font rasterization; its card pixels differ slightly from Figma despite the same source fill and border values. It did not run a job or verify populated Work. The fifth Kibble tab awaits a product decision. Work still reads the existing default/global engine scope; project selection is open.
