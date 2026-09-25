# Current Figma Chat — scoped package evidence

Live Figma frames: desktop Chat `185:4284`, mobile Chat `299:11571`, and mobile drawer `299:11583` in the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). The comparison uses a disposable `electron-builder --dir` package. Its two-turn `Website Redesign` conversation exists only in an isolated `%TEMP%` database. The canonical `App` and `Data` were not opened or changed.

| State | Live Figma | Disposable package | Result |
| --- | --- | --- | --- |
| Mobile Chat, 393 × 852 | [Frame](CHAT_MOBILE_FIGMA_299-11571.png) | [Capture](CHAT_MOBILE_PACKAGE_393.png) | User text occupies x97–377 and two lines. The four assistant actions are visible. Composer is x16, width 361, height 46. |
| Mobile drawer, 393 × 852 | [Frame](CHAT_DRAWER_FIGMA_299-11583.png) | [Capture](CHAT_DRAWER_PACKAGE_393.png) | Drawer width 310 versus Figma 311. Kel mark x16/y68, Search x16/y112/278×39, New Chat x16/y764/278×44; each differs from Figma by about 1px. Search opens the real conversation search dialog. |
| Desktop Chat, 1440 × 900 | [Frame](CHAT_DESKTOP_FIGMA_185-4284.png) | [Capture](CHAT_DESKTOP_PACKAGE_1440.png) | Read and captured. This small fixture cannot verify the five-step plan, project chip, footer metrics, or populated sidebar. |

The mobile drawer's dark background was sampled from both images. Figma RGB at x150/y20, y350, y650, y740 was `(29,48,83)`, `(21,38,71)`, `(15,32,64)`, `(14,32,69)`. The package measured `(29,48,83)`, `(23,41,75)`, `(17,35,68)`, `(16,35,70)`. The drawer uses a full-surface gradient; it has no single-side accent border.

The package used `KEL_DATA_DIR`, `AIONUI_DATA_DIR`, `KEL_HOST_DATA_DIR`, `AIONUI_MULTI_INSTANCE=1`, and `--user-data-dir` under one `%TEMP%` root. At 393, 320, and 1440px, document width equaled viewport width. No renderer page error occurred. TypeScript passed. The focused navigation and composer suites passed 2 files / 9 tests. Electron Vite and the disposable Windows package passed.

**Open:** the Figma phone frame includes iPhone status and home chrome; the Windows Electron viewport has a title bar. Figma has four bottom tabs, while production retains a fifth Kibble tab until its access path is decided. The app still shows attachment and mic controls in the mobile composer; Figma shows only plus and send. The desktop fixture has no live model turn, real project metrics, or populated plan. This is not product-wide Chat parity or physical iPhone proof.
