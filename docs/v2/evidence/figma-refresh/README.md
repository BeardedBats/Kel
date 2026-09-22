# Figma refresh — dark shell

Source: [Screens FINAL](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=185-2), [Foundations](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=139-2), and [Components](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=136-2). The layout source is Screens FINAL. This work starts from `integration/v2` at `466c99b` on an isolated branch.

## Implemented

- Shared 256px sidebar, six persistent section links, 920px in-chat frame, 200px frame navigation, and source SVG icons. Existing routes and real state remain wired.
- Projects, Work, Activity, Permissions, Knowledge, scheduled tasks, Providers, Diagnostics, onboarding, Connections, and Settings share the new frame. The Projects summary keeps three cards; the full recipe library opens from Recipes.
- Ramble keeps its separate recording layout. Transcriptions has an in-chat route that uses the existing recording state and actions.
- Dark canvas, glass frame, inner panels, spacing, shadow, and type use the source values. The body font is SF Pro Text; headings use Instrument Sans.
- The Projects recipe category response now accepts the engine's `{name,count}` rows. This fixes a render error found during visual navigation.

## Rendered comparison

The 1440×900 reference and built pairs are [Work](source-work.png) / [built](built-work.png), [Activity](source-activity.png) / [built](built-activity.png), [Projects](source-projects.png) / [built](built-projects.png), [Settings](source-settings.png) / [built](built-settings.png), and [Ramble](source-ramble.png) / [built](built-ramble.png). The built images use an isolated, empty data root. The Figma examples contain conversations, active work, a recording, and a changed theme state. Those data differences are not filled with mock content.

Permissions, scheduled tasks, Providers, Diagnostics, and onboarding were also inspected against their Screens FINAL renders. Their content changes with live data. The empty local root does not reproduce the populated Figma examples.

Measured in the built WebUI: the Work and Settings frames are `(388,112,920,760)`, the Ramble panel is `(388,93,920,783)`, and the Transcriptions panel is `(613,231,670,620)`. Activity starts at `(613,183,670,85)` and the Projects summary starts at `(613,185,670,85)`. These match the source layout measurements. The seven compared routes have no page error or horizontal overflow at 1440px.

## Checks

- `bunx tsc --noEmit` passed.
- `bun run package` passed.
- 22 dark routes opened with no page error or horizontal overflow at 1440px.
- Work, Projects, Settings, Ramble, and Transcriptions opened with no page error or horizontal overflow at 1024px, 393px, and 360px.
- The Projects link opened the real Knowledge route after the category fix.

## Open decisions and limits

- Screens FINAL includes Assistants and Skills in Settings. Kel's current product direction retired those as visible sections. Their routes remain in the app, but this branch does not restore those navigation items without a product decision.
- The screenshots prove the built WebUI on an isolated root. They do not prove an installed candidate or populated-state pixel fidelity.
- These comparisons establish the shared frame and sampled content layouts. A later audit must check every populated component state before anyone claims complete pixel fidelity.
- This branch does not merge with Kun's active audit or replace the V2 candidate. Merge and candidate verification belong after the parallel work is reconciled.
