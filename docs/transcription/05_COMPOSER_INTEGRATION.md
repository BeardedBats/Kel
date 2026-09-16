# Transcription — composer integration

## Placement

The composer's action row already reserved a speech slot; Kel fills it with its own microphone
(`pages/guid/components/KelMicButton.tsx`), replacing the donor's browser-speech button (which needs
a network service and fails silently in packaged builds — exactly the kind of dead control the User
Journey standard forbids).

```
[ workspace ] [ model ] [ … ] [ 🎤 mic ] [ send ]
```

## Behavior

1. Click the mic → recording starts (no spacebar, ever).
2. The button becomes unmistakable: red stop square + "Recording 0:14"; a **Cancel** control sits
   next to it. Escape cancels.
3. While recording, live text is inserted into the composer (when the runtime streams); the user
   watches their words appear.
4. Stop → the final transcript is **inserted into the composer as editable text**. Nothing is sent.
5. The user can edit, shorten, add context, or clear it — then press send like any message.

## Why no auto-send

The brief's default is explicit: *"Transcription produces editable text before sending."* Auto-send
would turn every misheard word into a committed message; instead the composer is the review step.

## The chat handoff from the page

"Send to chat" on the Transcription page stores the transcript in `sessionStorage`
(`kel.transcription.draft`) and opens the chat; the guid composer consumes it once, appends it to
whatever is already typed, and clears the handoff. Same editable-text guarantee.

## What the composer mic deliberately does NOT do

- No hidden spacebar shortcut, hint, or setting (program hard rule).
- No floating recording popup over the composer — the state lives in the action row itself.
- No auto-save of dictation into the transcript library: input is not a document.
