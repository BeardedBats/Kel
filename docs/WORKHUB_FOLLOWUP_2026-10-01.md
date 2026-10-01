# Work hub follow-up: 1 October 2026

Kel keeps its chat history locally. Native Codex work now uses temporary sessions.
Buffered exec, structured correction and image requests use `--ephemeral`.
App-server requests require a supported Codex version and an explicit temporary-session acknowledgment before sending the prompt.
Kel replays its saved context for restarted work. Old remote IDs remain diagnostic records.
Generic remote resume is refused because temporary sessions cannot resume after the transport ends.
The WSL transport cannot currently confirm the required native version and stops before creating a thread.

PDF references now keep readable page text and use local Windows OCR for pages without text.
The original file remains unchanged. The reference records `pdf-ocr` and the UI labels OCR text.
Both extraction steps share one execution deadline and retain existing byte, page, text and process limits.
OCR supplies text; it does not recreate diagram meaning or page layout.

Each trusted Windows command now starts suspended and joins its own kill-on-close Job before its code runs.
Only its standard input/output handles can pass to the child.
Kel ends the command tree on normal exit, Stop, timeout, output limit and transport loss.
Setup and cleanup errors cannot produce a passing check receipt.
This improves process lifetime. It does not provide complete file-read or network isolation.

Explicit paragraph requests accept short, brief and concise modifiers.
Approximate counts, ranges, quoted examples and per-paragraph counts remain outside this exact-count contract.
The original source study exposed the missing modifier before this fix.
Its generated candidate and subsequent review remain separately labeled evidence.

Focused source checks and independent source reviews cover these changes.
Real synthetic Windows OCR and child-tree checks are distinct from mocked failure checks.
The external release folder records the package, installed build and remaining verification limits.
Physical microphone and phone checks remain unverified. Verified Claude/DeepSeek browser export formats still need actual export samples.
No new account connections or API keys are required for these changes.
