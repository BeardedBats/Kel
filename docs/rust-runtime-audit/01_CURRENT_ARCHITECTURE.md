# 01 — Current architecture as built

At commit `ffeef73`. Everything below was read from source, not from design intent. Where the
documents and the code disagree, the code is quoted.

## 1. The process tree

A running Kel with one active coding conversation owns this many processes:

```
Kel.exe  (Electron main)                                   ← TypeScript, owns lifecycle + credentials
├── Chromium renderer / GPU / utility processes            ← Electron
├── aioncore.exe                                           ← vendor native binary, bundled
│                                                            (resources/bundled-aioncore/win32-x64/)
├── KelEngine.exe --data <root>                            ← PyInstaller bundle; long-lived HTTP daemon
│     spawned detached:true + child.unref()  (KelService.ts:95-101)
│     listens 127.0.0.1:<port>, bearer token, 45 s boot deadline polled every 250 ms
│
└── (per conversation, spawned by AionCore, not by Electron)
      KelEngine.exe --acp --data <root>                    ← ACP host over stdio  (acp_host.py)
        │   registered as a *custom agent* through AionCore's HTTP API
        │   (KelService.ts:126-135)
        │
        ├── KelEngine.exe --data <root> --run <run_id>      ← one full interpreter per worker run
        │      runner.py:124-127                            (the broker that talks to the provider)
        ├── KelEngine.exe --data <root> --rpc-run <id>      ← one full interpreter per coding run
        │      coding_transport.py:68-71
        ├── codex app-server --stdio                        ← provider host child (appserver.py:37)
        │      or: node host_claude.mjs <claude.exe>        ← provider host child (host_runtime.py:43)
        ├── git ...                                         ← coding.py:17, projectmap.py:69
        └── wsl.exe ...                                     ← wsl_runtime.py:18, runtime_setup.py
```

Two facts matter more than the rest of the tree:

1. **The engine is a detached daemon.** `spawn(..., { detached: true })` followed by `child.unref()`
   means the engine is *designed* to outlive Electron. That is a deliberate choice, not an accident.
2. **Every worker run and every coding run boots a fresh copy of the whole runtime**
   (`argv = [sys.executable]` when frozen). The engine does not run workers in-process.

## 2. Ownership map

| Thing | Owner | Mechanism |
|---|---|---|
| Engine data folder | the daemon | `KEL_DATA_DIR` or `%APPDATA%\kel-desktop\work` |
| `kel.sqlite3` (engine state) | `runtime/kel/core.py` `Store` | `sqlite3`, WAL, `BEGIN IMMEDIATE`, `synchronous=FULL`, `secure_delete=ON` |
| **A second SQLite database** | Electron main | `better-sqlite3`, `busy_timeout=5000`, WAL, `users`/`conversations` tables + 64 KB `migrations.ts` |
| Single-instance guarantee | Python kernel lock | `msvcrt.locking` / `flock` on `controller.lock` — released by the kernel on process death, no timeout (`instance_lock.py`) |
| Worker lifetime group (Windows) | Python `ctypes` → Win32 | `CreateJobObjectW` + `AssignProcessToJobObject`, kill-on-close (`windows_job.py`) |
| Worker lifetime group (Linux) | Python → cgroup v2 | `memory.max=2 GiB`, `pids.max=256` (`native_group.py`) |
| Worker identity / anti-PID-reuse | Python `ctypes` → Win32 | `GetProcessTimes` creation time; `/proc/<pid>/stat` on Linux (`runner.py:19-38`) |
| Provider credentials | **Electron main only** | Electron `safeStorage` = DPAPI on Windows; injected into the child env at spawn; never in the renderer, never in the engine DB (`kelCredentials.ts:65,89`) |
| Sleep inhibition | Electron | `powerSaveBlocker.start('prevent-app-suspension')` (`keepAwake.ts:26`) |
| Authorization, leases, approvals | Python | durable SQLite state machines in `authorize.py`, `capabilities.py`, `autonomy.py`, `chat_approvals.py` |

Note the shape: **two SQLite databases with two different owners in two different language runtimes.**
That is the real database-ownership fact, and it is not the "Python holds SQLite" picture the
candidate architecture assumes.

## 3. Transport boundaries

Three distinct ones, each with a different failure mode:

| Boundary | Transport | Where |
|---|---|---|
| Electron main ↔ engine daemon | loopback HTTP + bearer token, descriptor file `desktop-session.json` | `KelService.ts:12-24`, `service.py:945-947` |
| Electron main ↔ AionCore | loopback HTTP, `/api/agents/custom`, `/api/conversations` | `KelService.ts:119-131` |
| AionCore ↔ ACP host | stdio, JSON-RPC-ish ACP | `acp_host.py:363-395` |
| Engine ↔ provider CLI | stdio JSON-RPC (`codex app-server`) | `appserver.py:37` |
| Renderer ↔ main | `ipcMain.handle('kel:request')` with a **route allowlist regex** | `KelService.ts:365-384` |

## 4. Measured startup, honestly

From `docs/v1.5/12_PERFORMANCE.md` (one machine, stated as such) plus live spans in the archived
packaged runs:

| Measure | Value |
|---|---|
| `import kel.service` (cold) | ~60 ms |
| `Store` open | ~46 ms |
| `Service` construct (store + adapters + engine) | **~650 ms** |
| **live `engine-start` span** | **93–113 ms typical; 243 / 378 / 404 / 486 ms outliers** |
| Authorization decision | ~30 ms (each writes a durable `guardrail_decisions` row with fsync) |
| Diagnostics snapshot | ~8 ms |
| Electron boot wait ceiling | 45 000 ms, polling every 250 ms |

Read that table again with the Rust question in mind. The engine announces readiness in about a
tenth of a second, on a boot path with a forty-five-second ceiling, behind an Electron/Chromium
startup that nobody has even instrumented yet — `12_PERFORMANCE.md` says plainly: *"No renderer
startup / first-paint timing yet."* Startup is not a bottleneck in this product. It is not close.

## 5. The engine's dependency surface

An AST scan of all 47 `runtime/kel/*.py` at `ffeef73` finds exactly one third-party import:

```
stdlib modules used: 32
THIRD-PARTY: ['websocket']     ← websocket-client, transcription realtime socket only
```

`runtime/KelEngine.spec` confirms it: `binaries=[]`, `hiddenimports=[]`, `excludes=[]`.

The engine is **pure standard library plus one WebSocket client**. There is no NumPy, no Pandas, no
native extension, no compiled wheel, no ABI surface to manage. The `hiddenimports=[]` line is the
whole native-module-ABI story: there isn't one.

## 6. What this section establishes for the rest of the audit

Three premises that the analysis in `03` and `04` depends on:

- **P1 — SQLite is the same C library on both sides.** `sqlite3` (Python) and `rusqlite` (Rust) are
  both thin wrappers over libsqlite3. WAL, SHM, `BEGIN IMMEDIATE`, busy timeouts, and the
  killed-process WAL-mapping behaviour on Windows are *properties of SQLite and Windows*, not of the
  calling language. A Rust store would meet the identical constraints.
- **P2 — the expensive parts of boot are not Python.** Chromium, `aioncore.exe`, and disk I/O
  dominate. Python contributes ~60 ms of import.
- **P3 — the trust core is language-neutral in a different sense.** Leases, approvals, fencing,
  grants and receipts are *protocols over durable rows*. Their correctness comes from the tests and
  the state machine, not from the language. Rewriting them in Rust does not make them more correct;
  it makes them new.
