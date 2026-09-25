# Desktop Permissions — current Figma revision

Current Figma [Permissions `189:1758`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=189-1758) was read directly. An isolated package rendered the empty state at [1440px](DESKTOP_PERMISSIONS_EMPTY_PACKAGE_1440.png) and [800px](DESKTOP_PERMISSIONS_EMPTY_PACKAGE_800.png). At 1440px the three cards measured x613/y185, x613/y282, and x613/y379, all 670px wide. The first two measured 85px high, and Permission check measured 89px. At 800px they measured x371/y181, x371/y278, and x371/y375, all 388px wide with the same heights. No overflow or renderer error appeared. No source change was needed for this state.

The displayed guardrail digest comes from the isolated engine and differs from Figma's sample. Populated grants and access requests, resolving a request, and the Run check interaction remain open. Canonical App and Data were untouched.
