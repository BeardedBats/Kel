# Desktop Dark Tools status — canonical review

**Authority:** [Kel Design System, FINAL Tools `188:1956`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=188-1956), plus Foundations and Components. **Rendered evidence:** [r47 at 1440px](key/r47-tools-1440.png), [r47 at 800px](key/r47-tools-800.png), [measurements](r47-desktop-check.json), and [interaction check](r47-tools-interactions.json).

The r47 source changed MCP rows from 50px to the FINAL 40px desktop rhythm. The first row shows a connected check, and both rows retain their expand and retest controls. At 800px, each row grows to 48px for its label and the card keeps Add MCP inside its bounds. The functional Add MCP control and the second row's status detail are extra runtime information absent from FINAL's sample. They do not justify removing live controls. The r47 interaction record confirms expand/collapse, Add MCP menu, and navigation to Model.

No `ToolsSettings` source changed between r47 and canonical `main`. The r47 packaged captures therefore remain evidence for this scoped layout and connected sample state. No new source repair was indicated by this comparison. The canonical App was not relaunched for this review.

**Still open:** exercise a disconnected MCP, an active retest, error/help details, and an enabled Image Model on disposable data. Compare each rendered state to Components at 1440 and 800px. These dynamic states are not proved by the FINAL sample or the r47 connected capture. Keyboard and assistive-technology checks also remain open.
