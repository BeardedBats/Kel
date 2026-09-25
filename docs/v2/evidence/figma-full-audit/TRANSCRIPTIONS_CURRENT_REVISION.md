# Current Figma populated Transcriptions — scoped package evidence

The live [desktop Transcriptions frame `189:4032`](TRANSCRIPTIONS_CURRENT_FIGMA_189-4032.png) was read directly from the [Kel Design System](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System). A disposable Windows package used two synthetic recordings created through the isolated engine's transcription API. It did not read or change the canonical Data root.

| Viewport | Disposable package | Result |
| --- | --- | --- |
| 1440 × 900 | [Capture](TRANSCRIPTIONS_CURRENT_PACKAGE_1440.png) | Document panel x613–1283, y231–851, 670×620. Figma's panel is x613–1283, y229–847, 670×618. |
| 800 × 900 | [Top](TRANSCRIPTIONS_CURRENT_PACKAGE_800.png), [scrolled footer](TRANSCRIPTIONS_CURRENT_PACKAGE_800_FOOTER.png) | The long transcript scrolls inside the page. All four footer actions remain reachable. No horizontal overflow. |

The populated document now uses Figma's amber title, right-aligned Saved check and settings icon, header rule, Upload Audio link, blue Record More, red Record, three quiet footer actions, and blue Combine. The seven icons are local assets exported from the current Figma frame. The footer starts at x650/y794 in the package, 3px below Figma's buttons. The body uses the current frame's SF Pro Text 15px/26px values; the synthetic words and Windows font rendering differ from Figma's sample. The package loaded the font and reported weight 400. No single-side accent border appears.

Both synthetic records have one-second local WAV files, so Download Audio and Combine were enabled. Combine opened its existing dialog after scrolling at 800px. No merge, upload, microphone capture, download, or clipboard write was submitted. The selected transcript was chosen by the existing newest-record rule. No renderer error appeared.

TypeScript, focused Transcriptions tests (**2 files / 7 tests**), Electron Vite, and disposable Windows packaging passed. The canonical App still packages `8c67121` until broader current-revision acceptance is green.
