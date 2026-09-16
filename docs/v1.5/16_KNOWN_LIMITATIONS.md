# 16 — Known Limitations (Kel V1.5)

Status: **working** — kept current; nothing is removed without evidence.

## Authorization increment (G1/G2, this working tree)

- Model/provider inference calls (read-only native adapters, internal worker) are not lease-gated;
  those adapters perform no repository or filesystem effects.
- `browser` and `external` action kinds have no calling runtime today; boundary policy exists so a
  future caller already passes the gate.
- `no-screen-takeover` and `firefox-only` remain checker-level rules: no current action family
  synthesizes input or drives a browser (G2 review decision: gate or truthful scope statement).
- Role snapshots are attached to every run at claim time, and enforcement reads the frozen
  snapshot; roles only narrow (lease and guardrails always apply). Live role edits govern ad-hoc
  intents that pass a role directly and apply to new runs, never retroactively to a frozen one.
- The Autonomy page copy is current (G7 correction, G12 qualification): the boundary runs at the
  execution-path effect points that exist today — repository work, file application, and project
  creation — stated per effect point instead of a blanket claim.
- The ACP host is a transport for the donor agent surface: donor-agent tool permission requests
  are refused by policy and no tool execution is implemented there (V1.5 G12).

## Credentials (G4)

- New or changed credentials apply at the next engine start; a running engine keeps its spawn-time
  environment.
- Only `anthropic:api_key` is consumed by a live engine call path today (internal worker and
  research). Other stored providers keep custody + metadata until their execution paths exist.
- Desktop `tsc --noEmit` is clean as of G8 (26 → 0 errors, behavior-preserving fixes) and is kept
  green through the release.

## Carried from V1.4.1 (still true)

- `docs/v1.4.1/06_V1_5_DEFERRED_WORK.md` is the frozen historical ledger: its items 1–4
  (execution-path enforcement, central authorization, role tool-policy at effect points,
  `guardrail_decisions`) shipped in V1.5 — see `02`/`02A`; the v1.4.1 document itself is not
  edited (historical record).
- No OS-level sandboxing for native hosts: the documented user-authorized trust model applies
  (`docs/v1.4.1/02_RUNTIME_TRUST_BOUNDARY.md`); Codex Windows sandbox modes remain the blocker.
- Byte-identical release rebuilds are not promised; verify with `scripts/verify-release.ps1`.
