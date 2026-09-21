# Shell implementation boundary

Base: 772b2c357943cf9793639bbf660171c49d809c38. Clean dev/v2 at worktree creation.
Worktree: C:/Users/Nick/Desktop/Kel/kel-v2-shell. Branch: ux/v2-shell.

## Preserve behavior

- Layout.tsx: retain authentication, navigation, notifications, resizable panels, mobile drawer, preview ownership, and Ctrl+Shift+F.
- Sider/index.tsx: retain history loading, batch selection, project grouping, pinning, drag ordering, and logout.
- GuidPage.tsx: retain draft, model selection, attachments, IME, slash commands, Muse, and send hooks.
- SendBox/index.tsx: retain conversation send, cancellation, uploads, mentions, permissions, and mobile action sheet.
- Kel pages: retain their existing API reads, mutations, approval gates, errors, and recovery paths.
- Transcription: retain recording, Muse streaming, library, upload, merge, export, and review handlers.
- FixCaptureLayer and dogfood page: retain capture lifecycle, shortcut, engine API, and persisted identifiers.

## Presentation plan

- Map Figma variables into one generated CSS file with source IDs.
- Reuse KelPrimitives and Arco control behavior; apply canonical V2 component geometry and states.
- Replace the sidebar toolbar presentation and add a data-driven Tools section.
- Restyle existing history rows rather than replace their state and action hooks.
- Use exported Figma assets for the background, brand, and canonical icons.
- Retain existing desktop and phone behavior where no Figma frame defines a replacement.

## Source inventory

Screens - FINAL (76:2) contains 22 desktop frames, each 1440 by 900.
DS v2 Components (136:2) defines button, navigation, chat, composer, input, toggle, menu, toast, and attachment states.
No phone frame was found in the final-screen inventory. The final home sidebar has no Tools group.
Record conservative production extensions in FIGMA_GAPS.md.
