# Figma refresh — dark shell

Source: [Screens FINAL](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=185-2), [Foundations](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=139-2), and [Components](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=136-2). The layout source is Screens FINAL. This work starts from `integration/v2` at `466c99b` on an isolated branch.

## Implemented

- Shared 256px sidebar, six persistent section links, 920px in-chat frame, 200px frame navigation, and source SVG icons. Existing routes and real state remain wired.
- Projects, Work, Activity, Permissions, Knowledge, scheduled tasks, Providers, Diagnostics, onboarding, Connections, and Settings share the new frame. The Projects summary keeps three cards; the full recipe library opens from Recipes.
- Ramble keeps its separate recording layout. Transcriptions has an in-chat route that uses the existing recording state and actions.
- Dark canvas, glass frame, inner panels, spacing, shadow, and type use the source values. The body font is SF Pro Text; headings use Instrument Sans.
- The Projects recipe category response now accepts the engine's `{name,count}` rows. This fixes a render error found during visual navigation.
- Model and Archived now use the source empty-state spacing and icon treatment. Tools and About use the source card alignment. The Model page keeps its working Add Model action.
- Assistants and Skills appear in the Settings navigation at the source positions. Their pages read the existing assistant and skill stores and use the source empty cards, titles, and icons.

## Rendered comparison

The 1440×900 reference and built pairs are [Home](source-home.png) / [built](built-home.png), [Work](source-work.png) / [built](built-work.png), [Activity](source-activity.png) / [built](built-activity.png), [Projects](source-projects.png) / [built](built-projects.png), [Settings Appearance](source-settings.png) / [built](built-settings.png), [Settings Model](source-model.png) / [built](built-model.png), [Settings Assistants](source-assistants.png) / [built](built-assistants.png), [Settings Skills](source-skills.png) / [built](built-skills.png), [Settings Archived](source-archived.png) / [built](built-archived.png), and [Ramble](source-ramble.png) / [built](built-ramble.png). The built images use isolated data. The Figma examples contain conversations, active work, a recording, and a changed theme state. Those data differences are not filled with mock content. The isolated app has a saved Kel assistant, so its Assistants card shows that real row instead of the source empty state.

Permissions, scheduled tasks, Providers, Diagnostics, onboarding, Settings Tools, System, Remote / WebUI, Desktop Pet, and About were also inspected against their Screens FINAL renders. Their content changes with live data. The empty local root does not reproduce the populated Figma examples. WebUI mode shows browser-specific Remote / WebUI and Desktop Pet states; their desktop controls require a packaged-app comparison.

Measured in the built WebUI: the Work and Settings frames are `(388,112,920,760)`, the Ramble panel is `(388,93,920,783)`, and the Transcriptions panel is `(613,231,670,620)`. Activity starts at `(613,183,670,85)` and the Projects summary starts at `(613,185,670,85)`. Settings Model starts at `(613,183,670,320)` and its custom card at `(613,515,670,215)`. Archived starts at `(613,183,670,215)`. These match the source layout measurements within 1px. The ten compared routes have no page error or horizontal overflow at 1440px.

Assistants and Skills each start with a `(613,183,670,215)` card. The Skills Usage Tip starts at `(613,410,670,100)`. The navigation order and these bounds match Screens FINAL. The prior Settings screenshots were recaptured after restoring both entries.

## Checks

- `bunx tsc --noEmit` passed.
- `bun run package` passed.
- 22 dark routes opened with no page error or horizontal overflow at 1440px.
- Work, Projects, Settings, Ramble, and Transcriptions opened with no page error or horizontal overflow at 1024px, 393px, and 360px.
- The Projects link opened the real Knowledge route after the category fix.
- Home, Model, Tools, Archived, and About opened with no page error or horizontal overflow at 1440px after the final settings pass.
- Model, Tools, Archived, and About opened with no page error or horizontal overflow at 1024px, 393px, and 360px.
- Assistants and Skills opened with the correct active navigation row, no page error, and no horizontal overflow at 1440px, 1024px, 393px, and 360px.
- The built page resolves its heading to Instrument Sans and its body to SF Pro Text; both local font families loaded.

## Open decisions and limits

- Nick confirmed that Assistants and Skills belong in Settings. Their visible overview pages now follow Screens FINAL and show real stored rows. The Figma file specifies empty states without create or edit controls, so these pages are read-only. Populated-row layouts are a documented inference. The older management editor is not exposed by this change.
- The screenshots prove the built WebUI on an isolated root. They do not prove an installed candidate or populated-state pixel fidelity.
- Remote / WebUI and Desktop Pet render different content in browser mode. Their desktop-only controls remain unverified in this branch.
- These comparisons establish the shared frame and sampled content layouts. A later audit must check every populated component state before anyone claims complete pixel fidelity.
- This branch does not merge with Kun's active audit or replace the V2 candidate. Merge and candidate verification belong after the parallel work is reconciled.
