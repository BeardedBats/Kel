# The Memory folder (D-81)

Every AI tool Kel runs (Claude Code, Codex, every staff member) reads and writes only inside
`Desktop\Kel\Memory\` (anywhere in it, across projects) and the run's own working copy. Kel's App,
Data (the real data and every key), Kel (source) and Tools folders, Documents and the home folder are
off-limits. A refusal is one plain sentence: "That's outside Kel's Memory folder, so I can't touch it."

## Layout and location

| Path | What it is |
|---|---|
| `Memory\Projects\` | Where Kel creates every new project (`projects.projects_root`). Existing projects stay where they are. |
| `Memory\Kel\` | Kel's read-only mirror for the agents (`kel/memory_mirror.py`). |
| `Memory\Kel\settings.json` | Kel's settings with every key, password and token removed (by field name and by value shape; `assert_clean` runs before writing). |
| `Memory\Kel\chats\<project or "No project">\<date> <title>.md` | One file per chat, all of them, archived ones included. Both chat stores are read (D-77): the app's chats, with their titles and archived flag, carrying the engine's words, plus every engine conversation with messages that no app chat points at. Secret-shaped strings are replaced. |
| `Memory\Kel\knowledge\<project>\notes.md`, `memory.md` | The project's notes and the facts Kel remembers (active memories). |

- **Location:** `KEL_MEMORY_ROOT` if set. Tests and audits point it at scratch. The desktop main process passes `<folder holding App>\Memory` when packaged. Without either, the engine uses the folder beside the installed App, or else the folder beside Data.
- **Creation:** made on demand.
- **Mirror refresh:** the engine's `Keeper` thread rewrites the mirror once the source files have been still for 2 s after a change. Every 15 s it checks the mirror against a manifest kept in `<engine>\memory-mirror\` and puts back anything changed. Mirror files are marked read-only. After every native run, `runtime_guard.settle` repeats the check. It reverts any change, moves files an agent added to `<engine>\memory-mirror\reverted\`, and adds one Activity line and one sentence to the result.

## Enforcement, per tool

### Claude Code

Claude Code is held by a PreToolUse hook plus deny rules (`guard_hook.mjs` and `runtime_guard.policy`). The hook is an allow-list:

| Access | Where |
|---|---|
| Read and write | The working copy, Memory, and the run's own temp folder (`<engine>\sessions\<run>`, which becomes the child's TEMP/TMP). |
| Read only | `Memory\Kel` (writes are refused), and `<engine>\desktop-session.json` for the Connections bridge. |
| Read only (system and tool paths) | See the next list. |
| Refused | Everything else. |

The system and tool paths the worker may read (`memory_folder.system_readable_roots`):

- `%SystemRoot%` / `%WINDIR%` (C:\Windows): shells and system libraries.
- `%ProgramFiles%`, `%ProgramFiles(x86)%`, `%ProgramW6432%`: installed tools such as Git, Git Bash, Node.js and PowerShell 7.
- Every folder on PATH, except the home folder itself and any PATH folder inside an off-limits place (Kel's App, Data, source, Tools, or a credential folder).
- The CLIs' own install folders (Claude Code's package folder, Node.js).
- The Git Bash POSIX roots `/usr`, `/bin`, `/etc`, `/mingw64`, `/dev`, `/tmp` and similar, which live inside Git's install. `/c`-style one-letter switches count as switches, not paths.

Shell commands are checked word by word. Quoted paths count as one word. Every drive path written anywhere in the command, including inside code such as `node -e "...readFileSync('C:/...')"`, is checked too. `..` hops are resolved before the check.

Deny rules cover Kel's folders beside Memory, the Data parts that don't hold the working copy, and credential folders. The hook still covers the Data folder itself, because that folder holds the working copy. Deny rules also block edits in `Memory\Kel`.

### Codex 0.157.1

Kel runs Codex with a permission profile, `-c default_permissions="kel"`. The profile gives read on `:root`, write on `:workspace_roots` (the working copy), and write on Memory and the run's temp folder. Kel no longer sends a per-thread `sandbox` or per-turn `sandboxPolicy`, because either one replaces the profile with the legacy policy, and that policy also makes the whole machine's temp folder writable.

**What Codex 0.157.1 cannot do.** Both Windows sandboxes refuse a profile without `:root` read:

- `windows-sandbox-rs/src/lib.rs:714` refuses it.
- `resolved_permissions.rs:105` fails with "elevated Windows sandbox requires effective `:root` read access".

A true read allow-list is therefore impossible in 0.157.1, and each mode does this:

- **Restricted token (`unelevated`, the default, no admin).** Codex can write only to the working copy, Memory and the run's temp folder. Checked against Kel's exact settings: writes to Data and to other folders were refused, and a file outside Memory could still be read. Reads are not confined. Settings says so.
- **Elevated sandbox (after the one-time approval).** Commands run as Codex's own users, CodexSandboxOffline and CodexSandboxOnline. Kel adds `deny` entries (`runtime_guard.codex_deny_paths`), which Windows enforces as deny ACEs for the CodexSandboxUsers group:
  - Kel's folders beside Memory. That means everything in Data except `engine`, and everything in `engine` except `repositories` and `sessions`.
  - Credential folders and `KEL_PROTECTED_PATHS`.
  - Documents, Downloads, Pictures, Music, Videos, Favorites, Contacts, Links, Saved Games, Searches and OneDrive*.
  - The Desktop apart from the Kel folder.
  - `.claude`, `.claude.json`, `.codex\auth.json`, `.gnupg`, `.config`, `.git-credentials`, `.npmrc`, `.pypirc` and `.netrc`.

  Paths are listed only if they exist, and never a folder that holds Memory, the working copy or the run's temp folder. Codex still reads Windows, Program Files, ProgramData, AppData (where tools are installed) and other drives.

**The one Windows admin approval.** In Settings → Permissions, "Where the AI tools work", Nick presses **Block Codex reads outside Memory**. This sends `/api/autonomy {action: 'codex_sandbox_setup'}`, and Codex's app-server runs `windowsSandbox/setupStart {mode: 'elevated'}`. If Codex's setup isn't complete yet, Windows shows one UAC prompt for `codex-windows-sandbox-setup.exe` (publisher OpenAI OpCo, LLC). On success, Kel switches its Codex runs to the elevated sandbox. If Codex's setup markers are already current (version 5 in `%USERPROFILE%\.codex\.sandbox\setup_marker.json` and `.sandbox-secrets\sandbox_users.json`), there is no prompt.

**Before every elevated run**, Kel asks Codex for `windowsSandbox/readiness`. A Codex update can require setup again. If Codex isn't ready, that run uses the restricted-token sandbox, so no admin prompt appears mid-run, and Settings offers the button again.

**Known costs of the elevated mode:**

- The deny ACLs stay on disk. They are tracked in `%USERPROFILE%\.codex\.sandbox\deny_read_acl_state.json`, which the Codex desktop app shares, so its own runs re-sync that list.
- The first run applies deny entries to large folders such as Documents, which may take time.

### Staff and turn models

The turn, reply, planning, review and research calls run Claude Code with no file tools (`--tools ''`, or WebSearch and WebFetch only). They run Codex with its shell tool disabled in a read-only sandbox. They cannot touch files at all.

## Up-front refusal

`runtime_guard.request_refusal` runs before any work starts (D-55). It answers with the one plain sentence when a request names a place outside Memory. These count as allowed: Memory, the project's own folder (the worker has its copy), and system paths for reading. A request that would change `Memory\Kel` or Kel's settings gets: "Memory\Kel is Kel's own read-only copy of its settings, chats and notes, so I can't change it."

## Known gaps

- **Claude Code has no OS-level read sandbox on Windows.** The hook sees the paths in tool arguments and commands. A program the worker runs can still open files it computes at run time.
- **Codex reads stay open until the one-time approval.** After it, reads are open wherever Kel adds no deny entry, including AppData and other drives.
- **Existing projects outside Memory are reachable only through their own run's working copy.** Another project's folder outside Memory is off-limits, like any other outside place.
