# Increment — R7: credential / network boundary (CREDENTIAL-CONTAINMENT)

increment_id: V16-R7-CREDENTIAL-BOUNDARY
invariant: **CREDENTIAL-CONTAINMENT** — the capability to use a provider does not imply arbitrary
worker or tool access to the raw credential
requirement: `REQ-R25-R7` (roadmap R2.5 §R7; marathon directive §15)
phase: Campaign A — R7
base_commit: `e8bbb05`
production_commit: `b6c4eff`
status: complete

## Inventory (code-verified)

| Channel | Where | Control | Verdict |
|---|---|---|---|
| Trusted provider process (Claude/Codex/DeepSeek/internal) | `host_runtime.py` (harness `params['apiKey']`), `coding.py` (Claude run), `appserver.py` (Codex child), `internal.py` | reads the key from the environment at call time and passes it to the provider process only | allowed by R7.C |
| Model prompt text | prompts sent to providers | no prompt builder interpolates a credential; the harness receives `apiKey` as a *parameter*, never inside the prompt | SAFE |
| Ambient child environment | `appserver.py` (Codex child), `coding.py` (test command), `internal.child_env` | **fixed here**: a child receives only the credentials named in `keep`; the coding test command clears all three provider keys and runs with `networkAccess: False` | **FIXED** |
| Durable content (events, packets, memories, workforce records, artifacts) | `internal.redact` (live values + `sk-` tokens), `memory.scan_secret`, `workforce.assert_safe` | redaction at error paths, refusal at record/proposal boundaries | SAFE |
| Diagnostics / exports | `diagnostics.py` (excludes 'credentials, tokens and API keys' and 'environment dumps'; `SECRET_MARKERS` masking in redaction paths) | refuses to enumerate or dump secrets | SAFE |
| Logs | engine logs carry state names and plain sentences; `redact` wraps provider errors | no key material found in log-producing paths | SAFE |
| Backups | `backup.py` | the credentials file never travels in a backup (PER-04); `SECRET_KEYS` stripped | SAFE |
| Guardrail vocabulary | `guardrails.py` 'credential-boundary' | 'Kel reads or writes only its own namespaced credential entries; unrelated secrets are never enumerated, exported, or logged' | SAFE |
| Autonomy refusals | `autonomy.py` | credential-kind actions are refused unconditionally | SAFE |

## Gaps closed

1. `appserver.py` copied the whole environment and removed only `ANTHROPIC_API_KEY`; the Codex child
   therefore also received the DeepSeek key (and any other unrelated provider key). New
   `internal.child_env(*, keep=())` returns an environment containing only the named credentials.
2. `coding.py`'s test-command env cleared Anthropic/OpenAI but not `DEEPSEEK_API_KEY`.

## Network boundary — the honest statement (R7.D)

`host_runtime.py` is **user-authorized native execution**: it is not an OS sandbox and does not
pretend to be one. A full-access native process can reach the network as the user can; domain policy
inside Kel is a convenience guard, not a firewall. Campaign A therefore does **not** implement Windows
egress filtering; enforceable network-aware runtime grants are recorded as **post-V1.6 research**
(roadmap §21 watchlist). What Campaign A does guarantee: provider children get only their own
credential (fixed here), the coding test command runs with the provider keys cleared and
`networkAccess: False`, and no credential becomes prompt text, artifact, packet, log or diagnostics
content.

## Tests (R7.E, synthetic sentinels)

`tests/test_v16_r7_credentials.py` — **5 new**: a child receives only the credential it requires
(Anthropic child has no OpenAI/DeepSeek key and vice versa); a child needing no provider credential
receives none; `redact` masks a live sentinel value and `sk-` tokens while leaving ordinary text
alone; a secret-shaped value is detected by `scan_secret` and refused by `assert_safe`; the
containment is wired at the spawn sites (no `os.environ.copy()` in `appserver.py`, the coding
test-command env names all three keys).

Focused: workforce-schemas, coding transport/recovery, memory suites + R7 = **85 passed**. Full
engine: TEST_EVIDENCE_INDEX A-26.

## Limitations / audit questions / repair hints

- The engine process itself necessarily holds the credential in memory (it calls providers) and its
  own local helper subprocesses (e.g. `git` in `coding.py`) inherit the engine environment. That is
  the user's own machine-local execution, not worker-visible data; an audit question is whether any
  future *untrusted* helper should be spawned through `child_env()` instead.
- `host_runtime.py` hands the user's environment to the native host by design (it runs user-approved
  commands); this is disclosed, not hidden.
- Prompts: no builder interpolates a credential; the audit should still grep for any future
  `apiKey`-into-prompt path.
- Audit questions: (a) does any provider adapter log its own request headers? (b) does the desktop
  renderer ever receive a credential (it should not — the engine owns them)? (c) is the harness
  parameter channel audited for length/content limits? (d) are third-party CLI credential stores
  (`claude`, `codex` own configs) in scope for a future credential proxy (post-V1.6 watchlist)?
- Repair hints: none open from this increment.
