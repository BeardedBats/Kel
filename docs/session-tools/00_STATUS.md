# Session-scoped tool controls — status

Program: let a user control what Kel may use **for one conversation** without touching Kel's global
configuration, in plain words, through the same authorization boundary everything else already uses.

## State (2026-09-17)

| Area | State |
|---|---|
| Capability model + availability | done — `runtime/kel/capabilities.py` (Web, Files, Terminal, GitHub, Google Drive, Connected apps) |
| Conversation overrides + persistence | done — `conversation_capabilities` / `capability_global` / `capability_grants` (migration 14) |
| Authorization integration | done — layer 3c in `kel.authorize` (after guardrails, before role policy and leases); the effect spends a one-shot grant exactly once |
| Conversation UI | done — `KelToolsControl` beside the model pill |
| Natural-language control | done — same state, answered inline by the ACP host |
| Engine tests | done — `runtime/tests/test_capabilities.py` (16), full engine suite 545 passed |
| Packaged journey | done — harness scenario `sessiontools` on `dist/package-final10`; all required checks pass, including Allow once (see 06) |
| Independent review | see `docs/basic-ux-sweep/15_FINAL_VERDICT.md` (session-tools continuation entry) |

Evidence artifacts (scratch, not shipped): `ux-audit/runs/final10-sessiontools/ux-sessiontools.json`,
`ux-sessiontools-db.json`, screenshots `sessiontools-01-menu.png`, `sessiontools-03-natural-language.png`.

## Files

- engine: `runtime/kel/capabilities.py`, `service.py` (`/api/capabilities`), `authorize.py` (layer 3c),
  `coding.py` (passes the capability of each effect tool), `acp_host.py` (inline directives)
- desktop: `renderer/components/kel/KelToolsControl.tsx`, mounted in
  `pages/conversation/components/ChatConversation.tsx`; bridge whitelist in
  `process/services/kel/KelService.ts`
- tests: `runtime/tests/test_capabilities.py`, harness scenario `sessiontools` in `packaging/ux-audit.cjs`
