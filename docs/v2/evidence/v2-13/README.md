# V2-13 — Local execution isolation (2026-09-21)

Increment: §18's practical containment on the paths Kel already has — no VM platform, no container
orchestration, no sandbox rewrite. The measured starting point first, then the three gaps closed.

## What was already true (measured, not assumed)

- **Processes.** Broker and coding transports spawn with `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`
  (`start_new_session` on POSIX), keep broker logs under the data root, and kill through
  `terminate_known_process` — an **identity-bound** handle (Win32 process-creation time; `pidfd` on
  POSIX), never a reused PID. `test_isolated_recovery` already pins: quiescent-contained work retries
  without the old session, expanded permission prevents automatic replay, unknown-process quiescence
  stays fenced, and a cancel is acknowledged only after a confirmed group stop.
- **Filesystem.** Coding never edits the project: it snapshots to an isolated copy
  (`repositories/<job_id>`, recorded in `code_workspaces`) with linked-path refusals, `.env*` skips and
  a 10 MB untracked cap; application into the project is a fully guarded transactional apply
  (authorization gate, linked-metadata refusal, instance lock, baseline/after manifests, backup vault,
  conflict refusals — `apply_changes.py`).
- **Read-only execution.** Native leaves already run tool-disabled: codex `-s read-only` +
  `sandbox_mode="read-only"` + a long `--disable` list; claude `--safe-mode --tools '' 
  --permission-mode dontAsk`. Credential containment (Round 2.5 R7) already strips other providers'
  keys from a child.

## What this increment added

| Piece | Where | What it does now |
|---|---|---|
| `kel/containment.py` (new) | one small module | The three reusable rules: sensitive folders, disposable sessions, and secret-shape scrubbing. |
| Sensitive-folder protection | `assert_usable_root` + `sensitive_reason` | Kel refuses to snapshot or modify: Windows / Program Files, the user's credential folders (`.ssh`, `.aws`, `.gnupg`, `.azure`, `.kube`, `.docker`, `.config/gcloud`), anything inside **Kel's own data root**, and any path the environment protects via `KEL_PROTECTED_PATHS` (the desktop sets its stable-app folders there). Refusal is a plain sentence naming the reason. |
| Wired at both autonomous seams | `coding.snapshot` (every caller) + `CodingAdapter.execute` (every execute, so a root that moves under one later is refused too) + `apply_changes.apply_checked` (before any staging) | A sensitive source can never be snapshotted; a sensitive destination can never be written. |
| Disposable sessions | `session_dir` / `cleanup_session` + `NativeAdapter.execute` | Every native run gets `<data root>/sessions/<run_id>`, TMP/TEMP/TMPDIR point at it, and it is removed when the transport returns (best-effort; a locked leftover never fails the run). |
| Widened env scrub | `scrub_secrets` + `child_env(provider, session=…)` | The R7 rule is now the **shape** of the name: anything ending KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH is dropped unless it is this provider's own credential (Kel's `KEL_*` helpers are configuration, not a service secret). |

## Rules the increment pins

- **Nothing sensitive is snapshotted or written** — the check runs on every execute and before any
  staging write, and names its reason in plain words.
- **A run's temp is disposable** — created per run, pointed at by the child's TMP/TEMP/TMPDIR, removed
  on return.
- **A child carries its own credential and no other secret-shaped variable.**
- **The read-only leaf cannot regress silently** — the argv pins (`-s read-only`,
  `sandbox_mode="read-only"`, `--disable`, `--safe-mode --tools ''`) are asserted.

## Verification (on the final code of this increment)

- `tests/test_v2_isolation.py` (new, 10 tests) — system folder refused (with its label); credential
  folders refused; `KEL_PROTECTED_PATHS` refused (including an inner path); Kel's own data root
  refused; a plain temp project allowed; `coding.snapshot` refuses a sensitive source before any git
  call; the scrub drops every secret shape but keeps the named credential; `child_env` keeps only its
  own provider credential; the session becomes the child's TMP/TEMP/TMPDIR and is removed on cleanup;
  the read-only leaf argv is pinned.
- Bounded groups on the final code (one stack at a time):
  `test_v2_isolation test_coding_boundaries test_coding_recovery test_coding_transport
  test_isolated_recovery test_broker_recovery test_v15_credentials test_core` → **108 OK** (15 s);
  `test_apply_changes test_v16_r7_credentials` → **11 OK** (6 s).

## Honest limits (also in `KNOWN_LIMITATIONS.md`)

- **The child env is a scrubbed inherit, not an allowlist** — restricting PATH/SystemRoot etc. to a
  fixed set would risk breaking installed CLIs without live testing; the secret-shape rule is the
  enforceable part.
- **Sessions are for native CLI children**; broker processes are Kel's own and inherit the engine env.
- **The sensitive list is a rule, not a filesystem ACL** — it refuses Kel-driven work at two seams;
  it is not an OS-level sandbox (explicitly out of scope).
- **`KEL_PROTECTED_PATHS` is environment-driven** — the desktop must set it for stable-app folders to
  be protected; the V2 test root sets it only in tests.
