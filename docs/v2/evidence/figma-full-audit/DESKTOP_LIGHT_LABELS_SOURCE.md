# Desktop Light labels — measured source repair

The current Figma Foundations board 139:3 specifies the Dark palette. It provides no complete Light palette. This increment preserves Figma desktop geometry and uses Kel's existing Light semantic colors. It establishes scoped label contrast, not exact Light color parity or a complete Light design audit.

Desktop Light now resolves shared sidebar/section/catalog labels through its own primary, secondary, muted, accent, and semantic colors. Tools statuses/error copy/image setup, model availability/action labels, Kibble tabs, project-map captions/freshness, and Settings navigation no longer use pale Dark text on Light surfaces. New Chat and the primary/secondary Setup and map buttons use the existing Light accent with inverse text. Their hover state uses the existing accent-hover token. Desktop Dark and phone CSS rules were not changed. No accent rail was added.

An isolated Electron app rendered current source, selected the real Light theme, checked eight routes at 1440px and 800px, then restored Dark. Routes: Appearance, Skills, Pet, Kibble, Tools, Work, Knowledge, and Setup. The [measurement file](desktop-light-label-measurements.json) records computed text colors, ancestor-composited background colors, and ratios. Every measured enabled text label meets 4.5:1. The minimum is 4.86:1, with zero document overflow and zero renderer errors. This is a computed-style measurement, not pixel-level anti-aliasing analysis. Disabled Pet radio labels were excluded and remain dimmed. Icon contrast, every popup, populated Skills in Light, live providers, sign-in, and custom-color combinations remain open.

Screenshots: [Appearance 1440](DESKTOP_LIGHT_APPEARANCE_1440.png), [800](DESKTOP_LIGHT_APPEARANCE_800.png); [Tools 1440](DESKTOP_LIGHT_TOOLS_1440.png), [800](DESKTOP_LIGHT_TOOLS_800.png); [Setup 1440](DESKTOP_LIGHT_SETUP_1440.png), [800](DESKTOP_LIGHT_SETUP_800.png); [Knowledge 1440](DESKTOP_LIGHT_KNOWLEDGE_1440.png), [800](DESKTOP_LIGHT_KNOWLEDGE_800.png).

Seven existing theme/override/input tests passed across two files. The final source build passed. No live user theme or canonical App/Data changed. The earlier full 437-test desktop regression was not repeated for this CSS-only repair. Package proof waits for the combined desktop milestone.


A post-repair desktop Dark Pet probe also passed at both widths. Its card remained 670×259 / 388×259; real refusal/reload kept Pet Off, with zero renderer errors/overflow.
