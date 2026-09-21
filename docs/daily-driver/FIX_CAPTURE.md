# FIX_CAPTURE — V2.0 preflight

*Status: implemented, tested, packaged, installed and verified in the installed app. The rest of V2.0
has deliberately not been started.*

The Daily Driver marathon closed with a candidate Nick could use; this tranche is the small tool that
makes using it worth something: **Fix Capture** — Ctrl+Shift+F, click the part of Kel that bothers you,
say why, save, keep working. Fifteen seconds, not sixty, and nothing to fill in: Kel captures the
context itself.

## What it is, and what it is not

| | |
|---|---|
| Invoke | **Ctrl+Shift+F** (again stops a recording), **Esc** cancels, clicking the highlighted area stops |
| Select | click buttons, cards, text areas, settings rows, sidebar items, conversation areas, panels — the hovered element gets a full-perimeter highlight and the cursor says "selecting" |
| Say | a compact panel opens beside the target (never on top of it when there is room) with the live transcript from Kel's own transcription |
| Decide | **Save Fix** / **Record Again**; clicking outside or Esc cancels without saving |
| Review | `/dogfood` — Open / Batched / Fixed / Dismissed, transcript previews, and a detail pane with the words, the captured context and the screenshot with the target outlined by the view |
| Batch | **Prepare Fix Prompt** turns the selected OPEN fixes into one structured development prompt |

It is **not** an issue tracker: four statuses, and a schema pin (engine) plus a vocabulary pin
(desktop) that there are no assignees, priorities, due dates, labels, sprints, comments or boards.

## Built out of what Kel already had

| Need | Reused, not rebuilt |
|---|---|
| Words | `/api/transcription` — `stream_start` / `stream_chunk` / `stream_status` / `stream_finish`, with the `quick_transcribe` fallback; `friendlyMicError` for device problems. Raw audio is never kept: only the words are stored |
| Durable state | the engine's SQLite store and its migration pattern (`runtime/kel/dogfood.py`, migration **22**) |
| Screenshot | the main process reads **Kel's own window** (`webContents.capturePage`), the same technique the donor's feedback bridge already used — never the desktop, never another app |
| Shell plumbing | the `kel:request` bridge and its route allowlist, the preload surface, the `assertTrustedSender` guard used by every privileged channel |
| UI | Kel's tokens and primitives, the layout-mounted overlay pattern (the command palette's neighbour), 8px geometry, no pills, no accent rails |
| Prompt | rendered in the engine, deterministically; no model call and no upload anywhere in the feature |

## Real Muse, and what happens when it cannot answer

Kel transcribes with Meta Muse, using the credential the **copied Transcriptions app already stored on
this computer** — read read-only from Windows Credential Manager, never migrated, never re-entered,
never shown. The engine's resolution order is env → Kel's own setting → that shared credential, and
practice text is now produced **only** when someone asks for it by name (`…=fixture`). This is what
made Fix Capture return canned text before: the family fell back to `FixtureProvider` whenever its two
key sources were empty. The full root cause, the guard and the verification live in
`docs/transcription/11_MUSE_SHARED_CREDENTIAL.md`.

When Muse cannot answer, the panel says so and offers the way out:

- **“Couldn't transcribe this recording.”** plus Muse's own sentence (for example *The Meta API key was
  not accepted. Replace it in Settings.*). Never a substitute transcript, never a silent blank.
- **Retry Transcription** re-sends the recording that is already captured — the WAV is held for the
  whole review, so a failed call never costs a second take.
- **Record Again** throws the failed recording away and transcribes the new one; **Esc / click-outside**
  throws it away and cleans the temporary screenshot, leaving nothing behind.
- The engine refuses to *save* the archived practice sentences as feedback at all
  (*"That is Kel's practice text, not your words — record again."*) unless practice mode is explicitly on,
  so a debug build cannot file canned text as a real finding.

## The hotkey conflict, resolved deliberately

The donor's conversation-search modal already bound Ctrl+Shift+F (a document-level capture listener
that opens the search). Fix Capture is the primary consumer of that chord now, so the layer listens on
`window` in the **capture phase** and stops the event before the search handler sees it. The search
keeps its own trigger in the conversation header and the Ctrl+K palette path; its binding is left in
the source as the documented trade, pinned by `fix-capture.dom.test.ts`. Nick asked for Ctrl+Shift+F,
so the capture wins the chord.

## Storage

```
<engine data root>/
  kel.sqlite3                      dogfood_fixes (id, created, updated, status, transcript, …)
  dogfood/
    screenshots/FIX-0001.png       committed by the engine under the fix id
    tmp/<uuid>.png                 in-flight captures; deleted on cancel, swept when stale
    prompts/PROMPT-<stamp>.md      the generated fix prompt, kept next to its findings
```

Screenshots never enter the repository, are never uploaded and never reach a model during capture; the
stored target box is metadata, so the highlight is **not** baked into the PNG. Only files inside
`dogfood/tmp` can be deleted by a cancel, and only PNGs directly inside `dogfood/screenshots` can be
read back for the view.

## Statuses and the prompt

`OPEN → BATCHED → FIXED / DISMISSED`, with Reopen. `prepare_prompt` includes every OPEN fix by default
(or exactly the ids the view sends), writes `dogfood/prompts/<id>.md` **first**, and only then marks
those fixes BATCHED — a prompt that was never written changes nothing. The rendered prompt carries each
Fix id, Nick's transcript, the capture time, the route and page, the selected element, the locator, the
target box, the window/scale, the build, the project/conversation context where relevant, the
screenshot reference, and the ten instructions a fixing session must follow (reconcile, reproduce,
group root causes, smallest coherent fix, north star, regression coverage, verify the UI, don't call it
fixed because code changed, report the ids).

## Test evidence

**Engine** — `runtime/tests/test_dogfood.py`, 27 tests: id allocation, screenshot commit and refusal
outside `dogfood/`, honest saves when a capture vanished, in-flight discard (and the refusal to touch
anything else), status validation, subset prompts, determinism, the ten instructions, project
resolution from a conversation, the stale-tmp sweep, durability across a reopen, the schema pin
against tracking fields, and the practice-text guard (refused as feedback in production, allowed when
practice mode is asked for by name). Full engine suite: **1060 tests OK**.

**Desktop** — `fix-capture.dom.test.ts` (pure helpers + pins) and `fix-capture-layer.dom.test.tsx`
(ten integration tests through the real layer with a stubbed microphone and engine): hotkey opens,
Esc cancels, a click selects and starts recording, the live transcript arrives, the hotkey stops and
the transcript reaches review, Record Again replaces the words and keeps the target, Save produces
exactly one fix with the full payload, a missing microphone becomes a typed capture, click-outside
cancels without saving and hands the temp screenshot back, a failed transcription says so honestly
and its retry re-sends the very same recording, and Record Again drops a failed take — plus the pins
that matter: the bridge allowlist admits the dogfood routes, the capture-phase claim over the donor
search, one capture implementation shared with the Transcriptions page, no spacebar shortcut, no
single-side borders, exactly four statuses, screenshot path safety. Full desktop suite:
**38 files / 310 tests** (tsc clean).

The Muse repair was packaged on top of this: `dist/package-r12/Kel-1.7.0-dev-win-x64.exe` —
`007eaaa5…` (213,649,875 bytes), `Kel.exe` `9a2ffbdf…`, engine `e6444991…` — and installed over the same
candidate (data root untouched: the four earlier fixes and their prompt survived the update).
Verification for that build, driven through the installed app with the real production Muse path
(`packaging/verify-muse-live.cjs`; evidence in `docs/daily-driver/evidence/muse/`):

| Run | Result |
|---|---|
| Normal Transcriptions (phrase *“Regular transcription Muse verification, orange baseball forty-seven.”*) | **PASS** — page reports **Muse**; live text *“Regular transcription muse verification”*; saved transcript *“Regular transcription muse verification orange”* |
| Fix Capture (phrase *“Fix Capture Muse verification, blue baseball eighty-three.”*) | **PASS** — **FIX-0006** transcript *“Fix capture muse verification, blue baseball 83”*, visible in Dogfood Fixes, nothing invented |
| Failure (unusable key, one launch only) | **PASS** — *“Couldn't transcribe this recording. The Meta API key was not accepted. Replace it in Settings.”*, **Retry** present and reusing the recording, Save disabled, **no fix saved**, and the practice-text guard answered 400 |
| Real microphone | **PASS** — four real inputs listed, the app opened the default device with no error, peak ≈ 0.001 (the room is silent; nobody can speak during an automated run, so the spoken phrases came from a TTS WAV injected as the media input) |

Every run: 0 console errors, 0 orphaned engines; the Dogfood page kept 0 px overflow, no donor terms
and no raw internal ids across the list, the detail outline and Prepare Fix Prompt (which still produced
a prompt containing both new Fix ids and the ten instructions, moving them to Batched).

The earlier journey table below was recorded before the Muse repair and therefore shows the practice
provider answering those recordings — that was the bug this tranche fixed. The journey mechanics
(hotkey, selection, panel, cancel, prompt, screenshot outline) are unchanged and re-verified above.

## The package, and what the installed app proved

Build: `dist/package-r12/Kel-1.7.0-dev-win-x64.exe` — `c1a25b96…` (213,640,232 bytes).
Inside it: `Kel.exe` `588fcc5d…`, `resources/kel-engine/KelEngine.exe` `443a4e73…`.
Installed to **`C:\Users\Nick\KelDogfoodCandidate`** (its own target; registered there), data root
`C:\Users\Nick\KelDogfoodRuns\prepared\engine`.

One honest note about the previous candidate: NSIS updates heal to the *registered* install directory,
and the first Fix Capture install ran before the registration had been repointed — that one pass landed
in `C:\Users\Nick\KelDailyDriverCandidate`, so that directory now holds this build rather than the
Daily Driver one. Its **data root is untouched**, the Daily Driver candidate is still reproducible from
`DAILY_DRIVER_CANDIDATE_HEAD` (`6c9d1a1`), and every piece of Daily Driver evidence in this folder
stands; only the old installer binary in `dist/` has been superseded by this build. The Fix Capture
candidate was then installed to its own directory and is the registered application now.

The journeys were driven through the installed app's own window over CDP
(`packaging/verify-fix-capture.cjs`; raw results and screenshots in
`docs/daily-driver/evidence/fix-capture/`). This machine has no microphone, so the app was launched
with Chromium's synthetic audio device and the engine's practice transcription provider answered the
recording — the capture path, the transcription family, the store and the whole UI are the shipped
ones, and the transcript text is the practice sentence by design.

| Journey | Result |
|---|---|
| **A** Ctrl+Shift+F → click a Settings element → record → stop → Save Fix → restart | **PASS** — `FIX-0001` saved with its transcript, **still there after a restart**, transcript visible in the view |
| **B** Record Again → new transcript → Save | **PASS** — `FIX-0002`, exactly one fix created by the capture, the target kept across the re-record |
| **C** click outside after recording | **PASS** — cancelled, nothing saved, panel gone, **0 files left in `dogfood/tmp`** |
| **D** capture fixes → Prepare Fix Prompt | **PASS** — prompt written, every new Fix id inside it, all of them **OPEN → BATCHED**, the Open tab had listed them, and the prompt carries the ten instructions |
| **E** screenshot + target box vs the real element | **PASS** — `FIX-0001.png` saved (60,470 bytes, 2065×1392), route `/settings/about`, element `<span>` “Check for updates”, box inside the image, and the view draws the outline over it (104×17) |

Honesty checks on the same run: **0** console errors, **0** orphaned `KelEngine` processes, **no** raw
internal ids on the surface, **no** donor terminology, **0 px** horizontal overflow; `dogfood/` held
exactly one prompt, four screenshots, and no temporary files.

Four defects were found this way and fixed (see the two `fix(fix-capture)` commits): the main-process
route allowlist refusing `/api/dogfood`, the preload never exposing the saved-screenshot read, the
donor conversation search already owning Ctrl+Shift+F, and the temporary screenshot surviving a
cancel. Each one now has a pin.

## Honest limits

See `KNOWN_LIMITATIONS.md` — the synthetic-microphone verification, screenshot privacy (local only,
never uploaded, never sent to a model during capture), the app-scoped shortcut, and the Ctrl+Shift+F
trade with the conversation search. Raw audio is never kept: only the words become a fix.
