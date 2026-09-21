# Figma gaps and conservative production decisions

Source: Kel Design System, BlpVvZGuc9j9HhxUojIiJI. Final desktop frames and DS v2 components were inspected directly.

| Missing or conflicting state | Closest source | Decision | Code |
|---|---|---|---|
| Tools group and Kibble have no frame | Nav row 143:87, Card 137:6, Button 136:28 | Add a data-driven Tools group. Keep /transcription and /dogfood identifiers. | KelToolsSection, ShellNavRow, dogfood/index.tsx |
| Existing Work, Projects, Activity and Permissions entry points are absent from final chat sidebar | Nav row 143:87 | Retain real entry points above history. Do not hide working routes. | SiderNav/KelNavEntries |
| No mobile or intermediate frame exists among 22 final frames | Desktop sidebar 256px, composer 148:187, existing mobile drawer | Keep existing drawer, bottom control sheet, safe-area/PWA behavior. Use 44px touch targets, wrap controls, and stack Ramble below 980px. | kel-shell.css, existing Layout/mobile components |
| Final screen card fills and titles differ from detached DS v2 Card | 76:3959 versus 137:6 | Use final frame glass. The user-selected Foundations typography governs all card titles: Instrument Sans Bold 15/20, amber #FFC481. | kel-shell.css |
| Final screen body uses Inter; DS v2 uses SF Pro | 137:6, Typography variables | Follow the user-selected DS v2 Foundations typography: Instrument Sans and SF Pro Text. Card titles are amber, Bold 15/20. Inter is removed. | kelFonts.ts, kel-shell.css |
| Light theme has no final frame | Existing theme palette + v2 geometry | Preserve the light theme, custom color controls, font controls and custom CSS. | kel-shell.css, applyTheme.ts |
| Live state differs from sample content | Final Home 94:1585 | Show real attention lines, provider holds and empty history. Never insert sample conversations or fake status. | KelResumptionBrief, existing provider notice/history |
| Desktop window/navigation controls absent from Figma | Existing titlebar | Retain controls in the top-right area. Ramble reserves 22px above its toolbar to avoid overlapping native window controls; its document begins at y90 instead of y68 at 1440px. | kel-shell.css |
| Projects deep links previously used tabs | Final Projects 76:3893 | Show all three panels as specified. Existing deep links scroll to their section. Keep all actions and populated tables. | projects/index.tsx |
| Model unavailable; loading/error/empty data | Card 137:6, Button variants 136:28 | Keep real failure/retry/recovery copy and existing disabled rules using canonical surfaces. | existing Kel primitives, kel-shell.css |
| Additional Ramble controls, search, key setup, vetting, send to chat | Transcriptions 76:4603 | Keep actions in the existing library/document structure. Use canonical buttons and sheets. | transcription/index.tsx |
| Copy/fork controls on touch | Chat turn 137:68, final Chat 76:3001 | Use native buttons. Show applicable actions on touch and keep timestamps above text. Fork appears only when backend supports it. | MessageText.tsx |
| Reusable focus and reduced-motion states | Input 148:229 focus token, existing accessibility contract | Full focus outline; preserve keyboard semantics; suppress optional animation under reduced motion. | kel-shell.css |
| No connected model or Muse credential in isolated verification data | Existing unavailable/provider state | Verify honest holds and request wiring; do not invent successful model or Muse replies. Fixture data is confined to automated tests. | tests and evidence |
| Provider details exceed the four compact source rows | Providers 76:3996 | Use expandable integration rows. Keep key setup, model capabilities, preflight options and credential actions inside those rows or disclosure panels. Never fabricate passing preflight checks. | providers/index.tsx |
| Onboarding has no writable autonomy-mode contract matching the source select | Onboarding 123:1789 | Render all five source sections with real engine data. Open the existing Permissions route for edits. Keep Next, Back, Skip and completion persistence. | onboarding/index.tsx |
| Source project folder picker cannot map directly to the existing project record API | Onboarding 123:1789, Projects 76:3893 | Change opens real Projects. Show the returned project name rather than invent a local folder. | onboarding/index.tsx |
| Assistants and Skills frames refer to retired routes | 76:3474 and 76:3503 | Preserve existing route redirects and the single-assistant product. Do not restore retired configuration pages. | existing Router.tsx |
| Two System frames disagree | 112:10259 and 124:2028 | Use amber-title 112:10259, consistent with final Appearance. Preserve real backup paths, restore controls and explanations. | SystemModalContent, KelDataCard, kel-shell.css |
| About lacks an existing combined license inventory and direct folder action | About 76:3540, existing System data controls | Link the actual Kel license. Open System for the data folder. Keep update log, issue link and prerelease choice. | AboutModalContent, public/licenses/Kel-LICENSE.txt |
| Scheduled work has an existing detail route | Scheduled 76:4389 | Keep routed details and editing rather than replace scheduling behavior. Apply shared card, header and control tokens. | ScheduledTasksPage/index.tsx |
| Native home includes assistant prompts and selection | Home 94:1585 | Preserve available assistant selection. Place prompt actions before the bottom composer. No prompts are invented. | GuidPage.tsx |
| Permission explanations and emergency controls exceed the empty source | Permissions 76:3789 | Show all three source cards. Keep advanced explanations and scope checks behind the existing disclosure. Preserve emergency confirmation. | autonomy/index.tsx |
| Live history includes drag ordering, batch controls, forks and active generation | Nav 143:87 and Chat 76:3001 | Use source status dots for ordinary rows. Keep existing spinner, lineage marker, drag handle, contextual actions and mobile actions. | ConversationRow.tsx |
| Model controls include health clearing and full empty-state help | Model 76:3222 | Keep Clear status, provider-specific validation and empty-state guidance. The custom-model card grows for these controls. | ModeSettings, ModelModalContent |
| Model form has additional required production fields | Model 76:3222 | Use source 520px modal width. Let height grow for real validation and provider-specific fields. | AddPlatformModal.tsx |
| Native WebUI controls differ from the static sample fields | WebUI 76:3357 | Keep existing read/copy/edit credential controls and the remote-access explanation. Preserve the full-width cards; these controls increase card height. | WebuiModalContent.tsx |

These decisions preserve real controls. Screenshot content and card heights can differ when returned state differs from the Figma sample.
No phone frame or complete loading/error/success matrix was present in the final-screen page. Existing state machines remain authoritative.
