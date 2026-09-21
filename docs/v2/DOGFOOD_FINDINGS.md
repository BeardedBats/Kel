# KEL V2.0 — DOGFOOD FINDINGS

Real Fix Capture feedback from the stable dogfood build (`C:\Users\Nick\KelDogfoodCandidate`) and how the
V2 line handled it. This file is the contract for treating that feedback as an **external input**, not
as synthetic test data.

## How a batch is handled (directive §15/§20)

1. reproduce the finding in the current build;
2. group related findings by root cause (duplicate symptoms are one bug);
3. implement a coherent repair — smallest change that satisfies the intent;
4. add regression coverage that would have caught it;
5. verify the affected UI directly (installed app where practical);
6. never mark a finding fixed merely because code changed — only when the reported behaviour is verified
   gone.

Findings can change V2 priorities; a priority change is recorded here with its reason.

## Findings incorporated so far

| Finding | Source | Disposition |
| --- | --- | --- |
| Fix Capture returned Kel's canned practice transcript instead of Nick's words (silent practice fallback when no key was configured) | V2 preflight verification of the dogfood build | **FIXED** on the predecessor line: the engine now reuses the credential the copied Transcriptions app already stored, practice mode is explicit-only, and the dogfood store refuses canned text. Records: `docs/transcription/11_MUSE_SHARED_CREDENTIAL.md`, `docs/daily-driver/FIX_CAPTURE.md`; live evidence in `docs/daily-driver/evidence/muse/`. |
| The bridge refused `/api/dogfood` ("Unknown Kel action") | installed journeys (preflight) | **FIXED** — the `kel:request` allowlist admits the dogfood routes; pinned by the allowlist test. |
| The view could not show a saved screenshot (preload never exposed the read) | installed journeys (preflight) | **FIXED** — preload exposes `dogfood.screenshot`; pinned end-to-end. |
| Ctrl+Shift+F was already owned by the donor conversation search | installed journeys (preflight) | **FIXED** — Fix Capture claims the chord in the capture phase; the trade is documented and pinned. |
| Cancelling left the temporary screenshot behind | installed journeys (preflight) | **FIXED** — the engine discards in-flight captures (tmp only) and the hook calls it on cancel; the cancel journey now asserts zero leftovers. |

## Awaiting real input

No consumer (real-use) Fix Capture batch has been brought into the V2 thread yet. When one arrives,
append it here with: the raw transcript(s), the route/screen, what was reproduced, the root cause, the
repair commit, the regression added, and the verification that closed it. If a finding is deliberately
*not* fixed in V2, say so with the reason — never leave it silently open.
