# Current Figma mobile Projects — scoped package evidence

The live [mobile Projects frame `299:13686`](PROJECTS_CURRENT_FIGMA_299-13686.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). A disposable Windows package used isolated `%TEMP%` data with one synthetic `Website Redesign` project. The canonical App and Data were untouched.

| Width | Disposable package | Measured result |
| --- | --- | --- |
| 393 × 852 | [Capture](PROJECTS_CURRENT_PACKAGE_393.png) | First card x16/y163, 361×296; Figma x16/y163, about 361×294. Kel card x16/y515, 361×149; Figma x16/y518, about 361×147. |
| 320 × 852 | [Capture](PROJECTS_CURRENT_PACKAGE_320.png) | Cards fit x16–304 with zero document overflow. Every row remains reachable. |

The mobile index now groups Work, Activity, Permissions, Knowledge, Recipes, and Scheduled tasks beneath the one available project name. Providers, Diagnostics, and Workspaces sit in the Kel group. Both cards use the current full border, radius, fill, row rhythm, and exact Figma icons. Work and Recipes rows navigated to their existing routes. No renderer error appeared. TypeScript, the full desktop suite **54 files / 400 tests**, Electron Vite, and disposable Windows packaging passed.

This is scoped geometry and route evidence, **not exact phone pixel parity**. Windows uses a native titlebar and different font rasterization. The fifth Kibble tab remains pending a product decision. When several projects exist, the heading stays `Projects` because no project selector has yet scoped these existing routes; this avoids naming the wrong project. The index groups routes visually, but Work and Knowledge still use their existing global/default engine scopes. Project selection and route scoping need a separate behavior pass.
