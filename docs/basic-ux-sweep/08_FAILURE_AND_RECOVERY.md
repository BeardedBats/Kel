# Failure and recovery

Every failure answers four questions (what happened / is Kel handling it / do I need to act / how to
continue) in plain sentences; no transport envelopes, HTTP codes or stack traces reach the UI.

| Case | Behaviour | Class |
|---|---|---|
| Provider unavailable | chat shows the job waiting for a model, user text kept in the transcript | PAG |
| Wrong API key | plain sentence (“The Meta API key was not accepted…”) without status codes | PAG |
| Network failure mid-request | adapter errors map to one plain sentence at the service boundary | PAG (engine) |
| Task failure | Work card shows failed + reason; Retry re-runs without retyping | PBF → probe |
| Denied permission | policy blocks are shown as plain “blocked by a safety rule” states | PAG |
| Cancelled operation | cancel recorded; cancelled jobs stop looking active | PBF (no live provider to cancel) |
| Failed upload / transcription | one plain sentence; nothing partial is saved; retry works | PAG |
| Model unavailable | “Needs setup” chips + Automatic fallback | PAG |
| Engine killed while typing | app stays usable; next send fails plainly; draft survives restart | PAG after fix |
