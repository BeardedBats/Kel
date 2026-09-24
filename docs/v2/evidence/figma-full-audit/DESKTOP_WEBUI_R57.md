# Desktop Dark WebUI comparison — r57

**Authority:** Kel Design System, `Screens - FINAL` `188:2240`, Foundations `139:2`, and Components `136:2` (including Lightbox `147:162` and Input `148:229`). **Package:** `C:\Users\Nick\KelV2Candidate.r57`, source `cafe10e32abcf53f4d65ca00fb9814c4f44865c8`, Dark, 100% zoom. The `r43-populated` roots are disposable.

The [r54 1440px baseline](key/r54-webui-1440.png) had an extra desktop sentence, omitted the three-part step strip, and used longer rows. Its first WebUI card began at y266 and measured about 258px high. Its Login Info card began at y548 and measured about 212px. FINAL places the strip at y183, the WebUI card at x613/y228, and Login Info at x613/y453.

The [r57 1440px package](key/r57-webui-1440.png) shows the FINAL step strip and first-step copy. It uses the 15×15 activity icon from the Figma node, 16px banner text, 49px switch rows, and 34px credential fields. [Measurements](r57-webui-dialogs.json) put WebUI at x613/y228, 670×213, Login Info at x613/y453, 670×190, and the three-segment strip at x613/y183, 670×3. The [800px package](key/r57-webui-800.png) has no horizontal document overflow.

Username and password editing are working overlays with no full FINAL screen. They now use the Dark Lightbox treatment and Input controls from Components. [The username dialog](key/r57-webui-username-dialog.png) and [password dialog](key/r57-webui-password-dialog.png) opened in the packaged app. Both closed with Escape after the transition. An r56 intermediate exposed a second border inside password fields; the r57 [focus capture](key/r57-webui-password-focus.png) and [computed styles](r57-webui-field.json) show a borderless inner input, one outer field border, and the blue focus edge and glow. No credential change was submitted.

The packaged profile was on step 1 with WebUI disabled. Later steps, remote access, and a live response remain unverified. Runtime username and password values differ from Figma sample data. This comparison closes the measured first-step desktop layout and dialog component gaps; it does not establish exact product-wide parity.
