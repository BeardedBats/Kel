# Transcription — known limitations

Recorded honestly; none of these block the shipped flows.

1. **Muse (Meta) is implemented but unverified live.** No Meta API key exists on this machine, so the
   realtime websocket path and the multipart file transcription were ported faithfully from the donor
   (same endpoint, handshake, error mapping) but only their *contract* is exercised by tests. Practice
   mode (deterministic local text) is what the packaged verification runs against. When a key is
   connected, the same UI switches to Muse with no other change.
2. **Live transcription depends on the runtime.** Muse realtime needs `websocket-client` in the
   bundled engine; when the package cannot stream, the page records and transcribes on stop, and
   nothing claims otherwise in the UI.
3. **Uploads are prepared in the renderer.** MP3/MP4/etc. are decoded with WebAudio to 24 kHz mono
   PCM16 WAV. Formats Chromium cannot decode are refused with one plain sentence; there is
   deliberately no FFmpeg sidecar in the package.
4. **Combine and Record more concatenate audio only when both sides are WAV.** That is always true
   for anything recorded or uploaded in Kel (the renderer normalizes), so foreign audio files copied
   into the data directory by hand are the only exception; text and duration always combine.
5. **One transcript text field.** Speaker labels appear only when the provider returns diarized
   turns (Muse file mode); there is no per-word editing UI, timestamps, or per-line seek.
6. **Dictation is not saved to the library.** Composer transcripts are input; only the dedicated
   page saves documents. Cancel discards (by design).
7. **Transcription provider choice is not a user setting.** Practice mode or Muse — the key decides.
   A provider picker was deliberately not added (JR-37: one plain status).
8. **Design Vetting integration is English-tuned** like the rest of Vetting (question ids, option
   codes); a fully localized voice flow is future work.
9. **The composer mic uses the chat conversation**, while the dedicated page applies vetting
   transcripts to the newest active session when no conversation is given. Two chats with two active
   sessions is the one ambiguous case; the review modal names the answers it will apply.
