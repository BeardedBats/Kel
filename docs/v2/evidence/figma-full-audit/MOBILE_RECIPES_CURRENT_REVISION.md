# Mobile Recipes list and preview — implementation check

Current Figma [list `299:14428`](MOBILE_RECIPES_FIGMA_299-14428.png) and [preview `299:14477`](MOBILE_RECIPES_PREVIEW_FIGMA_299-14477.png) were read directly. The mobile page now uses engine recipes, search, favourites, categories, and actual step titles. Run still opens the existing input review before submission.

The disposable package rendered the [list at 393px](MOBILE_RECIPES_PACKAGE_393.png) and [320px](MOBILE_RECIPES_PACKAGE_320.png), plus the [preview at 393px](MOBILE_RECIPES_PREVIEW_PACKAGE_393.png) and [320px](MOBILE_RECIPES_PREVIEW_PACKAGE_320.png). Card x16/y115 and width 361 are within 1px of the list frame. Rows measure 57px. Preview opens and closes; the three real steps came from the engine. Both widths had zero document overflow and no renderer error. TypeScript, focused recipe tests **1 file / 4 tests**, Electron Vite, and disposable packaging passed.

Figma uses four sample recipes and a four-step sample preview. The isolated engine has five built-in recipes; none has a saved run. The package displays those real names and no fabricated success. Its category is `Uncategorised`, so the sample `Release` tab is absent. The Windows titlebar and font rasterization differ from iPhone chrome. Canonical App and Data were untouched.
