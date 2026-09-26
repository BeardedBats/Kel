# Desktop populated Skills — source verification

Authority: current [Skills frame 311:3536](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=311-3536). The existing informational row structure remains. The desktop panel now uses the specified two-layer fill: blue at 6% over navy at 22%, a continuous neutral outline, and a 16px radius. Long imported names and descriptions wrap within the panel. Mobile and custom panel colors remain unchanged.

Three synthetic skills were imported through the real isolated host service. Each remained custom and non-auto-injected. Their names use an audit prefix to avoid existing built-in names. The initial attempt encountered the built-in pdf name, stopped, and removed its one owned import. No built-in skill was overwritten. Final import, list, and reload passed for all three audit skills. No skill execution or assistant attachment ran.

| Source render | 1440px | 800px |
| --- | --- | --- |
| Populated card | [Screenshot](DESKTOP_SKILLS_POPULATED_SOURCE_1440.png), 670×224, x613/y183 | [Screenshot](DESKTOP_SKILLS_POPULATED_SOURCE_800.png), 388×224, x371/y179 |
| Typical row | 58px | 58px |
| Long text | [Screenshot](DESKTOP_SKILLS_LONG_SOURCE_1440.png), 125px row | [Screenshot](DESKTOP_SKILLS_LONG_SOURCE_800.png), 229px row |

Both widths had zero document overflow, zero name/description overflow, and zero renderer errors. The long-text case imported a fourth synthetic skill through the same real service. All four imports were deleted through that service after the check. Synthetic import history and source files remain inside the existing bounded temporary stack. No canonical App or Data request ran.

TypeScript and the final Electron Vite source build passed. This CSS-only change used measured render checks; no new implementation-mirroring unit tests were added. The earlier 63-file/437-test suite remains evidence for the preceding Kibble increment, not a rerun for this change. Package proof waits for the larger desktop milestone. The Skills detail/import-history routes still redirect elsewhere; no detail interaction is claimed.
