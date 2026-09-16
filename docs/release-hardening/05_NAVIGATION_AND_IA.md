# Navigation and IA

## Where Transcription lives

- One sider entry (Tools group, beside Work/Autonomy/…), one route `/transcription`, reachable from
  the command palette (probe: `paletteTranscript` true) — first-class but not intrusive: the chat
  stays the default surface.
- The composer mic is the fast path; the page is the library and the review surface. Neither is
  needed for the other to work.

## Anti-duplication audit

- **One mic control**: `KelMicButton` in both composers; donor `SpeechInputButton` unmounted
  everywhere (grep-verified; its Ctrl/Cmd+M registration is inert) → JR-40.
- **One vetting door to voice**: transcription routes into the existing session model; there is no
  second voice-specific vetting parser or engine (code-reviewed and contract-tested) → JR-34/39.
- **One nav registry**: sider items and settings tabs derive from single registries (`BUILTIN_*`),
  so a hidden page or a second nav concept fails the `settings`/`sider` scenarios → JR-30.

## Reachability

- Every `data-testid` control on `/transcription` was clicked or explicitly exercised by the
  packaged scenarios in this program (record, upload, rename, folder create, drag/select assign,
  copy, download txt, download audio, combine, send to chat, use-vetting, think-out-loud, delete,
  source settings, key connect/clear).
- Engine family vs renderer: `combine` (unreachable in review round 1) now has a UI door; the
  remaining engine-only actions are documented API-only in the transcription docs → JR-39.

## No stale donor concepts on Kel surfaces

- `AionUI`/`aionui` strings, `acp-temp` tab naming, and donor page labels remain recorded open
  items in `docs/product/USER_JOURNEY_HISTORY.md` (O2/O4) with their rules — unchanged by this
  program, verified not to have grown (jargon scan + sider/maintext scenarios).
