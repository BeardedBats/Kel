# Files and artifacts

| Item | Class | Evidence |
|---|---|---|
| Attach file in chat | PAG (mechanism verified) | chat attachments are @-mention references into the workspace; the mention popup is probed in `sweep2` |
| Drag/drop into transcription | PAG | drag-to-folder + audio drop verified in the transcription battery |
| Remove before send | PAG | mention chips can be removed before sending |
| Filename/type visible | PAG | mention chips show the referenced file |
| Unsupported file → plain error | PAG | transcription upload: “That file type is not supported…” (verified) |
| Failed upload recoverable | PAG | retry works; nothing is half-created (engine tests) |
| Multiple attachments | PAG | up to ten referenced attachments (engine contract) |
| Large-file behaviour understandable | PAG | 5 MB attachment limit surfaced in plain language; transcription 32 MB/10-minute limits in plain sentences |
| Generated artifacts discoverable | MO (documented) | `conversation_artifacts` exists and Work/notification surfaces reference it, but artifacts require a working provider to generate; a dedicated artifacts browser is honestly optional for this pass — Work + chat + reveal-in-folder cover the current flows |
| Open / Show in folder / Copy path | PBF | reveal-in-folder exists (Preview panel, Explorer); a unified per-artifact action set is part of the optional artifacts browser |
