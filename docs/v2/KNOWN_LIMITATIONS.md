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

- **The assistant cannot use a connection yet.** V2-01 … V2-04 built the
  model, the central surface, Test Connection and the eight services as data. The framework's actions
  (rows, `run()`, the confirmation gate and the access history) are built too, but the bridge that would
  let a conversation call one is not — the
  assistant's tools come from the coding runtime the desktop agent runs, so that is deliberate work, with
  the same one-request rule and the mutating confirmation. No Connections capability switch is offered
  until it exists. None of the services' real credentials exist on this
  machine except the Muse one, and **no real service has been contacted**: every check ran against a
  local stand-in service on the loopback interface.
- **The eight services are known by address and shape, not proven.** GitHub, Stripe, Figma, ClickUp,
  Discord and Google Drive use the endpoints their own documentation publishes; Pitcher List is an
  assumption (the standard WordPress layout) and Raptive's API address is unknown to Kel until Nick
  pastes the one Raptive issues. Nothing here has been run against the real service.
- **Google Drive cannot be checked beyond a pasted token.** There is no OAuth account sign-in step yet, so
  the token has to be supplied by hand; the catalogue entry says so rather than pretending otherwise.
- **The Connections surface has not been verified in an installed app.** It is covered in jsdom through
  the shipped page components and the real bridge contract, and the connection credential namespace has
  its own tests, but no installed Kel has had its Test connection button clicked, and OS-level encryption
  of a connection credential (as opposed to the V1.4 provider credentials that store already proves) is
  untested on a real DPAPI-backed install.
- **The framework's retries are proven against a local stand-in only** — a scripted 503-then-200 service,
  never a real rate limit from a real API.
- **No mobile hardware in this environment.** iPhone PWA verification will be synthetic (the PWA driven
  in a desktop browser over the web-host gateway) plus the installed-app tether check; real-device
  behaviour (iOS Safari, add-to-home-screen, backgrounding) can only be confirmed by Nick.
- **Isolation and network rules will be verified locally and synthetically** (path probes, process-tree
  kills, blocked-domain attempts) rather than by hostile scenarios.
- **Upgrade reliability must be proven without touching the dogfood install.** V2 upgrade tests use V2
  data roots and the V2 candidate only; the protected dogfood pair is never the subject.
