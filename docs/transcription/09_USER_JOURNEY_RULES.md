# Transcription — User Journey rules applied

This feature was built under `docs/product/USER_JOURNEY_STANDARD.md`. Three new generalized rules
came out of it (H18–H20 in the history ledger); the rest of the program mapped to existing rules.

## New rules (created)

1. **JR-35 — Recording is loud, stoppable, and never hidden.** Any capture state must be unmistakable
   (visible mark + plain label + elapsed time), have an explicit stop and an explicit cancel, be
   cancellable with Escape, and must never be triggered by a hidden or global shortcut. No spacebar
   recording; no discoverability hint for one; no settings toggle for one.
2. **JR-36 — Machine-written text lands editable before it acts.** Dictated or generated text enters
   the composer as text the user can edit or clear; it is never auto-sent, and it never replaces what
   the user already typed (it appends). The same guarantee covers hand-offs between surfaces
   (Transcription → chat) through a one-shot draft the composer consumes and clears.
3. **JR-37 — One plain status hides every provider.** A feature that talks to an external provider
   exposes exactly one human status ("Practice mode", "Muse (Meta)") with a single settings entry;
   endpoints, model names, protocol states, quota math, and socket errors stay out of the interface.

## Existing rules applied (examples)

- **JR-9 (silence is a defect):** every failure path answers with one plain sentence — microphone
  denied/busy/missing, unreadable file, provider rejection, missing session. Nothing fails silently.
- **JR-14/JR-16 (product words, not machinery):** the page never says WAV/PCM/websocket/multipart;
  it says Recording, Upload Audio, Transcript, Folder.
- **JR-17 (identifiers are not names):** transcripts are titled from their own first words
  (`contextual_title`), uploads fall back to the file's stem — never a raw id.
- **JR-18/JR-19 (novelty must pay rent):** the composer's donor speech slot was replaced rather than
  duplicated; the sider gained exactly one entry (Transcription) for a first-class tool.
- **JR-22/JR-23 (find by meaning):** folders above, recents below, inline create/rename, drag to
  file — no modal required for any organizing task.
- **JR-25 (readability):** all page text uses Kel's type tokens; the page's own contrast is covered
  by the readability scenario run on the same package.
- **JR-28 (empty states teach):** no transcripts → "Your transcripts live here" + what to do;
  empty folder section explains dragging.
- **JR-31 (counters tell the truth):** the recording bar shows real elapsed time; statuses read
  Saved / Needs attention / Processing.
- **JR-34 (a route is wired for every consumer):** `/api/transcription` was added to the renderer
  bridge whitelist in the same change — verified by the live pass, not just unit tests.
