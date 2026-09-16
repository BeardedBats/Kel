# 04 — Credential Runtime (Kel V1.5, G4)

Status: **implemented (engine + desktop spawn path)** — verified by
`runtime/tests/test_v15_credentials.py` (7 tests) and the custody suite; the packaged
end-to-end check runs at G11 via `packaging/verify-credentials.cjs`.

## The flow as shipped

```text
provider execution needs a credential
        ↓
desktop main process decrypts exactly that value from OS secure storage (safeStorage / DPAPI)
        ↓
value enters only the engine child's environment at spawn (process-scoped; no global env mutation)
        ↓
engine adapters use it only in the request header of the intended provider call
        ↓
native CLI children receive at most their own provider's key (cross-provider keys stripped)
        ↓
test commands receive no provider keys; the isolated WSL runtime gets none from Kel — the WSL
distro keeps its own in-distro auth file (see Known limits)
        ↓
never persisted in the engine database · never returned to the renderer · never logged or
exported · durable error text is redacted before it can be stored
```

## What is implemented where

| Concern | Where | Evidence |
|---|---|---|
| Custody | `desktop/.../kelCredentials.ts` — safeStorage ciphertext on disk, no IPC returns a value | custody tests + `verify-credentials.cjs` |
| Injection | `KelService.ts` spawn: `getCredential('anthropic','api_key')` → child `env` only; value never logged | source; G11 packaged check |
| Request scope | `kel/internal.py` — key travels in the `x-api-key` header of the provider request only; never in request bodies | `RequestScopeTests` |
| Redaction | `kel/internal.py::redact` (also used by `kel/research.py`) — secret-shaped tokens and live env values are removed from any error/result text that can become durable | `RedactionTests` |
| Child isolation | `kel/native.py::child_env` — never `CLAUDECODE`, never the other provider's key | `ChildEnvironmentTests` |
| Test commands | `kel/host_runtime.py::test_command_env` — provider keys stripped | `ChildEnvironmentTests` |
| Durable hygiene | a completed worker run leaves no key bytes in the store (sqlite, wal, artifacts) | `DurableLeakTests` |
| Export hygiene | diagnostics export refuses secret-shaped values (V1.4.1) | custody suite |

## Leak vectors (G4 instructions) and their status

| Vector | Status |
|---|---|
| transport/provider error messages | redacted (`RedactionTests`) |
| request body | asserted absent (`RequestScopeTests`) |
| native child inheritance | cross-provider keys stripped (`ChildEnvironmentTests`) |
| test-command environment | stripped (`ChildEnvironmentTests`) |
| engine database / artifacts / logs of runs | scanned clean (`DurableLeakTests`) |
| command lines | the key is never placed in argv anywhere in the source |
| crash reports | engine writes no crash dumps containing env; desktop crash reporter is donor-side and unchanged (G8 review item) |
| diagnostics / exports | export refuses secret-shaped values; `decisions`/state carry no values |
| error messages / retries | adapter errors pass through `redact` before storage |
| provider fallback | fallback reuses the same header path; no second copy of the value is created |
| renderer | no IPC returns a value (custody design); `credentialStatus` lists field names only |

## Known limits (recorded, not hidden)

- New or changed credentials apply at the **next engine start**; the running engine keeps the
  environment it was spawned with. The Providers copy states this.
- Only `anthropic:api_key → ANTHROPIC_API_KEY` is consumed by a live engine call path today
  (internal worker + research). Other stored providers keep custody + metadata; their consumption
  lands when their engine execution paths exist (provider runtime audit, `03_PROVIDER_RUNTIME.md`).
- The WSL isolated runtime keeps its own in-distro provider auth (`runtime_setup.py` copies
  `auth.json` root-only at setup, `02A` row 28); it is out of the host-process env path and is
  reviewed again at G8/G9.
- `verify-credentials.cjs` is extended at G11 to assert injection + no-plaintext across a real
  engine restart on the packaged build.
