# KEL V2.0 — KNOWN LIMITATIONS

Honest, current limits at the V2 base — things a later run must not pretend are solved. Phase-specific
limits are appended as phases land.

## Inherited from the predecessor line (still true)

- **Verification audio is synthetic where a person would speak.** The Muse verification runs fed Windows
  TTS WAVs into the capture path (`--use-fake-device-for-media-stream` + `--use-file-for-fake-audio-capture`);
  the real-device run shows the app opening the actual microphone with no error, but the room is silent
  (peak ≈ 0.001) because nobody can speak during an automated run.
- **The shared meta credential is Windows-only.** `shared_muse_key()` reads Windows Credential Manager,
  so on another platform transcription reports `unavailable` unless a key is supplied through the
  environment or Kel's own setting.
- **Muse realtime endpointing returns the utterances it closed before Stop**, so a long phrase can arrive
  in parts ("…verification orange"; "…blue baseball 83" for "eighty-three"). That is ASR behaviour, not
  Kel copy.
- **Screenshots can contain whatever was on screen.** Fix Capture captures only Kel's own window, keeps
  everything local, and never uploads or sends them to a model during capture — but a screenshot is a
  screenshot, and they travel only inside a prompt Nick deliberately prepares.
- **Remote work needs the desktop awake.** Away-from-desktop use today depends on Nick's desktop Kel
  running; cloud Kel is V2.5 by decision, and mobile V2 deliberately has no uploads, camera, share sheet
  or push notifications.
- **The older Daily Driver / Fix Capture limits** (provider-id naming, cancellation hygiene, hotkey
  conflict resolution, and the rest) are recorded in `docs/daily-driver/KNOWN_LIMITATIONS.md` and remain
  accurate for this line.

## V2-specific unknowns and risks (to be resolved by their phases)

- **Connections do not exist yet.** Every V2 connection (Pitcher List, Stripe, Raptive, Google Drive,
  GitHub, ClickUp, Figma, Discord, Generic REST) starts as unbuilt; none of their credentials exist on
  this machine except the Muse one, so early connection work will be verified with local test doubles
  and only later against Nick's real accounts.
- **No mobile hardware in this environment.** iPhone PWA verification will be synthetic (the PWA driven
  in a desktop browser over the web-host gateway) plus the installed-app tether check; real-device
  behaviour (iOS Safari, add-to-home-screen, backgrounding) can only be confirmed by Nick.
- **Isolation and network rules will be verified locally and synthetically** (path probes, process-tree
  kills, blocked-domain attempts) rather than by hostile scenarios.
- **Upgrade reliability must be proven without touching the dogfood install.** V2 upgrade tests use V2
  data roots and the V2 candidate only; the protected dogfood pair is never the subject.
