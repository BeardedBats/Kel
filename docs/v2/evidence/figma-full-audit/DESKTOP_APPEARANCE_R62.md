# Desktop Dark Appearance — r62 scope

**Authority:** Kel Design System, Screens FINAL `186:1097` and the shared Dark components. **Source:** the r62 Appearance changes retained on canonical `main`. **Evidence:** [1440px capture](key/r62-appearance-1440.png), [800px capture](key/r62-appearance-800.png), [Add Theme dialog](key/r62-add-theme-dialog.png), and [measurements](r62-appearance-check.json).

At 1440px, the Theme card sits at x613/y183 and measures 670×180px. Theme colors starts at x613/y375 and measures 670×458px. Both align with the scaled FINAL frame. The Dark tile is selected and its check uses the `#7FA0FF` Foundation color. Restore all colors is plain text without a filled button edge. The 800px capture has no horizontal document overflow.

The packaged Add Theme dialog shows the current functional entry point and its default state. FINAL does not depict this dialog, so its fields follow the established Dark component treatment. The record does not prove saving a custom theme, the native color picker, Light labels, every hover/error state, or product-wide Figma parity. The FINAL sample shows a changed background value; the package shows its own default value, which is a state difference rather than a token mismatch.

The r62 candidate and test root were removed during consolidation. The installed canonical app was built from source including the r62 change. Its artifact hashes and data preservation are recorded in `docs/CONSOLIDATION_STATUS.md` and `Tools/consolidation/final-verification.json`.
