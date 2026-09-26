# Desktop Light menus — source repair

Desktop Light now uses existing semantic colors for Model, Project, Memory review, Permission, Attach, and Slash menus. Shared desktop geometry remains unchanged. Current rows and hover states use the Light accent fill. Project search, model scope, and Memory labels remain readable. Neutral image icons in menu, navigation, and catalog rows receive a dark tint. No accent rail was added. Dark and mobile rules remain unchanged.

The current Figma Foundations board provides the Dark palette, without a complete Light palette. This repair preserves desktop geometry and measures Light readability. It does not establish exact Light color parity.

An isolated Electron app rendered current source and selected Light through the real theme control. All six menus passed at 1440px and 800px. Model is 280px wide, Project 320px, Memory 440×236, Permission 300×286, Attach 220px, and Slash 340px. There was no document overflow, internal overflow, clipping, or renderer error. Escape and command selection passed. Memory decisions and the permission catalog were intercepted. Native file selection was intercepted and canceled. No provider request, file write, or live memory decision ran. Dark was restored afterward.

Computed label contrast uses ancestor-composited backgrounds. The lowest measured word label was 4.81:1; the lowest measured mark was 4.76:1. The gradient-backed Accept button was excluded from this assertion. Icon tint was visually inspected; pixel-level icon contrast remains unmeasured. This is computed-style proof, not anti-aliasing analysis.

Screenshots cover each menu at both widths: [Model 1440](DESKTOP_LIGHT_MODEL_MENU_1440.png), [800](DESKTOP_LIGHT_MODEL_MENU_800.png); [Project 1440](DESKTOP_LIGHT_PROJECT_MENU_1440.png), [800](DESKTOP_LIGHT_PROJECT_MENU_800.png); [Memory 1440](DESKTOP_LIGHT_MEMORY_REVIEW_1440.png), [800](DESKTOP_LIGHT_MEMORY_REVIEW_800.png); [Permission 1440](DESKTOP_LIGHT_PERMISSION_MENU_1440.png), [800](DESKTOP_LIGHT_PERMISSION_MENU_800.png); [Attach 1440](DESKTOP_LIGHT_ATTACH_MENU_1440.png), [800](DESKTOP_LIGHT_ATTACH_MENU_800.png); [Slash 1440](DESKTOP_LIGHT_SLASH_MENU_1440.png), [800](DESKTOP_LIGHT_SLASH_MENU_800.png).

The final source build passed. The prior full desktop regression passed 63 files / 440 tests. It was not repeated for this CSS-only repair. Package proof waits for the next larger desktop milestone. The latest disposable package remains 41a73f5. Canonical App remains 8c67121; durable Data was untouched.
