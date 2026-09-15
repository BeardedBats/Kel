# 16 — Known Limitations (Kel V1.5)

Status: **working** — kept current; nothing is removed without evidence.

## Authorization increment (G1/G2, this working tree)

- Model/provider inference calls (read-only native adapters, internal worker) are not lease-gated;
  those adapters perform no repository or filesystem effects.
- `browser` and `external` action kinds have no calling runtime today; boundary policy exists so a
  future caller already passes the gate.
- `no-screen-takeover` and `firefox-only` remain checker-level rules: no current action family
  synthesizes input or drives a browser (G2 review decision: gate or truthful scope statement).
- Role tool policy applies when a run carries an assigned role; automatic role attachment to every
  run is a later G3 step.
- The desktop Autonomy page copy still carries V1.4.1 "not yet" wording; it must be corrected
  before release (G7).

## Carried from V1.4.1 (still true)

- No OS-level sandboxing for native hosts: the documented user-authorized trust model applies
  (`docs/v1.4.1/02_RUNTIME_TRUST_BOUNDARY.md`); Codex Windows sandbox modes remain the blocker.
- Byte-identical release rebuilds are not promised; verify with `scripts/verify-release.ps1`.
