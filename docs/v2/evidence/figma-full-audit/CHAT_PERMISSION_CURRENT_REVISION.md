# Current Figma mobile Chat Permission sheet — scoped package evidence

The live [mobile Permission frame `299:12418`](CHAT_PERMISSION_CURRENT_FIGMA_299-12418.png) came from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). Its five options, selected Plan Mode, sheet material, and bounds were compared with a disposable Windows package.

| Width | Disposable package | Measured result |
| --- | --- | --- |
| 393 × 852 | [Capture](CHAT_PERMISSION_CURRENT_PACKAGE_393.png) | Sheet x0/y447, 393×405, exactly Figma's bounds. Title y479 and first choice y528 match. Five options fit; selected Plan Mode shows a check. Sampled background channels differ by 0–4 near the middle. |
| 320 × 852 | [Capture](CHAT_PERMISSION_CURRENT_PACKAGE_320.png) | Same 405px sheet height. All five choices fit x17–297, with zero document overflow. |

The sheet has a 20px top radius, 24px backdrop blur, continuous edge, full-width glass gradient, and no accent rail. The title returns to the main action menu at both widths. No renderer error appeared. TypeScript, the full desktop suite **54 files / 400 tests**, Electron Vite, and disposable Windows packaging passed. Canonical App and Data were untouched.

The isolated ACP session initialized but returned no mode catalog. A session-gated test injector supplied the five Figma sample choices to verify the rendering; production choices still come from the runtime. No live mode switch was submitted, and this check does not prove provider support for those modes. The Windows titlebar, chat content, and font rasterization differ from the iPhone frame.
