# Desktop Dark polish — r47 working record

**Baseline:** packaged r46 (`C:\Users\Nick\KelV2Candidate.r46`, source `7024865`), 1440×900, Dark, 100% zoom, disposable `r43-populated` data. **Authority:** Figma FINAL `188:1956` Tools and `189:4032` Transcriptions, Foundations `139:2`, Components `136:2`. Existing behaviors and isolated data remain authoritative for dynamic values.

| Lock | Preserve |
| --- | --- |
| Structure | Left app rail, nested Settings/Projects rail, card order, navigation and route ownership. |
| Identity | Instrument Sans headings, Dark canvas, blue glass panels, amber card headings, existing token roles. |
| Content | Actual MCP state and saved transcript text, Add MCP, upload, recording, and transcript actions. |
| Behavior | Settings access, MCP retest, model configuration link, saved transcript selection, rename/copy/download. |
| Repair scope | Desktop Tools row geometry, empty-model spacing, 800px wrapping; desktop embedded Transcriptions selection. No phone layout work. |

**Correction thesis:** restore Figma's compact desktop row rhythm and show existing saved transcript content without changing the workflow.

| Finding | Baseline evidence | Proposed repair |
| --- | --- | --- |
| Tools MCP rows and card are too tall. | Packaged desktop rows are 50px each; Figma `188:2198` and `188:2199` specify 40px. Current card is 198px, versus a 142px Figma card without the additional functional Add MCP button. | Keep Add MCP. Set the two desktop rows to 40px, use Figma's flat rows and hairlines, and reduce redundant inter-row spacing. |
| Empty image model copy runs into its link. | Packaged UI reads `No available image models.Go to configure`. | Add visible spacing and right-align this runtime value in the existing control area. |
| Tools controls clip or stack poorly at 800px. | At an 800×900 desktop viewport, Add MCP clips at the card edge and the Image Model label wraps into a narrow column despite no document overflow. | Wrap the card header and stack the image label/value only within the 768–980px desktop range. |
| Embedded Transcriptions shows an empty document although a saved transcript exists. | The same disposable profile shows `Yeah` in Ramble, while `/transcription/library` displays `Your transcripts live here`. Figma `189:4032` shows a selected saved document. | Select the newest saved transcript when the embedded route loads, while retaining a valid current selection. |

## Packaged result

**Source:** `54ce43fa08295799cddb0101816369e22d872bd2`. **Candidate:** `C:\Users\Nick\KelV2Candidate.r47`, Dark, 100% zoom, disposable data. The [r46 Tools baseline](key/r46-desktop-tools-1440.png) had 50px filled MCP rows and a 198px card. The [r47 1440px result](key/r47-tools-1440.png) has two 40px flat rows, 6px between the empty-model sentence and link, and a 158px MCP card with the extra functional Add MCP action. [Measurements](r47-desktop-check.json) show x613/y183 and 670px width. The [800px result](key/r47-tools-800.png) keeps Add MCP within its card, stacks the image label/value, and has no document overflow. The 800px MCP rows grow to 48px to fit the server names.

The [r46 Transcriptions baseline](key/r46-desktop-transcriptions-1440.png) falsely showed an empty document with a saved item in the same isolated library. [r47](key/r47-transcriptions-1440.png) opens the newest saved item (`Yeah`, `A: Yeah`) in the Figma document panel. The unit test covers newest selection with two saved items. [Packaged interactions](r47-tools-interactions.json) show Add MCP options, MCP expand/collapse, and Go to configure navigation to Model. The neighboring [Appearance capture](key/r47-appearance-1440.png) still has three theme cards and no horizontal overflow.

| Category | Baseline → r47 | Evidence and limit |
| --- | --- | --- |
| Hierarchy and comprehension | 3 → 4 | The actual saved document replaces a false empty state. Sample text differs from Figma. |
| Typography and readability | 3 → 4 | The empty-model sentence/link separate; 800px controls read in order. Expanded MCP tool descriptions were outside this repair. |
| Geometry and rhythm | 2 → 4 | Desktop MCP rows measure 40px at 1440px; 800px uses readable 48px rows. |
| Component and interaction craft | 3 → 4 | Add MCP, expand/collapse, and Model navigation work in the package. Unchecked MCP and model states remain open. |
| Responsive and accessibility integrity | 2 → 4 | The 800px desktop card contains its controls; both checked widths have no horizontal overflow. Keyboard and assistive-technology claims remain unverified. |
| Fidelity to approved direction | 3 → 4 | Figma panel rhythm and existing token roles remain. Add MCP is an intentional functional control absent from the sample frame. |

**Scoped result:** visible defects above are repaired. This pass did not inspect phone layouts or claim full product parity. No independent review occurred because `request_review` was unavailable.
