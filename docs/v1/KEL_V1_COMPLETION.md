# Kel V1 release 0.4.0

Kel starts in a wider normal window, sized to fit the screen. The sidebar, chat and message box use the available screen area.

## Native agent access

New coding tasks run on Windows. Codex uses danger-full-access with approval policy never. Claude uses its native bypassPermissions mode. Kel no longer imposes the previous tool whitelist or disables delegation in these native sessions.

Access follows the current Windows account. This does not grant administrator privileges. Installed agents, provider access and available tools still determine what each task can do. Kel creates a project copy for checked changes, but full native access is not a sandbox.

Old jobs without the native-host contract field keep their original WSL runtime. This preserves existing work. New jobs do not need WSL.

## Completion and recovery

Budgets, independent result checking, conflict checks and backups remain. A model answer alone cannot mark coding complete.

A broker restart reconnects to the existing transport and native session. If the native transport dies, Kel stops its descendant processes. Unknown host effects remain UNCERTAIN. Kel does not replay an action whose effects it cannot establish.

Apply checked changes verifies the original project and saves recoverable before and after bytes. It serializes Kel applications. Other editors can still change the same project.

## Evidence

Current evidence is under evidence/native-full/:

- tests.txt: automated behavior and host runtime checks.
- codex-code.json and claude-code.json: real native coding, Windows PowerShell tests, authorized outside-file reads, local HTTP access and session resume.
- faults/: six native fault checks across Codex and Claude. Broker loss preserves one run and one test execution. Cancellation stops work. Transport loss leaves an uncertain result without automatic replay.
- packaged/verification.json: packaged desktop workflow, normal window startup, checked report download, application, reopening and saved context.

Earlier release evidence remains under evidence/v1-finish/. Its isolation claims describe the old WSL runtime. They do not describe native-host access.

## Scope

V1 includes local chat, saved projects, context, durable work, result checking, research, coding and checked local application. Full native tools are available for requested work. Unrequested publication remains outside the work contract.

Personal-life OS features remain V2/V3. Universal compatibility with every Windows application is not established. This package includes neither credentials nor live user databases.

No direct donor code was copied. The user's permission to use Forge personally remains unchanged.
