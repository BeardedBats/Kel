# Current Figma Tools — scoped package evidence

**Authority:** [Desktop Tools `313:2441`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=313-2441), [mobile Tools `315:2842`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=315-2842), mobile detail `315:3004`, and desktop overlay nodes `313:2923`, `313:3413`, `313:3911`, `313:4441`, `313:4940`. The earlier 51-screen pair audit is superseded.

The test app is a disposable `electron-builder --dir` package of canonical `main` source. It runs with `KEL_DATA_DIR`, `AIONUI_DATA_DIR`, `KEL_HOST_DATA_DIR`, and Electron `--user-data-dir` under a single `%TEMP%` root. The canonical `App` and `Data` are not used. The synthetic `local-audit-mcp` points to an unused loopback port and reaches the real failed-check state. The package also shows built-in Connected and Not tested rows. No sign-in-needed row, personal credential, real tool list, or live image service is supplied.

## Measured checks

| State | Result | Evidence |
| --- | --- | --- |
| Desktop Tools, 1440×900 | MCP and image cards render the current copy. Document width is 1440px. | [capture](current-tools-1440.png) |
| Desktop Tools, 800×900 | Connected, Not tested, and failed status controls no longer overlap after the narrow-row fix. Document width is 800px. | [capture](current-tools-800.png) |
| Mobile Tools, 393×852 | MCP card starts at x=16, y=114 and spans 361px. Document width is 393px. | [capture](current-tools-393.png) |
| Mobile Tools, 320×852 | MCP card starts at x=16, y=114 and spans 288px. Document width is 320px. | [capture](current-tools-320.png) |
| Add MCP server / Paste JSON, 1440×900 | Modal bounds x=420, y=110, 600×366px. Sample JSON, hint, green Add server button, full border, and 24px blur render. | [capture](current-add-json.png) |
| Delete server, 1440×900 | Modal bounds x=490, y=300, 460×138px. Name, consequence, Keep, and danger Delete server render. Delete was **not** confirmed. | [capture](current-delete.png) |

The source repair preserves the existing JSON parser, multi-server import, retest, OAuth, delete, and feedback handlers. The UI does not invent Figma's sample rows. The mobile error detail uses the real failed status, a check time, a warning, a neutral empty-tools line, and working Test again and Report issue actions. The empty-tools line is an inference; the populated-tool variant remains open.

**Checks:** desktop TypeScript check passed. Full desktop Vitest passed 52 files / 396 tests. Electron Vite packaging and the disposable Electron builder passed. The package script reported zero page errors across the measured widths. The final package and screenshots are the evidence for the bounds above; CSS injection during iteration was not used as final proof.

**Remaining current-Tools gaps:** the CLI import dialog is still a three-step flow, whereas Figma `313:3911` shows a single selectable server list. Report issue still opens the general feedback dialog, whereas Figma `313:4441` shows a server-specific report. The OAuth sign-in row, populated mobile tools, keyboard and assistive-technology flow, and a real image provider remain unverified. The new mobile footer has four tabs; production preserves a fifth Kibble tab pending Nick's placement choice. Product-wide Figma parity is not established.
