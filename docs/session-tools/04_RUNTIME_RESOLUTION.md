# Runtime resolution — one intent, whichever worker runs

## The abstraction

A capability is a user word; a runtime gets tools. The mapping lives in one place
(`capabilities.CAPABILITIES[*]['tools']`) and is deliberately not user-visible:

| Capability | Tools it covers today | Availability probe |
|---|---|---|
| Web | `browser`, `web`, `research` | engine (Kel can look things up) |
| Files | `write`, `read_files` | always available (Kel owns project writes) |
| Terminal | `shell`, `run_tests`, `run_command` | a usable coding runtime on this machine |
| GitHub | `git`, `repo` | same runtime probe |
| Google Drive | `drive` | connector — needs setup until a Kel-level connector exists |
| Connected apps | `mcp` | connector — needs setup |

`capability_for_tool(tool)` is what execution paths use: `kel.coding` passes
`capability_for_tool(tool)` for each of `git`, `run_tests`, `write` into `kel.authorize`, so a
conversation that has GitHub or Terminal switched off stops the run *at the boundary*, before any
repository effect, whichever ACP worker was going to perform it.

## What this preserves from the unified-tool architecture

- Tools/MCP servers are still configured once in **Settings · Tools**; the conversation control only
  expresses intent, and the capability layer only decides *whether* that intent is honoured here.
- The policy is stored per conversation, not per worker: switching the conversation's worker cannot
  change what it may use (the packaged scenario records the same override after a restart, and unit
  tests resolve without any worker in the picture).
- No new per-runtime configuration surface exists, and the UI contains no runtime words.

## Where a worker can still narrow

Role tool policy (layer 4) and capability leases (layer 5) run *after* the conversation layer. A run
whose role forbids `git`, or whose lease does not cover a target, is still refused — the conversation
override never widens those.

## Honest limits

- The connector-backed capabilities (Drive, Connected apps) have no Kel-level connector yet, so they
  report "Needs setup" and the control offers the settings surface that does exist. When a connector
  arrives, `availability()` gains one probe; nothing else changes.
- Agent-side tool registries (Codex/Claude internal tool names) are not enumerated in the UI or the
  engine policy: the engine decides Kel's effects, and the conversation policy governs those.
