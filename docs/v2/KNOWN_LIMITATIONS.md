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

## V2-05 — what a phone still cannot do (measured, not assumed)

1. **Voice → Muse is not wired from the browser.** The phone records (timer, Cancel, Stop all work) but
   stopping sends no `/api/transcription` request and produces no transcript. Desktop voice was repaired
   and verified in the Daily Driver line; the browser path is still unconnected.
2. **Sending needs a connected model.** With none connected the composer's send stays disabled (proved
   with both paste-shaped input and real key presses) and Kel says so plainly ("so Kel will wait instead
   of guessing" + Open Providers). Connecting one is reachable from the phone (4 providers · 2 usable),
   but no model turn was spent in this increment, so send-then-continue was not exercised end to end.
3. **Attention actions were exercised only for the kind of attention this instance actually had** — a
   connection needing setup, which opens Providers from the phone. Approval, deny, grant, resume, stop and
   review attach to job state that did not exist here.
4. **The phone's drawer was not opened by the automation.** A conversation seeded through the engine's own
   `/api/send` is authoritative and visible through `/api/state`, but the history entry was never reached
   on the phone. The collapsed rail visible at 393px is inert by design (`x=-11`, `pointer-events: none`)
   — the drawer, not the rail, is the phone's navigation.

### V2-05 voice — where the browser path actually breaks (diagnosed)

`KelMicButton.start()` starts capture, then calls `/api/transcription`
`{action:'stream_start'}` — but that call sits in a `try { … } catch { liveRef.current = false;
sessionRef.current = null }`. Every failure is swallowed: the phone shows a running recording timer and
then nothing, with no transcript and no message. In the measured run **no `/api/transcription` request
reached the gateway at all** (0 hits in the gateway log, HTTP or otherwise), so the browser's transport
for that route is the thing to connect — the engine and the gateway were both healthy at the time.
Required by V2-05 itself: when the microphone path cannot reach transcription, the phone must say so
truthfully instead of silently recording. Next run: find the browser transport for `/api/transcription`,
fix or wire it, replace the silent catch with a plain sentence, then verify against Muse.

### V2-05 voice — fixed (desktop bridge requirement removed)

The browser voice path now uses the shared Kel transport, so a phone reaches Muse through the gateway.
Verified end to end in a real browser: `stream_start` → 27 `stream_chunk` → `stream_finish`, Muse's
transcript in the composer, no practice text. The engine's 24 kHz mono PCM16 expectation is now recorded
in the evidence README (a fixture at any other rate is refused by Muse itself).

Still open after this pass, in `RESUME.md` order: send with a connected model (the phone can reach
Providers and Connections but no model was selected), conversation history from the phone's drawer,
job-driven attention actions, conversational project routing, and multi-utterance dictation (the
first utterance's partial is lost when Muse never marks it final).

### V2-05 — the "Work & context" panel is not reachable at phone width (measured)

The panel that holds Kel's conversation history, the attention-first work list and the conversation
selector is opened by the rail's footer trigger (`KelWorkPanel.tsx`, class `kel-work-context-btn`). At
393×852 that trigger sits in the collapsed rail — off-canvas and inert, exactly like the rail's named
entries — so clicking it times out and the panel never opens. Journey B records it
(`drawer-failed`, then the unchanged home text). Consequence: the phone cannot reach conversation
history, the conversation selector or the attention-first work list in this build; the phone's own
entry point for that panel (if one exists) was not identified in this increment. This is a real V2-05
gap, not a spec artifact: the trigger exists, resolves, and cannot be tapped.

### V2-05 — why the phone's composer cannot send: no assistant is selected (found, not guessed)

`useGuidSend.ts` gates the send button on `loading || !selectedAssistantId` — an *assistant* (the shell's
agent) must be chosen, and in a fresh web profile nothing is. The assistants exist and are reachable:
`GET /api/assistants` through the gateway answers with real entries (`bare:632f31d2` "Aion CLI", an
`aionrs` agent, plus the CLI-backed ones), and the Providers page already reports Claude Code and Codex
CLI as "Ready to use". What has not been done yet is choosing one **from the phone**: the assistant
selection area is where a desktop picks it, and this increment did not establish the phone's affordance
for it. Next run: select an assistant on the phone (or verify the shell persists a desktop pick into the
profile the phone uses), then prove type → send → model reply → continued context, with no model turn
spent until the send actually goes through.
