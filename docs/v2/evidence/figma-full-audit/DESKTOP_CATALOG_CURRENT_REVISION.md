# Desktop Assistants and Skills — current Figma revision

Current Figma [Assistants `311:3140`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=311-3140) and [Skills `311:3536`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=311-3536) show one glass card per page. Each card has a 15px amber title and 58px icon, name, and description rows. The source now uses those titles and row structures for actual user assistants and custom skills. The desktop Skills heading reads “Skills”; its extra Usage Tip card is hidden on desktop. Empty-state handling remains for an actual empty catalog. Skill rows are informational because the current detail route redirects to an unrelated page.

The isolated Windows package showed the real Kel assistant in a 670×108 card at [1440px](DESKTOP_ASSISTANTS_PACKAGE_1440.png) and a 388×108 card at [800px](DESKTOP_ASSISTANTS_PACKAGE_800.png). The isolated profile had no custom skills, so the Skills card showed its truthful empty state at [1440px](DESKTOP_SKILLS_PACKAGE_1440.png) and [800px](DESKTOP_SKILLS_PACKAGE_800.png). It measured 670×215 and 388×215. Both cards start at x613/y183 at 1440px and x371/y179 at 800px. Neither page overflowed or reported a renderer error. TypeScript, 54 desktop test files with 401 tests, Electron Vite, and Windows packaging passed.

Figma's Release writer, Research buddy, xlsx, pdf, and roundup entries are illustrative and were not inserted into the user's catalog. The real Kel assistant retains its stored description, which differs from Figma's sample copy. A populated custom-skill package state remains unverified. The canonical App and Data were untouched.


**2026-09-26 continuation:** [Populated Skills source checks](DESKTOP_SKILLS_POPULATED_SOURCE.md) now pass real isolated imports/reload at both widths. The panel fill was repaired and long text wraps. Typical rows remain 58px. Package proof remains open.
